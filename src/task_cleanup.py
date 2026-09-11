import os
import threading
import time
from typing import Optional

from mod.models import TskStatus
from util import log

lg = log.get(__name__)

_started_for: set[int] = set()
_lock = threading.Lock()


def _envInt(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except Exception:
        return default


def start(mgr) -> Optional[threading.Thread]:
    if mgr is None:
        return None

    key = id(mgr)
    with _lock:
        if key in _started_for:
            return None
        _started_for.add(key)

    retention = _envInt("DEDUP_TASK_RETENTION_SECONDS", 60, 10)
    interval = min(30, max(5, retention // 2))
    maxCompleted = _envInt("DEDUP_TASK_HISTORY", 20, 1)

    def cleanup() -> None:
        terminal = {TskStatus.COMPLETED, TskStatus.FAILED, TskStatus.CANCELLED}
        while True:
            time.sleep(interval)
            try:
                now = time.time()
                completed = [
                    (tsn, ti)
                    for tsn, ti in list(mgr.infos.items())
                    if ti.status in terminal and ti.dte is not None
                ]
                completed.sort(key=lambda item: item[1].dte or 0, reverse=True)
                keep = {tsn for tsn, _ in completed[:maxCompleted]}

                removed = 0
                for tsn, ti in completed:
                    age = now - (ti.dte or now)
                    if age < retention and tsn in keep:
                        continue
                    mgr.tsks.pop(tsn, None)
                    mgr.threads.pop(tsn, None)
                    mgr.infos.pop(tsn, None)
                    removed += 1

                if removed:
                    lg.info(f"[tskMgr] cleaned {removed} completed task(s)")
            except Exception as e:
                lg.warning(f"[tskMgr] task cleanup failed: {e}")

    thread = threading.Thread(target=cleanup, name="task-history-cleanup", daemon=True)
    thread.start()
    lg.info(f"[tskMgr] completed-task retention: {retention}s, history={maxCompleted}")
    return thread
