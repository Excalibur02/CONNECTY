import os
import sys
import time
import subprocess
import requests
import webbrowser
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from server.app.config import settings

def wait_for_backend(timeout=15):
    start = time.time()
    url = f"http://127.0.0.1:{settings.PORT}/api/v1/health"
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def main():
    python_exe = sys.executable
    print("=" * 64)
    print("   CONNECTY: Starting Laptop P2P Sharing + Streamlit UI")
    print("=" * 64)
    print(f" [FastAPI Service] : http://{settings.LAN_IP}:{settings.PORT}")
    print(f" [Streamlit Hub]   : http://localhost:8501")
    print("=" * 64)

    # 1. Start FastAPI backend as subprocess
    server_process = subprocess.Popen([
        python_exe,
        str(root_dir / "server" / "run.py")
    ])

    try:
        print("\nWaiting for FastAPI backend to initialize...")
        if not wait_for_backend():
            print("[WARNING] Backend took longer than expected to start, launching Streamlit...")

        # 2. Launch Streamlit UI
        streamlit_app = str(root_dir / "server" / "streamlit_app.py")
        cmd = [
            python_exe,
            "-m", "streamlit", "run",
            streamlit_app,
            "--server.port=8501",
            "--server.headless=false",
            "--browser.gatherUsageStats=false"
        ]

        print("\nLaunching Streamlit Dashboard at http://localhost:8501...")
        streamlit_process = subprocess.Popen(cmd)

        # Wait on Streamlit process
        streamlit_process.wait()

    except KeyboardInterrupt:
        print("\nShutting down CONNECTY...")
    finally:
        if server_process.poll() is None:
            server_process.terminate()
            try:
                server_process.wait(timeout=3)
            except Exception:
                server_process.kill()

if __name__ == "__main__":
    main()
