from collections.abc import Sequence

import numpy as np
from qdrant_client.http import models as qmod

from util import log
from util.err import mkErr
from . import vecs

lg = log.get(__name__)


def _point(aid: int, vector: np.ndarray, uuid: str) -> qmod.PointStruct:
    arr = np.asarray(vector, dtype=np.float32)
    if arr.ndim != 1 or arr.size != 2048:
        raise ValueError(f"[vecs] Vector length is incorrect, expected 2048, actual {arr.size}")
    if not np.isfinite(arr).all():
        raise ValueError(f"[vecs] Vector contains invalid values aid[{aid}]")
    return qmod.PointStruct(
        id=int(aid),
        vector=arr.tolist(),
        payload={"aid": int(aid), "uuid": str(uuid)},
    )


def saveBatch(items: Sequence[tuple[int, np.ndarray, str]], batchSize: int = 128) -> int:
    try:
        if vecs.conn is None:
            raise RuntimeError("[vecs] Qdrant connection not initialized")
        if not items:
            return 0

        done = 0
        for i in range(0, len(items), max(1, batchSize)):
            chunk = items[i:i + max(1, batchSize)]
            points = [_point(aid, vector, uuid) for aid, vector, uuid in chunk]
            vecs.conn.upsert(
                collection_name=vecs.keyColl,
                points=points,
                wait=True,
            )
            done += len(points)
        return done
    except Exception as e:
        raise mkErr("[vecs] Error batch saving vectors", e)


def saveBatchWithFallback(items: Sequence[tuple[int, np.ndarray, str]], batchSize: int = 128) -> dict[int, str | None]:
    if not items:
        return {}

    try:
        saveBatch(items, batchSize=batchSize)
        return {int(aid): None for aid, _, _ in items}
    except Exception as batchError:
        lg.warning(f"[vecs] Batch upsert failed; retrying individually: {batchError}")
        result: dict[int, str | None] = {}
        for aid, vector, uuid in items:
            try:
                vecs.save(int(aid), vector, str(uuid), confirm=False)
                result[int(aid)] = None
            except Exception as e:
                result[int(aid)] = str(e)
        return result
