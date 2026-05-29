
import json
import os
import time
import logging

import numpy as np
import pyarrow as pa
import pyarrow.ipc as ipc
import requests as http_client
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from filelock import FileLock


SHM_PATH: str = os.getenv("SHARED_MEM_PATH", "/tmp/shared_memory.arrow")
LOCK_PATH: str = f"{SHM_PATH}.lock"
READY_PATH: str = f"{SHM_PATH}.ready"
CONSUMER_URL: str = os.getenv("CONSUMER_URL", "http://localhost:8001")

# Strict Arrow schema — float32 guarantees zero-copy into torch.float32
ARROW_SCHEMA = pa.schema([("values", pa.float32())])

logging.basicConfig(level=logging.INFO, format="%(asctime)s [PRODUCER] %(message)s")
log = logging.getLogger("producer")


app = FastAPI(title="Zero-Copy Producer", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)



class ProcessRequest(BaseModel):
    data: list[float]


class ProcessResponse(BaseModel):
    status: str
    num_elements: int
    serialization_ms: float
    write_ms: float
    total_ms: float


class BenchmarkRequest(BaseModel):
    size: int


class ArrowBenchmarkResponse(BaseModel):
    pipeline: str
    num_elements: int
    # Producer-side timing
    serialization_ms: float
    write_ms: float
    # Consumer-side timing
    consumer_read_ms: float
    consumer_convert_ms: float
    consumer_total_ms: float
    # End-to-end
    total_e2e_ms: float
    # Memory footprint
    arrow_bytes: int


class JsonBenchmarkResponse(BaseModel):
    pipeline: str
    num_elements: int
    # Producer-side timing
    json_serialize_ms: float
    http_transfer_ms: float
    # Consumer-side timing
    consumer_deserialize_ms: float
    consumer_convert_ms: float
    consumer_total_ms: float
    # End-to-end
    total_e2e_ms: float
    # Memory footprint
    json_bytes: int


def _write_arrow_to_shm(data: list[float]) -> tuple[float, float]:
    """Write float array to shared-memory Arrow IPC file.

    Returns (serialization_ms, write_ms).
    """
    t0 = time.perf_counter()

    arr = pa.array(data, type=pa.float32())
    batch = pa.record_batch([arr], schema=ARROW_SCHEMA)

    t_ser = time.perf_counter()

    lock = FileLock(LOCK_PATH)
    with lock:
        os.makedirs(os.path.dirname(SHM_PATH) or ".", exist_ok=True)
        sink = pa.OSFile(SHM_PATH, "wb")
        writer = ipc.RecordBatchStreamWriter(sink, ARROW_SCHEMA)
        writer.write_batch(batch)
        writer.close()
        sink.close()

        with open(READY_PATH, "w") as f:
            f.write(str(time.time()))

    t_end = time.perf_counter()
    return (t_ser - t0) * 1000, (t_end - t_ser) * 1000


@app.post("/process", response_model=ProcessResponse)
async def process(request: ProcessRequest):
    """Accept an array of floats, serialize to Arrow RecordBatch, and write
    directly to the shared-memory IPC file."""
    if not request.data:
        raise HTTPException(status_code=400, detail="data array must not be empty")

    t_start = time.perf_counter()
    serialization_ms, write_ms = _write_arrow_to_shm(request.data)
    t_end = time.perf_counter()

    total_ms = (t_end - t_start) * 1000

    log.info(
        "Wrote %d elements | serialize=%.4fms  write=%.4fms  total=%.4fms",
        len(request.data), serialization_ms, write_ms, total_ms,
    )

    return ProcessResponse(
        status="ok",
        num_elements=len(request.data),
        serialization_ms=round(serialization_ms, 4),
        write_ms=round(write_ms, 4),
        total_ms=round(total_ms, 4),
    )



