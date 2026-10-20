import asyncio
import subprocess
try:
    from wakeonlan import wake
    def _do_wake(mac, broadcast):
        wake(mac, host=broadcast)
except Exception:
    from wakeonlan import send_magic_packet
    def _do_wake(mac, broadcast):
        send_magic_packet(mac, ip_address=broadcast)
from src.config import settings

class WOLService:
    @staticmethod
    def wake_pc() -> dict:
        """Envía el paquete mágico Wake-on-LAN a la PC configurada."""
        try:
            _do_wake(
                settings.WOL_MAC_ADDRESS,
                settings.WOL_BROADCAST_IP
            )
            return {
                "success": True,
                "mac": settings.WOL_MAC_ADDRESS,
                "broadcast": settings.WOL_BROADCAST_IP,
                "target_ip": settings.WOL_TARGET_IP
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    async def is_pc_online(timeout: int = 1) -> bool:
        """Comprueba si la PC responde a ping."""
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "1", "-W", str(timeout), settings.WOL_TARGET_IP,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return (await proc.wait()) == 0
