# modules/scan_manager.py

from typing import Dict, Any

from modules.pipelines.basic_pipeline import BasicPipeline
from modules.pipelines.authenticated_pipeline import AuthenticatedPipeline


class ScanManager:

    def __init__(self, config: dict, logger=None, progress_cb=None, stop_event=None):
        self.config = config
        self.logger = logger or (lambda msg, lvl="INFO": None)
        self.progress_cb = progress_cb
        self.stop_event = stop_event
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
        # BASIC SCAN: SKIP PING HERE
        # Pipeline will handle DNS → Asset Discovery → Ping → Scan
        # =========================
        results = []
        scanned_count = 0
        self.alive_total = len(targets)

        for target in targets:
            # Check if stop requested before starting new target
            if self.stop_event and self.stop_event.is_set():
                self.logger("Scan stop requested — aborting remaining targets", "WARN")
                break
            # ---- RUN BASIC PIPELINE ----
            result = self._run_basic(target, host_result_cb)

            # Fan-out multi-host results if provided by pipeline
            if isinstance(result, dict) and result.get("multi_host"):
                # Fan-out the per-host results only; BasicPipeline already invoked
                # host_result_cb for each IP, so we avoid sending the aggregate here
                for ip, rep in result.get("per_host_results", []):
                    results.append({"host": ip, "result": rep})
            else:
                results.append({"host": target, "result": result})

            # Call host-level callback (if provided) so UI can update incrementally
            # For multi-host basic scans, per-IP callbacks have already been emitted
            if host_result_cb and not (isinstance(result, dict) and result.get("multi_host")):
                try:
                    host_result_cb(target, result)
                except Exception:
                    pass

            # ---- UPDATE SCAN PROGRESS ----
            scanned_count += 1
            if self.progress_cb:
                percent = int(scanned_count * 100 / self.alive_total)
                self.progress_cb("scan", percent, f"Scanning {target}")

        return results

    # ==================================================
    # INTERNAL
    # ==================================================
    def _run_basic(self, target, host_result_cb=None):
        pipeline = BasicPipeline(
            self.config,
            logger=self.logger,
            progress_cb=self.progress_cb,
            host_result_cb=host_result_cb,
            stop_event=self.stop_event
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
