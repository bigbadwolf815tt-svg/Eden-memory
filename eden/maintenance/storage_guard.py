"""Resource-aware storage capacity checks."""
from dataclasses import dataclass
from pathlib import Path
import shutil

DEFAULT_RESERVE_BYTES = 512 * 1024 * 1024

@dataclass(frozen=True)
class StorageStatus:
    path: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    reserve_bytes: int
    available_bytes: int
    within_reserve: bool

def get_storage_status(path, reserve_bytes=DEFAULT_RESERVE_BYTES):
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(target)
    if isinstance(reserve_bytes, bool) or not isinstance(reserve_bytes, int) or reserve_bytes < 0:
        raise ValueError("reserve_bytes must be a non-negative integer")
    usage = shutil.disk_usage(target)
    available = max(0, usage.free - reserve_bytes)
    return StorageStatus(
        str(target), usage.total, usage.used, usage.free,
        reserve_bytes, available, usage.free < reserve_bytes
    )

def require_storage_capacity(path, required_bytes, reserve_bytes=DEFAULT_RESERVE_BYTES):
    if isinstance(required_bytes, bool) or not isinstance(required_bytes, int) or required_bytes < 0:
        raise ValueError("required_bytes must be a non-negative integer")
    status = get_storage_status(path, reserve_bytes)
    if required_bytes > status.available_bytes:
        raise OSError(
            f"Insufficient storage: need {required_bytes} bytes; "
            f"only {status.available_bytes} bytes available after reserve"
        )
    return status
