import asyncio
import os
import tempfile
import time
import unittest

from fastapi import HTTPException

import consumer
import producer

MAX_ACCEPTABLE_TOTAL_LATENCY_MS = 5000.0
MAX_ACCEPTABLE_READ_LATENCY_MS = 2000.0
EFFICIENCY_SAMPLE_SIZE = 5000
FLOAT_COMPARISON_PLACES = 5


class AccuracyEfficiencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self._shm_path = os.path.join(self._tmpdir.name, "shared_memory.arrow")

        self._old_producer_paths = (
            producer.SHM_PATH,
            producer.LOCK_PATH,
            producer.READY_PATH,
        )
        producer.SHM_PATH = self._shm_path
        producer.LOCK_PATH = f"{self._shm_path}.lock"
        producer.READY_PATH = f"{self._shm_path}.ready"
        self.addCleanup(self._restore_producer_paths)

    def _restore_producer_paths(self) -> None:
        old_shm_path, old_lock_path, old_ready_path = self._old_producer_paths
        producer.SHM_PATH = old_shm_path
        producer.LOCK_PATH = old_lock_path
        producer.READY_PATH = old_ready_path

    def test_process_rejects_empty_input(self) -> None:
        with self.assertRaises(HTTPException) as context:
            asyncio.run(producer.process(producer.ProcessRequest(data=[])))

        self.assertEqual(context.exception.status_code, 400)

    def test_round_trip_accuracy_and_zero_copy(self) -> None:
        input_data = [1.25, -3.5, 8.0, 0.125, 42.75]
        response = asyncio.run(producer.process(producer.ProcessRequest(data=input_data)))

        self.assertEqual(response.status, "ok")
        self.assertEqual(response.num_elements, len(input_data))
        self.assertTrue(os.path.exists(producer.READY_PATH))

        reader = consumer.ArrowMemoryReader(producer.SHM_PATH, producer.LOCK_PATH)
        tensor = reader.read_tensor()

        self.assertEqual(tensor.shape[0], len(input_data))
        for expected, actual in zip(input_data, tensor.tolist()):
            self.assertAlmostEqual(actual, expected, places=FLOAT_COMPARISON_PLACES)

        np_view = tensor.numpy()
        self.assertEqual(
            tensor.data_ptr(),
            np_view.ctypes.data,
            "Tensor and NumPy view should share the same backing memory address",
        )

    def test_consumer_missing_file_raises(self) -> None:
        missing_path = os.path.join(self._tmpdir.name, "missing.arrow")
        reader = consumer.ArrowMemoryReader(missing_path, f"{missing_path}.lock")
        with self.assertRaises(FileNotFoundError):
            reader.read_tensor()

    def test_basic_efficiency_signals(self) -> None:
        input_data = [float(i) for i in range(EFFICIENCY_SAMPLE_SIZE)]
        response = asyncio.run(producer.process(producer.ProcessRequest(data=input_data)))

        self.assertGreaterEqual(response.serialization_ms, 0.0)
        self.assertGreaterEqual(response.write_ms, 0.0)
        self.assertGreaterEqual(response.total_ms, 0.0)
        self.assertLess(response.total_ms, MAX_ACCEPTABLE_TOTAL_LATENCY_MS)

        reader = consumer.ArrowMemoryReader(producer.SHM_PATH, producer.LOCK_PATH)
        start = time.perf_counter()
        tensor = reader.read_tensor()
        elapsed_ms = (time.perf_counter() - start) * 1000

        self.assertEqual(tensor.numel(), len(input_data))
        self.assertLess(elapsed_ms, MAX_ACCEPTABLE_READ_LATENCY_MS)


if __name__ == "__main__":
    unittest.main()
