import os

import db
from conf import ks
from mod import mapFns, models
from mod.models import IFnProg
from util import log
from perf import logMemory

lg = log.get(__name__)


def _chunkSize() -> int:
    try:
        return max(32, min(5000, int(os.getenv('DEDUP_VECTOR_CHUNK_SIZE', '512'))))
    except Exception:
        return 512


def vec_ToVec(doReport: IFnProg, sto: models.ITaskStore):
    from db import pics_stream
    import imgs

    nfy, _, cnt = sto.nfy, sto.now, sto.cnt
    msg = "[vec] Processing successful"
    logMemory('vector task start')

    try:
        photoQ = db.dto.photoQ
        doReport(1, f"[ToVec] start with photoQ[{photoQ}]")

        if sto.isCancelled():
            msg = "Task was cancelled before processing"
            nfy.info(msg)
            return sto, msg

        doReport(2, "reconcile: scan no-uuid")
        nuids = db.vecs.getNoUuidAids()
        if nuids:
            aidVec1 = pics_stream.getVectoredUuidMap(nuids)
            toFill = [(aid, aidVec1[aid]) for aid in nuids if aid in aidVec1]
            toDel = [aid for aid in nuids if aid not in aidVec1]

            if toFill:
                doReport(3, f"reconcile step1: backfill uuid ({len(toFill)})")
                db.vecs.setUuidPayloads(toFill)

            if toDel:
                doReport(4, f"reconcile: del orphan/non-ved ({len(toDel)})")
                bsz = 500
                for i in range(0, len(toDel), bsz):
                    if sto.isCancelled():
                        break
                    chunk = toDel[i:i + bsz]
                    db.vecs.deleteBy(chunk)
                    lg.info(f"[vec] delete batch[{i // bsz + 1}] cnt[{len(chunk)}]")

        total = db.pics.count(vectored=0)
        doReport(7, f"reconcile: process vecs ({total})")
        if total <= 0:
            msg = "No assets to process"
            nfy.error(msg)
            return sto, msg

        if sto.isCancelled():
            msg = "Task was cancelled during initialization"
            nfy.info(msg)
            return sto, msg

        doReport(8, f"Found [ {total} ] start processing..")
        aggregate = models.ProcessInfo(all=total, done=0, skip=0, erro=0)
        processed = 0
        newAids: set[int] = set()

        for assetChunk in pics_stream.iterNonVectorChunks(_chunkSize()):
            if sto.isCancelled():
                break

            newAids.update(int(asset.autoId) for asset in assetChunk)
            before = processed

            def reportChunk(localPct: int, localMsg: str):
                if not doReport:
                    return
                localDone = len(assetChunk) * max(0, min(100, localPct)) / 100.0
                overall = (before + localDone) / max(1, total)
                pct = 8 + int(overall * 85)
                doReport(min(93, pct), localMsg)

            rst = imgs.processVectors(
                assetChunk,
                photoQ,
                onUpdate=reportChunk,
                isCancelled=sto.isCancelled,
            )
            aggregate.done += rst.done
            aggregate.skip += rst.skip
            aggregate.erro += rst.erro
            processed += len(assetChunk)
            logMemory(f"vector task progress {processed}/{total}")

        if sto.isCancelled():
            msg = f"Processing cancelled: completed[ {aggregate.done} ] error[ {aggregate.erro} ]"
            nfy.info(msg)
            return sto, msg

        doReport(95, "wait Qdrant index build")
        if db.vecs.waitForGreen(timeout=600, isCancel=sto.isCancelled, doReport=doReport):
            doReport(96, "scan idx desync (exclude this-round)")
            scanned, repaired, broken = db.vecs.scanRepairIdx(
                doReport,
                sto.isCancelled,
                excludeAids=newAids,
            )
            lg.info(f"[vec] post-repair scanned={scanned} repaired={repaired} broken={len(broken)}")
            if broken:
                db.pics.setVectoredByAids(broken, done=0)
                nfy.warn(
                    f"Post-repair: {len(broken)} broken cleared, run again to regenerate. "
                    f"IDs: {broken[:20]}{'...' if len(broken) > 20 else ''}"
                )
            elif repaired:
                nfy.info(f"Post-repair: fixed {repaired}/{scanned} point(s)")
        else:
            nfy.warn("Qdrant index still building, skipped post-repair")

        cnt.vec = db.pics.count(vectored=1)
        msg = f"Completed: total[ {aggregate.all} ] done[ {aggregate.done} ] Skip[ {aggregate.skip} ]"
        if aggregate.erro:
            msg += f" Error[ {aggregate.erro}]"
        nfy.success(msg)
        return sto, msg
    except Exception as e:
        if sto.isCancelled():
            msg = "Task was cancelled"
            nfy.info(msg)
            return sto, msg
        msg = f"Asset processing failed: {str(e)}"
        nfy.error(msg)
        raise RuntimeError(msg)
    finally:
        logMemory('vector task end')


def register() -> None:
    mapFns[ks.cmd.vec.toVec] = vec_ToVec
    lg.info("[vec] optimized streaming vector task registered")
