"""System Health Manager tracking hardware metrics, memory, and services status."""

import os
import psutil
import socket
import urllib.request
from typing import Dict, Any, List
from logger import get_logger

_log = get_logger("os_health")


class OSHealthManager:
    """Continuously evaluates hardware health, local AI dependencies, and system parameters."""

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url

    def check_health(self) -> Dict[str, Any]:
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        
        # Ollama check
        ollama_status = "offline"
        models: List[str] = []
        try:
            with urllib.request.urlopen(self.ollama_url, timeout=1.5) as conn:
                if conn.status == 200:
                    ollama_status = "online"
            
            # Fetch loaded models
            import json
            req = urllib.request.Request(f"{self.ollama_url}/api/tags")
            with urllib.request.urlopen(req, timeout=1.5) as conn:
                data = json.loads(conn.read().decode("utf-8"))
                models = [m.get("name") for m in data.get("models", [])]
        except Exception:
            pass

        # GPU metrics approximation (falls back safely if nvidia-smi is not configured)
        vram_percent = 0.0
        try:
            import subprocess
            out = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,utilization.memory", "--format=csv,noheader,nounits"], 
                                 capture_output=True, text=True, timeout=1.5)
            if out.returncode == 0:
                parts = out.stdout.strip().split(",")
                if len(parts) >= 2:
                    vram_percent = float(parts[1].strip())
        except Exception:
            pass

        return {
            "cpu_percent": cpu,
            "memory_percent": mem.percent,
            "vram_percent": vram_percent,
            "ollama_status": ollama_status,
            "available_models": models,
            "status": "healthy" if ollama_status == "online" and mem.percent < 90 else "degraded",
        }
