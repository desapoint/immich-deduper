import gc
import os
import sys

from util import log

lg = log.get(__name__)


def rssBytes() -> int:
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss
    except Exception:
        return 0


def rssMb() -> float:
    return rssBytes() / (1024 * 1024)


def logMemory(label: str, level: str = "info") -> float:
    mb = rssMb()
    if mb <= 0:
        return mb
    msg = f"[memory] {label}: rss={mb:.1f} MB"
    fn = getattr(lg, level, lg.info)
    fn(msg)
    return mb


def trimMemory(*, collect: bool = True, clear_device_cache: bool = True) -> None:
    if collect:
        gc.collect()

    if clear_device_cache:
        torch = sys.modules.get("torch")
        if torch is not None:
            try:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
            try:
                mps = getattr(torch, "mps", None)
                if mps is not None and hasattr(mps, "empty_cache"):
                    mps.empty_cache()
            except Exception:
                pass

    if sys.platform.startswith("linux"):
        try:
            import ctypes
            libc = ctypes.CDLL("libc.so.6")
            trim = getattr(libc, "malloc_trim", None)
            if trim is not None:
                trim(0)
        except Exception:
            pass
