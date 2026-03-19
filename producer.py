"""
producer.py — Node A (FastAPI Producer)

Receives arrays of floats via POST /process, serializes them as an Apache Arrow
RecordBatch, and streams the IPC data directly into a POSIX shared memory file
using pyarrow.OSFile.  No intermediate Python-heap buffers.

Concurrency: filelock.FileLock wraps the write region.
Signaling:   A .ready sentinel file notifies the consumer.
"""

import os
import time
import logging

import numpy as np
import pyarrow as pa
import pyarrow.ipc as ipc
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from filelock import FileLock

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SHM_PATH: str = os.getenv("SHARED_MEM_PATH", "/dev/shm/shared_memory.arrow")
LOCK_PATH: str = f"{SHM_PATH}.lock"
READY_PATH: str = f"{SHM_PATH}.ready"

# Strict Arrow schema — float32 guarantees zero-copy into torch.float32
ARROW_SCHEMA = pa.schema([("values", pa.float32())])

logging.basicConfig(level=logging.INFO, format="%(asctime)s [PRODUCER] %(message)s")
log = logging.getLogger("producer")

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Zero-Copy Producer", version="1.0.0")


class ProcessRequest(BaseModel):
    data: list[float]


class ProcessResponse(BaseModel):
    status: str
    num_elements: int
    serialization_ms: float
    write_ms: float
    total_ms: float


@app.post("/process", response_model=ProcessResponse)
async def process(request: ProcessRequest):
    """
    Accept an array of floats, serialize to Arrow RecordBatch, and write
    directly to the shared-memory IPC file.
    """
    if not request.data:
        raise HTTPException(status_code=400, detail="data array must not be empty")

    t_start = time.perf_counter()

    # -----------------------------------------------------------------------
    # 1. Build the Arrow RecordBatch (in-process, zero-alloc where possible)
    # -----------------------------------------------------------------------
    arr = pa.array(request.data, type=pa.float32())
    batch = pa.record_batch([arr], schema=ARROW_SCHEMA)

    t_serialized = time.perf_counter()

    # -----------------------------------------------------------------------
    # 2. Write directly to shared memory via pa.OSFile — NO BytesIO copy
    # -----------------------------------------------------------------------
    lock = FileLock(LOCK_PATH)
    try:
        with lock:
            # Ensure parent directory exists (for local dev outside /dev/shm)
            os.makedirs(os.path.dirname(SHM_PATH) or ".", exist_ok=True)

            sink = pa.OSFile(SHM_PATH, "wb")
            writer = ipc.RecordBatchStreamWriter(sink, ARROW_SCHEMA)
            writer.write_batch(batch)
            writer.close()
            sink.close()

            # Signal consumer that new data is ready
            with open(READY_PATH, "w") as f:
                f.write(str(time.time()))

    except Exception as exc:
        log.error("Failed to write to shared memory: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    t_end = time.perf_counter()

    serialization_ms = (t_serialized - t_start) * 1000
    write_ms = (t_end - t_serialized) * 1000
    total_ms = (t_end - t_start) * 1000

    log.info(
        "Wrote %d elements | serialize=%.4fms  write=%.4fms  total=%.4fms",
        len(request.data),
        serialization_ms,
        write_ms,
        total_ms,
    )

    return ProcessResponse(
        status="ok",
        num_elements=len(request.data),
        serialization_ms=round(serialization_ms, 4),
        write_ms=round(write_ms, 4),
        total_ms=round(total_ms, 4),
    )


@app.get("/health")
async def health():
    return {"status": "healthy"}
