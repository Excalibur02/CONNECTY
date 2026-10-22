import os
import socket
import uuid
from pathlib import Path
from pydantic import BaseModel

def get_local_lan_ip() -> str:
    """Get the primary local LAN IP address of this device."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Using a public DNS IP to determine the default routing interface without sending packets
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"

class Settings(BaseModel):
    HOST: str = "0.0.0.0"
    PORT: int = int(os.environ.get("CONNECTY_PORT", "8000"))
    LAN_IP: str = get_local_lan_ip()
    DEVICE_NAME: str = os.environ.get("CONNECTY_DEVICE_NAME", f"Laptop-{socket.gethostname()}")
    DEVICE_ID: str = os.environ.get("CONNECTY_DEVICE_ID", str(uuid.uuid4()))
    DEVICE_TYPE: str = "laptop"
    PROTOCOL_VERSION: str = "1.0.0"
    
    # Base data directory for DB, temporary transfer chunks, and shared folders
    BASE_DIR: Path = Path(os.environ.get("CONNECTY_BASE_DIR", str(Path(__file__).resolve().parent.parent.parent / ".connecty_data")))
    
    @property
    def DB_PATH(self) -> Path:
        return self.BASE_DIR / "connecty.db"

    @property
    def STAGING_DIR(self) -> Path:
        return self.BASE_DIR / "transfers_staging"

    @property
    def DEFAULT_SHARED_DIR(self) -> Path:
        return self.BASE_DIR / "shared"

    SECRET_KEY: str = os.environ.get("CONNECTY_SECRET_KEY", "connecty-p2p-secret-key-change-in-prod")
    PAIRING_PIN_EXPIRE_SECONDS: int = 600  # 10 minutes

settings = Settings()

# Ensure directories exist
settings.BASE_DIR.mkdir(parents=True, exist_ok=True)
settings.STAGING_DIR.mkdir(parents=True, exist_ok=True)
settings.DEFAULT_SHARED_DIR.mkdir(parents=True, exist_ok=True)
