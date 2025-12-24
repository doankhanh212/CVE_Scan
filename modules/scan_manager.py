# modules/scan_manager.py

from typing import Dict, Any
from threading import Thread
from queue import Empty

from modules.pipelines.basic_pipeline import BasicPipeline
from modules.pipelines.authenticated_pipeline import AuthenticatedPipeline
from modules.discovery.host_discovery import HostDiscovery


class ScanManager:

    def __init__(self, config: dict, logger=None, progress_cb=None):
        self.config = config
        self.logger = logger or (lambda msg, lvl="INFO": None)
        self.progress_cb = progress_cb
        self.logger("ScanManager initialized", "SYSTEM")

    # ==================================================
    def scan(self, targets, authenticated=False, auth_data=None, host_result_cb=None):
        """
        progress_cb(phase, percent, message)
        phase = "ping" | "scan"

        host_result_cb: optional callable(host, result) called each time a host is scanned
        """

        self.logger(f"Start scan with {len(targets)} targets", "SYSTEM")

        # =========================
        # AUTHENTICATED SCAN SKIP PING
        # =========================
        if authenticated:
            self.logger("Authenticated scan mode: skipping ICMP ping (will try direct SSH/WinRM)", "INFO")
            results = []
            alive_scanned = 0
            self.alive_total = len(targets)
            
            for host in targets:
                # ---- RUN AUTHENTICATED PIPELINE ----
                result = self._run_authenticated(host, auth_data)
                results.append({"host": host, "result": result})

                # Call host-level callback (if provided) so UI can update incrementally
                if host_result_cb:
                    try:
                        host_result_cb(host, result)
                    except Exception:
                        pass

                # ---- UPDATE SCAN PROGRESS ----
                alive_scanned += 1
                if self.progress_cb:
                    percent = int(alive_scanned * 100 / self.alive_total)
                    self.progress_cb("scan", percent, f"Scanning {host}")
            
            return results

        # =========================
        # HOST DISCOVERY (BASIC SCAN ONLY)
        # =========================
        discovery = HostDiscovery(
            timeout=1,
            retries=3,
            workers=20,
            logger=self.logger,
            progress_cb=self.progress_cb
        )

        ping_thread = Thread(
            target=discovery.discover,
            args=(targets,),
            daemon=True
        )
        ping_thread.start()

        results = []
        alive_scanned = 0
        # initialize estimated total to the number of targets to avoid
        # percent jumping to 100 on the first scanned alive host
        self.alive_total = max(1, len(targets))

        # =========================
        # CONSUMER LOOP (BASIC SCAN ONLY)
        # =========================
        while True:
            try:
                host = discovery.alive_queue.get(timeout=2)
            except Empty:
                if discovery.finished.is_set():
                    # discovery finished — use the actual number of alive hosts discovered
                    # (HostDiscovery sets `alive_total` when it finishes)
                    discovered_alive = getattr(discovery, 'alive_total', discovery.alive_queue.qsize())
                    self.alive_total = max(1, discovered_alive)
                    break
                continue

            # ---- RUN PIPELINE (BASIC SCAN) ----
            if authenticated:
                result = self._run_authenticated(host, auth_data)
            else:
                result = self._run_basic(host)

            results.append({"host": host, "result": result})

            # Call host-level callback (if provided) so UI can update incrementally
            if host_result_cb:
                try:
                    host_result_cb(host, result)
                except Exception:
                    pass

            # ---- UPDATE SCAN PROGRESS ----
            alive_scanned += 1
            if self.progress_cb:
                percent = int(alive_scanned * 100 / self.alive_total)
                self.progress_cb("scan", percent, f"Scanning {host}")

        return results

    # ==================================================
    # INTERNAL
    # ==================================================
    def _run_basic(self, target):
        pipeline = BasicPipeline(
            self.config,
            logger=self.logger,
            progress_cb=self.progress_cb
        )
        return pipeline.execute(target)

    def _run_authenticated(self, target: str, auth_data: Dict[str, Any]):
        if not auth_data:
            raise ValueError("auth_data is required")

        pipeline = AuthenticatedPipeline(
            self.config,
            logger_cb=self.logger
        )
        return pipeline.execute(target, auth_data)
