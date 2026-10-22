import sys
import os
import uvicorn
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from server.app.config import settings
from server.app.database import init_db, get_active_pin

def print_banner():
    init_db()
    pin = get_active_pin()
    lan_url = f"http://{settings.LAN_IP}:{settings.PORT}"
    
    print("\n" + "=" * 64)
    print("      CONNECTY: Peer-to-Peer Home File Sharing Server")
    print("=" * 64)
    print(f" [Device]       : {settings.DEVICE_NAME} ({settings.DEVICE_TYPE})")
    print(f" [LAN URL]      : {lan_url}")
    print(f" [Local URL]    : http://localhost:{settings.PORT}")
    print(f" [Pairing PIN]  : {pin}")
    print(f" [mDNS Service] : _homesync._tcp.local. (Active)")
    print(f" [Shared Dir]   : {settings.DEFAULT_SHARED_DIR.resolve()}")
    print("-" * 64)
    print(" TO CONNECT YOUR ANDROID PHONE:")
    print(f" 1. Make sure your phone is on the same Wi-Fi network.")
    print(f" 2. Open Chrome/browser on your phone and go to:")
    print(f"    {lan_url}")
    print(f" 3. Enter PIN [{pin}] (or scan the QR code on the laptop screen).")
    print("=" * 64 + "\n")

if __name__ == "__main__":
    print_banner()
    uvicorn.run(
        "server.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level="info"
    )
