"""Plugin Loader Registry for dynamic marketplace loading."""

import os
import json
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Optional
from logger import get_logger

_log = get_logger("os_plugin_registry")


class DynamicPluginRegistry:
    """Manages runtime discovery, parsing manifest, and loading Python modules dynamically."""

    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = Path(plugins_dir)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self._loaded_plugins: Dict[str, Any] = {}
        self._manifests: Dict[str, Dict[str, Any]] = {}
        self.load_all_plugins()

    def load_all_plugins(self) -> None:
        if not self.plugins_dir.exists():
            return
        
        for item in self.plugins_dir.iterdir():
            if item.is_dir():
                manifest_path = item / "plugin.json"
                if manifest_path.exists():
                    self._load_plugin(item, manifest_path)

    def _load_plugin(self, plugin_dir: Path, manifest_path: Path) -> None:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            name = manifest.get("name")
            main_file = manifest.get("main", "main.py")
            if not name:
                return

            self._manifests[name] = manifest
            entry_point = plugin_dir / main_file
            if entry_point.exists():
                spec = importlib.util.spec_from_file_location(name, str(entry_point))
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    self._loaded_plugins[name] = module
                    _log.info("Loaded plugin dynamically: %s (v%s)", name, manifest.get("version", "1.0.0"))
        except Exception as e:
            _log.error("Failed to load plugin from %s: %s", plugin_dir, str(e))

    def get_loaded_plugins(self) -> List[str]:
        return list(self._loaded_plugins.keys())

    def get_manifest(self, name: str) -> Optional[Dict[str, Any]]:
        return self._manifests.get(name)

    def execute_plugin_action(self, plugin_name: str, action: str, *args: Any, **kwargs: Any) -> Any:
        module = self._loaded_plugins.get(plugin_name)
        if not module:
            return {"success": False, "error": f"Plugin {plugin_name} not loaded"}
        
        func = getattr(module, action, None)
        if not func:
            return {"success": False, "error": f"Action {action} not found in plugin {plugin_name}"}

        try:
            return func(*args, **kwargs)
        except Exception as e:
            return {"success": False, "error": str(e)}
