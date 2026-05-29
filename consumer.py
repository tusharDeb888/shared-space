
import json
import os
import sys
import time
import logging
import threading

import numpy as np
import pyarrow as pa
import pyarrow.ipc as ipc
import torch
from fastapi import FastAPI, Request, HTTPException
from filelock import FileLock
from pydantic import BaseModel

SHM_PATH: str = os.getenv("SHARED_MEM_PATH", "/tmp/shared_memory.arrow")
LOCK_PATH: str = f"{SHM_PATH}.lock"
READY_PATH: str = f"{SHM_PATH}.ready"
POLL_INTERVAL_S: float = 0.1  # 100 ms

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CONSUMER] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("consumer")


class ArrowConsumeResponse(BaseModel):
    read_ms: float
    convert_ms: float
    total_ms: float
    tensor_shape: list[int]
    tensor_sum: float


class JsonConsumeResponse(BaseModel):
    deserialize_ms: float
    convert_ms: float
    total_ms: float
    tensor_shape: list[int]
    tensor_sum: float



class ArrowMemoryReader:
    """Reads an Arrow IPC stream from a memory-mapped file and produces a
    zero-copy PyTorch tensor."""

    def __init__(self, shm_path: str, lock_path: str) -> None:
        self._shm_path = shm_path
        self._lock = FileLock(lock_path)

    def read_tensor(self) -> tuple[torch.Tensor, float, float, float]:
        """Read the shared-memory Arrow file under lock and return a
        zero-copy float32 tensor plus timing breakdown.

        Returns
        -------
        (tensor, read_ms, convert_ms, total_ms)
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

        column: pa.Array = batch.column("values")

        # This will raise pa.ArrowInvalid if a copy would be required
        np_array = column.to_numpy(zero_copy_only=True)

        # torch.from_numpy shares the same memory — no copy
        tensor = torch.from_numpy(np_array)

        t_end = time.perf_counter()

        read_ms = (t_read - t_start) * 1000
        convert_ms = (t_end - t_read) * 1000
        total_ms = (t_end - t_start) * 1000

        return tensor, read_ms, convert_ms, total_ms


app = FastAPI(title="Zero-Copy Consumer", version="2.0.0")
arrow_reader = ArrowMemoryReader(SHM_PATH, LOCK_PATH)


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/consume_arrow", response_model=ArrowConsumeResponse)
async def consume_arrow():
    """Read the Arrow IPC shared-memory file and return timing metrics."""
    try:
        tensor, read_ms, convert_ms, total_ms = arrow_reader.read_tensor()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Shared memory file not found")
    except pa.ArrowInvalid as exc:
        raise HTTPException(
            status_code=500,
            detail=f"ZERO-COPY FAILED — architecture violation: {exc}",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    log.info(
        "ARROW CONSUME | shape=%s  read=%.4fms  convert=%.4fms  total=%.4fms",
        tensor.shape, read_ms, convert_ms, total_ms,
    )

    return ArrowConsumeResponse(
        read_ms=round(read_ms, 4),
        convert_ms=round(convert_ms, 4),
        total_ms=round(total_ms, 4),
        tensor_shape=list(tensor.shape),
        tensor_sum=round(tensor.sum().item(), 4),
    )


@app.post("/consume_json", response_model=JsonConsumeResponse)
async def consume_json(request: Request):
    """Accept raw JSON body, deserialize with json.loads(), convert to tensor.
    Intentionally performs full memory copy to simulate the traditional pipeline.
    """
    t_start = time.perf_counter()


    raw_body = await request.body()
    parsed = json.loads(raw_body)
    float_list = parsed.get("data", [])

    if not float_list:
        raise HTTPException(status_code=400, detail="data array must not be empty")

    t_deserialized = time.perf_counter()


    np_array = np.array(float_list, dtype=np.float32)  # full heap copy
    tensor = torch.from_numpy(np_array)

    t_end = time.perf_counter()

    deserialize_ms = (t_deserialized - t_start) * 1000
    convert_ms = (t_end - t_deserialized) * 1000
    total_ms = (t_end - t_start) * 1000

    log.info(
        "JSON CONSUME  | shape=%s  deser=%.4fms  convert=%.4fms  total=%.4fms",
        tensor.shape, deserialize_ms, convert_ms, total_ms,
    )

    return JsonConsumeResponse(
        deserialize_ms=round(deserialize_ms, 4),
        convert_ms=round(convert_ms, 4),
        total_ms=round(total_ms, 4),
        tensor_shape=list(tensor.shape),
        tensor_sum=round(tensor.sum().item(), 4),
    )



def _polling_loop() -> None:
    log.info("Polling thread started — monitoring %s every %.0f ms",
             SHM_PATH, POLL_INTERVAL_S * 1000)

    reader = ArrowMemoryReader(SHM_PATH, LOCK_PATH)

    while True:
        if not os.path.exists(READY_PATH):
            time.sleep(POLL_INTERVAL_S)
            continue

        try:
            tensor, read_ms, convert_ms, total_ms = reader.read_tensor()

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
            log.info("Inference placeholder — tensor sum: %.4f", tensor.sum().item())

            try:
                os.remove(READY_PATH)
            except FileNotFoundError:
                pass

        except FileNotFoundError:
            log.warning("Shared memory file disappeared before read")
            time.sleep(POLL_INTERVAL_S)
        except pa.ArrowInvalid as exc:
            log.error("ZERO-COPY FAILED — architecture violation: %s", exc)
            sys.exit(1)
        except Exception as exc:
            log.error("Unexpected error: %s", exc)
            time.sleep(POLL_INTERVAL_S)


@app.on_event("startup")
async def start_polling_thread():
    thread = threading.Thread(target=_polling_loop, daemon=True)
    thread.start()
    log.info("Background polling thread launched")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
