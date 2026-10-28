import shutil
import psutil
import docker

class SystemService:
    @staticmethod
    def get_metrics() -> dict:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count()

        # RAM
        mem = psutil.virtual_memory()
        ram_total_gb = round(mem.total / (1024 ** 3), 2)
        ram_used_gb = round(mem.used / (1024 ** 3), 2)
        ram_free_gb = round(mem.available / (1024 ** 3), 2)
        ram_percent = mem.percent

        # Discos sin duplicados
        targets = [
            {"name": "Almacenamiento Principal", "path": "/"},
            {"name": "Almacenamiento Secundario", "path": "/mnt/media"}
        ]
        disks = []
        for t in targets:
            try:
                usage = shutil.disk_usage(t["path"])
                total_gb = round(usage.total / (1024 ** 3), 1)
                free_gb = round(usage.free / (1024 ** 3), 1)
                used_gb = round(usage.used / (1024 ** 3), 1)
                percent = round((usage.used / usage.total) * 100, 1)
                disks.append({
                    "name": t["name"],
                    "path": t["path"],
                    "total_gb": total_gb,
                    "used_gb": used_gb,
                    "free_gb": free_gb,
                    "percent": percent
                })
            except Exception:
                continue

        # Docker Containers
        containers_info = []
        try:
            client = docker.from_env()
            for c in client.containers.list(all=True):
                containers_info.append({
                    "name": c.name,
                    "status": c.status,
                    "image": c.image.tags[0] if c.image.tags else "unknown"
                })
        except Exception as e:
            containers_info = [{"name": "Docker error", "status": str(e), "image": ""}]

        return {
            "cpu_percent": cpu_percent,
            "cpu_count": cpu_count,
            "ram": {
                "total_gb": ram_total_gb,
                "used_gb": ram_used_gb,
                "free_gb": ram_free_gb,
                "percent": ram_percent
            },
            "disks": disks,
            "containers": containers_info
        }
