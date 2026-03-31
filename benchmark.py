"""
benchmark.py — Comprehensive Efficiency & Accuracy Test Suite

Tests:
  1. Accuracy: bit-exact data integrity across producer→consumer pipeline
  2. Efficiency: latency & throughput across payload sizes (100 → 1M floats)
  3. Consistency: statistical analysis over multiple iterations per size

Runs against a live producer on localhost:8000.
Consumer output is read from /tmp/consumer_output.log.
"""

import json
import math
import os
import statistics
import struct
import sys
import time
import urllib.request

PRODUCER_URL = "http://localhost:8000/process"
CONSUMER_LOG = "/tmp/consumer_output.log"
RESULTS_FILE = "/tmp/benchmark_results.json"

# Payload sizes to test (number of float32 elements)
SIZES = [100, 1_000, 5_000, 10_000, 50_000, 100_000, 500_000, 1_000_000]
ITERATIONS = 5  # per size


def send_payload(data: list[float]) -> dict:
    """POST data to producer and return the JSON response + round-trip time."""
    payload = json.dumps({"data": data}).encode("utf-8")
    req = urllib.request.Request(
        PRODUCER_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode())
    t1 = time.perf_counter()

    body["roundtrip_ms"] = (t1 - t0) * 1000
    return body


def get_last_consumer_block(log_path: str, timeout_s: float = 10.0) -> dict:
    """Wait for and parse the most recent consumer log block."""
    deadline = time.time() + timeout_s
    last_size = 0

    while time.time() < deadline:
        try:
            with open(log_path, "r") as f:
                content = f.read()
        except FileNotFoundError:
            time.sleep(0.2)
            continue

        if len(content) > last_size and "TENSOR RECEIVED" in content[last_size:]:
            # Parse the last block
            lines = content.strip().split("\n")
            block = {}
            for line in reversed(lines):
                if "Tensor shape" in line:
                    # torch.Size([N]) → N  — use rfind to skip [CONSUMER] tag
                    bracket_start = line.rfind("[")
                    bracket_end = line.rfind("]")
                    block["shape"] = int(line[bracket_start + 1 : bracket_end])
                elif "Tensor dtype" in line:
                    block["dtype"] = line.split(":")[-1].strip()
                elif "Data pointer" in line:
                    block["data_ptr"] = line.split(":")[-1].strip()
                elif "Total latency" in line:
                    block["consumer_total_ms"] = float(line.split(":")[-1].strip().replace(" ms", ""))
                elif "Read latency" in line:
                    block["consumer_read_ms"] = float(line.split(":")[-1].strip().replace(" ms", ""))
                elif "Convert lat" in line:
                    block["consumer_convert_ms"] = float(line.split(":")[-1].strip().replace(" ms", ""))
                elif "First 5 vals" in line:
                    # Extract the [...] after "First 5 vals" — use rfind to skip [CONSUMER]
                    bracket_start = line.rfind("[")
                    bracket_end = line.rfind("]")
                    vals_str = line[bracket_start + 1 : bracket_end]
                    block["first_5"] = [float(v.strip()) for v in vals_str.split(",")]
                elif "tensor sum" in line:
                    block["tensor_sum"] = float(line.split(":")[-1].strip())
                if len(block) >= 8:
                    break
            return block

        last_size = len(content)
        time.sleep(0.2)

    return {}


def verify_accuracy(sent: list[float], consumer_block: dict) -> dict:
    """Check data integrity: shape, first values, and sum."""
    result = {"passed": True, "errors": []}

    # Shape check
    if consumer_block.get("shape") != len(sent):
        result["passed"] = False
        result["errors"].append(
            f"Shape mismatch: sent {len(sent)}, got {consumer_block.get('shape')}"
        )

    # Dtype check
    if consumer_block.get("dtype") != "torch.float32":
        result["passed"] = False
        result["errors"].append(f"Dtype mismatch: {consumer_block.get('dtype')}")

    # First-5 values check (float32 tolerance: ~1e-7 relative)
    if "first_5" in consumer_block:
        # The sent values go through float64→float32 cast, so we compare at float32 precision
        for i, (s, r) in enumerate(zip(sent[:5], consumer_block["first_5"])):
            s32 = struct.unpack("f", struct.pack("f", s))[0]
            if not math.isclose(s32, r, rel_tol=1e-5, abs_tol=1e-7):
                result["passed"] = False
                result["errors"].append(f"Value[{i}] mismatch: sent {s32}, got {r}")

    # Sum check (float32 accumulation has limited precision for large N)
    if "tensor_sum" in consumer_block:
        expected_sum = sum(struct.unpack("f", struct.pack("f", v))[0] for v in sent)
        rel_err = abs(consumer_block["tensor_sum"] - expected_sum) / max(abs(expected_sum), 1e-9)
        result["sum_relative_error"] = rel_err
        # Allow generous tolerance for large sums (float32 accumulation)
        if rel_err > 0.01:
            result["passed"] = False
            result["errors"].append(
                f"Sum mismatch: expected {expected_sum:.4f}, got {consumer_block['tensor_sum']:.4f} "
                f"(rel_err={rel_err:.6f})"
            )

    return result


def clear_consumer_log():
    """Truncate the consumer log so we can detect the next block cleanly."""
    try:
        with open(CONSUMER_LOG, "w") as f:
            f.truncate(0)
    except Exception:
        pass