@app.post("/benchmark_arrow", response_model=ArrowBenchmarkResponse)
async def benchmark_arrow(req: BenchmarkRequest):
    """Self-contained Arrow IPC benchmark.

    1. Generate N random floats.
    2. Serialize → Arrow RecordBatch → write to shared memory.
    3. Call consumer /consume_arrow to read zero-copy.
    4. Return full timing breakdown.
    """
    if req.size < 1:
        raise HTTPException(status_code=400, detail="size must be >= 1")

    t_e2e_start = time.perf_counter()

    # Generate deterministic test data
    data = np.random.default_rng(42).random(req.size, dtype=np.float64).tolist()

    # Producer: serialize + write to shared memory
    try:
        ser_ms, write_ms = _write_arrow_to_shm(data)
    except Exception as exc:
        log.error("Arrow write failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # Get Arrow buffer size on disk
    try:
        arrow_bytes = os.path.getsize(SHM_PATH)
    except FileNotFoundError:
        arrow_bytes = 0

    # Call consumer to read + convert
    try:
        resp = http_client.post(
            f"{CONSUMER_URL}/consume_arrow",
            timeout=120,
        )
        resp.raise_for_status()
        consumer_data = resp.json()
    except Exception as exc:
        log.error("Consumer /consume_arrow call failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Consumer error: {exc}") from exc

    t_e2e_end = time.perf_counter()

    log.info(
        "BENCHMARK ARROW | size=%d  ser=%.4fms  write=%.4fms  "
        "c_read=%.4fms  c_conv=%.4fms  e2e=%.4fms",
        req.size, ser_ms, write_ms,
        consumer_data["read_ms"], consumer_data["convert_ms"],
        (t_e2e_end - t_e2e_start) * 1000,
    )

    return ArrowBenchmarkResponse(
        pipeline="arrow_ipc_zero_copy",
        num_elements=req.size,
        serialization_ms=round(ser_ms, 4),
        write_ms=round(write_ms, 4),
        consumer_read_ms=round(consumer_data["read_ms"], 4),
        consumer_convert_ms=round(consumer_data["convert_ms"], 4),
        consumer_total_ms=round(consumer_data["total_ms"], 4),
        total_e2e_ms=round((t_e2e_end - t_e2e_start) * 1000, 4),
        arrow_bytes=arrow_bytes,
    )



@app.post("/benchmark_json", response_model=JsonBenchmarkResponse)
async def benchmark_json(req: BenchmarkRequest):
    """Self-contained JSON/REST baseline benchmark.

    1. Generate N random floats.
    2. Serialize to JSON string (json.dumps).
    3. POST JSON payload to consumer /consume_json via HTTP.
    4. Return full timing breakdown.
    """
    if req.size < 1:
        raise HTTPException(status_code=400, detail="size must be >= 1")

    t_e2e_start = time.perf_counter()

    # Generate deterministic test data (same seed as Arrow for fairness)
    data = np.random.default_rng(42).random(req.size, dtype=np.float64).tolist()

    t_ser_start = time.perf_counter()
    json_payload = json.dumps({"data": data})
    json_bytes_payload = json_payload.encode("utf-8")
    t_ser_end = time.perf_counter()
    json_serialize_ms = (t_ser_end - t_ser_start) * 1000


    t_transfer_start = time.perf_counter()
    try:
        resp = http_client.post(
            f"{CONSUMER_URL}/consume_json",
            data=json_bytes_payload,
            headers={"Content-Type": "application/json"},
            timeout=120,
        )
        resp.raise_for_status()
        consumer_data = resp.json()
    except Exception as exc:
        log.error("Consumer /consume_json call failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Consumer error: {exc}") from exc
    t_transfer_end = time.perf_counter()
    http_transfer_ms = (t_transfer_end - t_transfer_start) * 1000

    t_e2e_end = time.perf_counter()

    log.info(
        "BENCHMARK JSON  | size=%d  json_ser=%.4fms  http=%.4fms  "
        "c_deser=%.4fms  c_conv=%.4fms  e2e=%.4fms",
        req.size, json_serialize_ms, http_transfer_ms,
        consumer_data["deserialize_ms"], consumer_data["convert_ms"],
        (t_e2e_end - t_e2e_start) * 1000,
    )

    return JsonBenchmarkResponse(
        pipeline="traditional_json_rest",
        num_elements=req.size,
        json_serialize_ms=round(json_serialize_ms, 4),
        http_transfer_ms=round(http_transfer_ms, 4),
        consumer_deserialize_ms=round(consumer_data["deserialize_ms"], 4),
        consumer_convert_ms=round(consumer_data["convert_ms"], 4),
        consumer_total_ms=round(consumer_data["total_ms"], 4),
        total_e2e_ms=round((t_e2e_end - t_e2e_start) * 1000, 4),
        json_bytes=len(json_bytes_payload),
    )


@app.get("/health")
async def health():
    return {"status": "healthy"}
