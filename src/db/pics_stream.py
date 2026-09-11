from collections.abc import Iterator

from mod import models
from . import pics


def getVectoredUuidMap(aids: set[int] | list[int], batchSize: int = 500) -> dict[int, str]:
    ids = list(aids)
    if not ids:
        return {}

    result: dict[int, str] = {}
    with pics.mkConn() as conn:
        cur = conn.cursor()
        for i in range(0, len(ids), batchSize):
            chunk = ids[i:i + batchSize]
            placeholders = ",".join("?" for _ in chunk)
            cur.execute(
                f"SELECT autoId, id FROM assets WHERE isVectored=1 AND autoId IN ({placeholders})",
                chunk,
            )
            for row in cur.fetchall():
                result[int(row[0])] = str(row[1])
    return result


def getNonVectorChunk(afterAutoId: int = 0, limit: int = 512) -> list[models.Asset]:
    with pics.mkConn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT * FROM assets
            WHERE isVectored=0 AND autoId > ?
            ORDER BY autoId
            LIMIT ?
            """,
            (afterAutoId, limit),
        )
        rows = cur.fetchall()
        return [models.Asset.fromDB(cur, row) for row in rows]


def iterNonVectorChunks(limit: int = 512) -> Iterator[list[models.Asset]]:
    after = 0
    while True:
        chunk = getNonVectorChunk(after, limit)
        if not chunk:
            return
        yield chunk
        after = int(chunk[-1].autoId)
