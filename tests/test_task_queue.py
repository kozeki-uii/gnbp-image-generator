import threading
import time
import unittest

from config.config_mgr import GenConfig
from core.task_queue import TaskManager


class RecordingClient:
    def __init__(self, delay=0.1):
        self.delay = delay
        self.lock = threading.Lock()
        self.active = 0
        self.peak = 0

    def generate(self, config):
        with self.lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        time.sleep(self.delay)
        with self.lock:
            self.active -= 1
        return False, "offline test"


class BlockingClient(RecordingClient):
    def __init__(self, expected_active):
        super().__init__(delay=0)
        self.expected_active = expected_active
        self.all_started = threading.Event()
        self.release = threading.Event()

    def generate(self, config):
        with self.lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
            if self.active == self.expected_active:
                self.all_started.set()
        self.release.wait(timeout=2)
        with self.lock:
            self.active -= 1
        return False, "offline test"


class TaskManagerTests(unittest.TestCase):
    @staticmethod
    def make_config():
        return GenConfig(
            api_url="https://example.invalid",
            api_key="key",
            model="model",
            prompt="prompt",
            aspect_ratio="1:1",
            resolution="1K",
            output_dir="unused",
        )

    def test_scale_down_applies_before_idle_workers_start_new_tasks(self):
        manager = TaskManager(max_workers=3)
        client = RecordingClient()
        manager.gemini_client = client
        config = self.make_config()

        # Let all three workers block in queue.get(), then reduce the limit.
        time.sleep(0.05)
        manager.set_max_workers(1)
        for _ in range(3):
            manager.add_task(config)

        manager.queue.join()
        manager.active = False

        self.assertEqual(client.peak, 1)

    def test_scale_down_does_not_interrupt_running_tasks(self):
        manager = TaskManager(max_workers=3)
        client = BlockingClient(expected_active=3)
        manager.gemini_client = client
        for _ in range(3):
            manager.add_task(self.make_config())

        self.assertTrue(client.all_started.wait(timeout=1))
        manager.set_max_workers(1)
        time.sleep(0.05)

        with client.lock:
            self.assertEqual(client.active, 3)

        client.release.set()
        manager.queue.join()
        manager.active = False


if __name__ == "__main__":
    unittest.main()
