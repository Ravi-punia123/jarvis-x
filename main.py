"""Entry point for the JARVIS desktop assistant."""

import time
import sys
import subprocess
from pathlib import Path
from logger import get_logger

def _check_and_heal_env(log) -> bool:
    """Detect if python environment is missing required dependencies and attempt repair."""
    req_file = Path(__file__).parent / "requirements.txt"
    if not req_file.exists():
        log.warning("requirements.txt not found. Skipping environment validation.")
        return True

    try:
        with open(req_file, "r", encoding="utf-8") as f:
            packages = [line.strip().split("==")[0] for line in f if line.strip() and not line.strip().startswith("#")]
    except Exception as e:
        log.error("Failed to read requirements.txt: %s", e)
        return True

    # Simple import check mapping
    import_mapping = {
        "SpeechRecognition": "speech_recognition",
        "Pillow": "PIL",
        "PyGetWindow": "pygetwindow",
        "pytesseract": "pytesseract",
    }

    missing_packages = []
    for pkg in packages:
        module_name = import_mapping.get(pkg, pkg.lower().replace("-", "_"))
        try:
            __import__(module_name)
        except ImportError:
            log.warning("Required package '%s' (module '%s') is missing.", pkg, module_name)
            missing_packages.append(pkg)

    if missing_packages:
        log.info("Attempting to auto-install missing packages individually: %s", missing_packages)
        all_success = True
        for pkg in missing_packages:
            try:
                log.info("Installing package '%s'...", pkg)
                # Try installing package using current python interpreter
                subprocess.run([sys.executable, "-m", "pip", "install", pkg], check=True, capture_output=True, text=True)
                log.info("Package '%s' installed successfully.", pkg)
            except subprocess.CalledProcessError as e:
                all_success = False
                log.error("Failed to install '%s'. Error output:\n%s", pkg, e.stderr or e.stdout or str(e))
                if pkg == "PyAudio":
                    log.warning(
                        "PyAudio installation failed. Voice Input will be disabled. "
                        "To resolve this, please install Microsoft C++ Build Tools from "
                        "https://visualstudio.microsoft.com/visual-cpp-build-tools/ and try again."
                    )
            except Exception as e:
                all_success = False
                log.error("Unexpected error during installation of '%s': %s", pkg, e)
        return all_success
    return True

if __name__ == "__main__":
    t0 = time.perf_counter()
    log = get_logger("main")
    log.info("Starting JARVIS application startup checks")
    
    # We check environment but allow non-critical packaging errors (like PyAudio failing wheel build under Python 3.14) to launch.
    _check_and_heal_env(log)
        
    try:
        from ui import JarvisApp
        app = JarvisApp()
        elapsed = time.perf_counter() - t0
        log.info("JARVIS initialized successfully in %.3f seconds", elapsed)
        app.run()
    except Exception as e:
        log.critical("Failed to launch JARVIS application: %s", e, exc_info=True)
        sys.exit(1)
