"""Continuous Awareness Observer service tracking system metrics and folder status."""

import os
import time
import psutil
import socket
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from memory import MemoryManager
from logger import get_logger

_log = get_logger("os_observer")


class ContinuousObserver:
    """Monitors OS parameters, hardware, and specific folder changes in a background thread."""

    def __init__(self, memory: MemoryManager, scan_interval: float = 3.0):
        self.memory = memory
        self.scan_interval = max(0.5, float(scan_interval))
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._latest_metrics: Dict[str, Any] = {}
        
        # Paths to monitor
        self.desktop_path = Path(os.path.expanduser("~/Desktop"))
        self.downloads_path = Path(os.path.expanduser("~/Downloads"))
        
        # Cache snapshots for change tracking
        self._desktop_files = self._get_file_list(self.desktop_path)
        self._downloads_files = self._get_file_list(self.downloads_path)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        _log.info("Continuous OS Awareness Observer Service started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        _log.info("Continuous OS Awareness Observer Service stopped")

    def get_metrics(self) -> Dict[str, Any]:
        return dict(self._latest_metrics)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._update_metrics()
                self._check_file_changes()
            except Exception as e:
                _log.error("Error in OS metrics observer loop: %s", str(e))
            self._stop_event.wait(self.scan_interval)

    def _update_metrics(self) -> None:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        battery = psutil.sensors_battery()
        
        # Check network online status
        online = False
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=1.5)
            online = True
        except OSError:
            pass

        self._latest_metrics = {
            "cpu_percent": cpu,
            "memory_percent": mem.percent,
            "battery_percent": battery.percent if battery else 100,
            "battery_charging": battery.power_plugged if battery else True,
            "network_online": online,
            "timestamp": time.time(),
        }

        # Store critical hardware thresholds to memory
        if battery and battery.percent < 15 and not battery.power_plugged:
            self.memory.add_action("proactive_alert", "Battery level critically low (< 15%)")
        if not online:
            # Only record drop if we were online previously (we check last cached)
            pass

    def _get_file_list(self, directory: Path) -> List[str]:
        if not directory.exists() or not directory.is_dir():
            return []
        try:
            return sorted(f.name for f in directory.iterdir() if f.is_file())
        except Exception:
            return []

    def _check_file_changes(self) -> None:
        # Check Desktop changes
        current_desktop = self._get_file_list(self.desktop_path)
        added_desktop = set(current_desktop) - set(self._desktop_files)
        if added_desktop:
            for item in added_desktop:
                self.memory.add_action("desktop_changed", f"Added file to Desktop: {item}")
            self._desktop_files = current_desktop

        # Check Downloads changes
        current_downloads = self._get_file_list(self.downloads_path)
        added_downloads = set(current_downloads) - set(self._downloads_files)
        if added_downloads:
            for item in added_downloads:
                self.memory.add_action("downloads_changed", f"Added file to Downloads: {item}")
            self._downloads_files = current_downloads
