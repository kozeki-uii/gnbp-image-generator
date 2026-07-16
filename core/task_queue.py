import threading
import time
import queue
import uuid
from dataclasses import asdict
from PySide6.QtCore import QObject, Signal
from config.config_mgr import GenConfig
from core.api_client import GeminiApiClient
from core.gpt_client import GptApiClient


class TaskManager(QObject):
    task_added = Signal(dict)
    task_updated = Signal(dict)
    log_message = Signal(str)

    def __init__(self, max_workers=1):
        super().__init__()
        self.queue = queue.Queue()
        self.active = True
        self.cancelled_tasks = set()
        self.gemini_client = GeminiApiClient(self._log)
        self.gpt_client = GptApiClient(self._log)

        self._lock = threading.Lock()
        self._target_workers = max(1, max_workers)
        self._worker_count = 0
        self._worker_id = 0
        for _ in range(self._target_workers):
            self._spawn_worker()

    def _spawn_worker(self):
        self._worker_id += 1
        t = threading.Thread(target=self._worker, args=(self._worker_id,), daemon=True)
        t.start()
        self._worker_count += 1

    def set_max_workers(self, n):
        n = max(1, min(8, n))
        with self._lock:
            old = self._target_workers
            self._target_workers = n
            if n > old:
                for _ in range(n - old):
                    self._spawn_worker()

    def _retire_if_excess(self):
        with self._lock:
            if self._worker_count > self._target_workers:
                self._worker_count -= 1
                return True
        return False

    def _log(self, msg):
        self.log_message.emit(msg)

    def add_task(self, config: GenConfig):
        task_id = uuid.uuid4().hex[:6]
        if config.api_type == "gpt":
            params_short = f"{config.size} | {config.quality}"
        else:
            params_short = f"{config.aspect_ratio} | {config.resolution}"
        task_data = {
            "id": task_id,
            "config": asdict(config),
            "status": "Waiting",
            "start_time": None,
            "prompt_short": config.prompt.replace('\n', ' '),
            "params_short": params_short
        }
        self.queue.put(task_data)
        self.task_added.emit(task_data)
        return task_id

    def cancel_task(self, task_id):
        self.cancelled_tasks.add(task_id)

    def _worker(self, wid):
        while self.active:
            if self._retire_if_excess():
                return

            try:
                task_dict = self.queue.get(timeout=1)
            except queue.Empty:
                continue

            # A worker may already be blocked in queue.get() when the limit is
            # reduced. Return that still-waiting task before retiring.
            if self._retire_if_excess():
                self.queue.put(task_dict)
                self.queue.task_done()
                return

            tid = task_dict["id"]
            if tid in self.cancelled_tasks:
                self.cancelled_tasks.discard(tid)
                self.task_updated.emit({"id": tid, "status": "Cancelled"})
                self.queue.task_done()
                continue

            start_t = time.time()
            task_dict["start_time"] = start_t
            self.task_updated.emit({"id": tid, "status": "Running...", "start_time": start_t})

            try:
                cfg_data = task_dict["config"]
                valid_keys = GenConfig.__annotations__.keys()
                filtered_data = {k: v for k, v in cfg_data.items() if k in valid_keys}
                config_obj = GenConfig(**filtered_data)

                client = self.gpt_client if config_obj.api_type == "gpt" else self.gemini_client
                success, result = client.generate(config_obj)
                duration = time.time() - start_t
                duration_str = f"{duration:.1f}s"

                if success:
                    self.task_updated.emit({
                        "id": tid, "status": "Success",
                        "path": result, "duration_str": duration_str
                    })
                else:
                    self.task_updated.emit({
                        "id": tid, "status": "Failed",
                        "error_msg": result, "duration_str": duration_str
                    })
                    self._log(f"❌ 任务 {tid} 失败: {result}")
            except Exception as e:
                duration_str = f"{time.time() - start_t:.1f}s"
                self.task_updated.emit({"id": tid, "status": "Error", "duration_str": duration_str})
                self._log(f"💥 严重错误: {e}")

            self.queue.task_done()
