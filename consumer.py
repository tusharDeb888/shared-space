"""
consumer.py — Node B (PyTorch Consumer)

Monitors the POSIX shared memory file for new Arrow IPC data written by the
producer.  Reads the RecordBatch, enforces zero-copy conversion to a PyTorch
tensor, and prints shape / memory address / latency.

Zero-copy chain:
    pa.Column → .to_numpy(zero_copy_only=True) → torch.from_numpy()

Concurrency: filelock.FileLock wraps the read region.
Signaling:   Polls for the .ready sentinel file created by the producer.
"""

import os
import sys
import time
import logging

import pyarrow as pa
import pyarrow.ipc as ipc
import torch
from filelock import FileLock

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SHM_PATH: str = os.getenv("SHARED_MEM_PATH", "/dev/shm/shared_memory.arrow")
LOCK_PATH: str = f"{SHM_PATH}.lock"
READY_PATH: str = f"{SHM_PATH}.ready"
POLL_INTERVAL_S: float = 0.1  # 100 ms

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CONSUMER] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("consumer")


# ---------------------------------------------------------------------------
# Core: read Arrow IPC → zero-copy → PyTorch tensor
# ---------------------------------------------------------------------------
class ArrowMemoryReader:
    """Reads an Arrow IPC stream from a memory-mapped file and produces a
    zero-copy PyTorch tensor."""

    def __init__(self, shm_path: str, lock_path: str) -> None:
        self._shm_path = shm_path
        self._lock = FileLock(lock_path)

    def read_tensor(self) -> torch.Tensor:
        """Read the shared-memory Arrow file under lock and return a
        zero-copy float32 tensor.

        Raises
        ------
        FileNotFoundError
            If the shared-memory file does not exist yet.
        pa.ArrowInvalid
            If zero-copy conversion fails (schema mismatch).
        """
        t_start = time.perf_counter()

        try:
            with self._lock:
                source = pa.OSFile(self._shm_path, "rb")
                reader = ipc.RecordBatchStreamReader(source)
                batch: pa.RecordBatch = reader.read_next_batch()
                reader.close()
                source.close()

        except FileNotFoundError:
            raise
        except Exception as exc:
            log.error("Failed to read shared memory: %s", exc)
            raise

        t_read = time.perf_counter()

        # ------------------------------------------------------------------
        # Zero-copy chain: Arrow column → NumPy (zero_copy_only) → PyTorch
        # ------------------------------------------------------------------
        column: pa.Array = batch.column("values")

        # This will raise pa.ArrowInvalid if a copy would be required
        np_array = column.to_numpy(zero_copy_only=True)

        # torch.from_numpy shares the same memory — no copy
        tensor = torch.from_numpy(np_array)

        t_end = time.perf_counter()

        read_ms = (t_read - t_start) * 1000
        convert_ms = (t_end - t_read) * 1000
        total_ms = (t_end - t_start) * 1000

        log.info("=" * 60)
        log.info("TENSOR RECEIVED — ZERO-COPY VERIFIED")
        log.info("  Tensor shape : %s", tensor.shape)
        log.info("  Tensor dtype : %s", tensor.dtype)
        log.info("  Data pointer : 0x%x", tensor.data_ptr())
        log.info("  First 5 vals : %s", tensor[:5].tolist())
        log.info("  Read latency : %.4f ms", read_ms)
        log.info("  Convert lat. : %.4f ms", convert_ms)
        log.info("  Total latency: %.4f ms", total_ms)
        log.info("=" * 60)

        return tensor


# ---------------------------------------------------------------------------
# Main polling loop
# ---------------------------------------------------------------------------
def main() -> None:
    log.info("Consumer started — polling %s every %.0f ms",
             SHM_PATH, POLL_INTERVAL_S * 1000)

    reader = ArrowMemoryReader(SHM_PATH, LOCK_PATH)

    while True:
        # Wait for the sentinel file that signals new data
        if not os.path.exists(READY_PATH):
            time.sleep(POLL_INTERVAL_S)
            continue

        try:
            tensor = reader.read_tensor()

            # ----------------------------------------------------------
            # Placeholder: run inference here
            # For now, just confirm the tensor is usable on the device
            # ----------------------------------------------------------
            log.info("Inference placeholder — tensor sum: %.4f", tensor.sum().item())

            # Remove sentinel so we wait for the next write
            try:
                os.remove(READY_PATH)
            except FileNotFoundError:
                pass  # producer may have already cleaned up

        except FileNotFoundError:
            log.warning("Shared memory file disappeared before read")
            time.sleep(POLL_INTERVAL_S)
        except pa.ArrowInvalid as exc:
            log.error("ZERO-COPY FAILED — architecture violation: %s", exc)
            sys.exit(1)
        except Exception as exc:
            log.error("Unexpected error: %s", exc)
            time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main()
