# modules/discovery/host_discovery.py

import subprocess
import threading
from queue import Queue
from threading import Event
from typing import List


class HostDiscovery:

    def __init__(self, timeout=1, retries=3, workers=20, logger=None, progress_cb=None):
        self.timeout = timeout
        self.retries = retries
        self.workers = workers
        self.logger = logger or (lambda msg, lvl="INFO": None)
        self.progress_cb = progress_cb

        self.queue = Queue()
        self.alive_queue = Queue()
        self.finished = Event()

        self.total = 1
        self.done = 0
        self._lock = threading.Lock()

    def _ping(self, ip: str) -> bool:
        try:
            proc = subprocess.run(
                ["ping", "-n", str(self.retries), ip],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=self.retries * self.timeout + 1
            )
            return proc.returncode == 0
        except Exception:
            return False

    def _worker(self):
        while True:
            ip = self.queue.get()
            if ip is None:
                self.queue.task_done()
                break

            if self._ping(ip):
                self.alive_queue.put(ip)

            with self._lock:
                self.done += 1
                percent = int(self.done * 100 / self.total) if self.total else 100
                if self.progress_cb:
                    self.progress_cb("ping", percent)
            self.queue.task_done()

    def discover(self, targets: List[str]):
        """Discover alive hosts from `targets` using multiple worker threads.
        This method is blocking and will populate `self.alive_queue` with live hosts.
        """
        # reset state
        self.total = max(1, len(targets))
        self.done = 0
        self.finished.clear()

        # start worker threads
        for _ in range(self.workers):
            threading.Thread(target=self._worker, daemon=True).start()

        # enqueue targets
        for ip in targets:
            self.queue.put(ip)

        # Wait for all tasks to finish
        self.queue.join()

        # stop workers
        for _ in range(self.workers):
            self.queue.put(None)

        # capture total alive hosts now (before consumers remove them)
        alive_count = self.alive_queue.qsize()
        # store for external consumers (e.g., ScanManager) to use as denominator
        self.alive_total = alive_count

        self.finished.set()

        # summary
        self.logger(f"[PING] Hoàn tất: {alive_count} host đang hoạt động", "SUCCESS")
        # optionally emit final progress
        if self.progress_cb:
            self.progress_cb("ping", 100)
