# JARVIS v3.0 Plugin SDK

Build and load third-party extensions dynamically for JARVIS without editing core code.

## 1. Plugin Directory Structure
Place your files in a subdirectory inside `plugins/` (e.g., `plugins/my_custom_plugin/`):
```
plugins/
  my_custom_plugin/
    plugin.json
    main.py
```

## 2. Manifest Schema (`plugin.json`)
```json
{
  "name": "my_custom_plugin",
  "version": "1.0.0",
  "main": "main.py",
  "permissions": ["filesystem", "network"],
  "capabilities": ["custom_automation"]
}
```

## 3. Entrypoint Specification (`main.py`)
```python
def my_plugin_action(param1, param2):
    # Perform custom automation task
    return {"success": True, "result": "Action executed successfully!"}
```
