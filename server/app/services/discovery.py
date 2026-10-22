import socket
import logging
import time
from typing import Dict, Any, List
from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser, ServiceListener
from server.app.config import settings

logger = logging.getLogger("connecty.discovery")

MDNS_TYPE = "_homesync._tcp.local."
MDNS_TYPE_FALLBACK = "_connecty._tcp.local."

class PeerListener(ServiceListener):
    def __init__(self):
        self.peers: Dict[str, Dict[str, Any]] = {}

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        logger.info(f"Service removed: {name}")
        self.peers.pop(name, None)

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info:
            self._update_peer(name, info)

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info:
            self._update_peer(name, info)

    def _update_peer(self, name: str, info: ServiceInfo):
        try:
            addresses = [socket.inet_ntoa(addr) for addr in info.addresses if len(addr) == 4]
            properties = {k.decode("utf-8"): v.decode("utf-8") if isinstance(v, bytes) else str(v)
                          for k, v in (info.properties or {}).items()}
            
            # Don't register ourselves as an external peer
            if properties.get("device_id") == settings.DEVICE_ID:
                return

            self.peers[name] = {
                "name": name,
                "device_name": properties.get("device_name", name),
                "device_id": properties.get("device_id", "unknown"),
                "device_type": properties.get("device_type", "unknown"),
                "addresses": addresses,
                "port": info.port,
                "capabilities": properties.get("capabilities", "").split(","),
                "version": properties.get("version", "1.0.0"),
                "last_seen": time.time()
            }
        except Exception as e:
            logger.warning(f"Failed to parse peer info: {e}")

class DiscoveryService:
    def __init__(self):
        self.zeroconf: Zeroconf = None
        self.service_info: ServiceInfo = None
        self.listener: PeerListener = None
        self.browser: ServiceBrowser = None
        self._is_running = False

    def start(self):
        if self._is_running:
            return
        try:
            self.zeroconf = Zeroconf()
            self.listener = PeerListener()
            self.browser = ServiceBrowser(self.zeroconf, MDNS_TYPE, self.listener)
            
            # Prepare our own service announcement
            ip_str = settings.LAN_IP
            ip_bytes = socket.inet_aton(ip_str)
            
            clean_name = settings.DEVICE_NAME.replace(" ", "-")
            service_name = f"{clean_name}.{MDNS_TYPE}"
            
            properties = {
                "device_name": settings.DEVICE_NAME,
                "device_id": settings.DEVICE_ID,
                "device_type": settings.DEVICE_TYPE,
                "version": settings.PROTOCOL_VERSION,
                "capabilities": "browse,stream,receive",
                "lan_ip": settings.LAN_IP,
                "port": str(settings.PORT)
            }
            
            self.service_info = ServiceInfo(
                type_=MDNS_TYPE,
                name=service_name,
                addresses=[ip_bytes],
                port=settings.PORT,
                properties=properties,
                server=f"{socket.gethostname()}.local."
            )
            
            self.zeroconf.register_service(self.service_info)
            self._is_running = True
            logger.info(f"mDNS Discovery started: advertising {service_name} at {ip_str}:{settings.PORT}")
        except Exception as e:
            logger.error(f"Failed to start mDNS Discovery service: {e}")

    def stop(self):
        if not self._is_running:
            return
        try:
            if self.zeroconf and self.service_info:
                self.zeroconf.unregister_service(self.service_info)
            if self.zeroconf:
                self.zeroconf.close()
            self._is_running = False
            logger.info("mDNS Discovery stopped.")
        except Exception as e:
            logger.error(f"Error stopping mDNS: {e}")

    def get_discovered_peers(self) -> List[Dict[str, Any]]:
        if not self.listener:
            return []
        # Return peers seen within last 2 minutes
        now = time.time()
        active = [p for p in self.listener.peers.values() if now - p["last_seen"] < 120]
        return active

discovery_service = DiscoveryService()