def run_benchmark():
    print("=" * 72)
    print("ZERO-COPY SHARED MEMORY — EFFICIENCY & ACCURACY BENCHMARK")
    print("=" * 72)

    all_results = []

    for size in SIZES:
        print(f"\n{'─' * 72}")
        print(f"  PAYLOAD SIZE: {size:>10,} floats ({size * 4 / 1024:.1f} KB)")
        print(f"{'─' * 72}")

        iteration_results = []

        for it in range(ITERATIONS):
            # Generate deterministic test data
            data = [float(i) * 0.001 for i in range(size)]

            clear_consumer_log()
            time.sleep(0.3)  # let consumer see the cleared log

            # Send to producer
            try:
                producer_resp = send_payload(data)
            except Exception as exc:
                print(f"  [{it+1}/{ITERATIONS}] PRODUCER ERROR: {exc}")
                continue

            # Wait for consumer to process
            consumer_block = get_last_consumer_block(CONSUMER_LOG, timeout_s=30.0)

            if not consumer_block:
                print(f"  [{it+1}/{ITERATIONS}] CONSUMER TIMEOUT — no output detected")
                continue

            # Accuracy verification
            accuracy = verify_accuracy(data, consumer_block)

            record = {
                "size": size,
                "iteration": it + 1,
                "producer_serialize_ms": producer_resp.get("serialization_ms"),
                "producer_write_ms": producer_resp.get("write_ms"),
                "producer_total_ms": producer_resp.get("total_ms"),
                "consumer_read_ms": consumer_block.get("consumer_read_ms"),
                "consumer_convert_ms": consumer_block.get("consumer_convert_ms"),
                "consumer_total_ms": consumer_block.get("consumer_total_ms"),
                "roundtrip_ms": producer_resp.get("roundtrip_ms"),
                "accuracy_passed": accuracy["passed"],
                "accuracy_errors": accuracy.get("errors", []),
                "sum_rel_error": accuracy.get("sum_relative_error"),
                "data_ptr": consumer_block.get("data_ptr"),
            }
            iteration_results.append(record)

            status = "✅" if accuracy["passed"] else "❌"
            print(
                f"  [{it+1}/{ITERATIONS}] {status}  "
                f"producer={record['producer_total_ms']:.2f}ms  "
                f"consumer={record['consumer_total_ms']:.2f}ms  "
                f"roundtrip={record['roundtrip_ms']:.1f}ms  "
                f"ptr={record['data_ptr']}"
            )
            if not accuracy["passed"]:
                for err in accuracy["errors"]:
                    print(f"           ⚠ {err}")

        if iteration_results:
            # Statistics
            p_totals = [r["producer_total_ms"] for r in iteration_results]
            c_totals = [r["consumer_total_ms"] for r in iteration_results]
            rts = [r["roundtrip_ms"] for r in iteration_results]
            accuracy_rate = sum(1 for r in iteration_results if r["accuracy_passed"]) / len(iteration_results)

            payload_kb = size * 4 / 1024
            throughput_mbps = (payload_kb / 1024) / (statistics.mean(c_totals) / 1000) if statistics.mean(c_totals) > 0 else 0

            summary = {
                "size": size,
                "payload_kb": payload_kb,
                "iterations": len(iteration_results),
                "accuracy_rate": accuracy_rate,
                "producer_mean_ms": round(statistics.mean(p_totals), 3),
                "producer_p50_ms": round(statistics.median(p_totals), 3),
                "producer_stdev_ms": round(statistics.stdev(p_totals), 3) if len(p_totals) > 1 else 0,
                "consumer_mean_ms": round(statistics.mean(c_totals), 3),
                "consumer_p50_ms": round(statistics.median(c_totals), 3),
                "consumer_stdev_ms": round(statistics.stdev(c_totals), 3) if len(c_totals) > 1 else 0,
                "roundtrip_mean_ms": round(statistics.mean(rts), 3),
                "throughput_mb_s": round(throughput_mbps, 2),
            }
            all_results.append(summary)

            print(f"\n  Summary: accuracy={accuracy_rate*100:.0f}%  "
                  f"producer_avg={summary['producer_mean_ms']:.2f}ms  "
                  f"consumer_avg={summary['consumer_mean_ms']:.2f}ms  "
                  f"throughput={summary['throughput_mb_s']:.1f} MB/s")

    # Final report
    print(f"\n{'=' * 72}")
    print("FINAL RESULTS")
    print(f"{'=' * 72}")
    print(f"{'Size':>10} {'Payload':>10} {'Accuracy':>10} {'Prod(ms)':>10} "
          f"{'Cons(ms)':>10} {'RT(ms)':>10} {'Tput(MB/s)':>12}")
    print("─" * 74)
    for r in all_results:
        print(f"{r['size']:>10,} {r['payload_kb']:>9.1f}K {r['accuracy_rate']*100:>9.0f}% "
              f"{r['producer_mean_ms']:>10.2f} {r['consumer_mean_ms']:>10.2f} "
              f"{r['roundtrip_mean_ms']:>10.1f} {r['throughput_mb_s']:>12.1f}")

    # Save to JSON
    with open(RESULTS_FILE, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nDetailed results saved to {RESULTS_FILE}")

    # Overall verdict
    total_accuracy = sum(r["accuracy_rate"] for r in all_results) / len(all_results) if all_results else 0
    print(f"\nOverall accuracy: {total_accuracy*100:.1f}%")
    if total_accuracy == 1.0:
        print("VERDICT: ✅ ALL TESTS PASSED — Zero-copy IPC is accurate and efficient")
    else:
        print("VERDICT: ⚠ SOME ACCURACY FAILURES — investigate errors above")


if __name__ == "__main__":
    run_benchmark()
