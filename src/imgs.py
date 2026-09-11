from __future__ import annotations

import base64
import gc
import multiprocessing
import os
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from io import BytesIO
from typing import Any, List, Optional, Tuple

import numpy as np

import db
import conf
import rtm
from conf import envs
from mod import models
from util import log
from util.err import mkErr
from perf import logMemory, trimMemory

lg = log.get(__name__)
os.environ['KMP_DUPLICATE_LIB_OK'] = "TRUE"

_model = None
_model_lock = threading.RLock()
_model_active = 0
_model_last_used = 0.0
_model_monitor_started = False
_transform = None
_torch_module = None
_cpu_threads_configured = False


def _envInt(name: str, default: int, minimum: int = 0, maximum: Optional[int] = None) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except Exception:
        value = default
    value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _torch():
    global _torch_module
    if _torch_module is None:
        import torch
        _torch_module = torch
    return _torch_module


def _getTransform():
    global _transform
    if _transform is None:
        from torchvision.transforms import Compose, Resize, ToTensor, Normalize

        def to_rgb(image):
            return image if image.mode == 'RGB' else image.convert('RGB')

        _transform = Compose([
            to_rgb,
            Resize((224, 224)),
            ToTensor(),
            Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
    return _transform


def FeatureExtractor(base_model):
    torch = _torch()

    class _FeatureExtractor(torch.nn.Module):
        def __init__(self, model):
            super().__init__()
            self.features = torch.nn.Sequential(*list(model.children())[:-2])
            self.avgpool = torch.nn.AdaptiveAvgPool2d((1, 1))

        def forward(self, x):
            x = self.features(x)
            x = self.avgpool(x)
            return x.view(x.size(0), -1)

    return _FeatureExtractor(base_model)


def _configureCpuThreads() -> None:
    global _cpu_threads_configured
    if _cpu_threads_configured:
        return
    if conf.device.type != 'cpu':
        _cpu_threads_configured = True
        return

    torch = _torch()
    cpuCnt = max(1, multiprocessing.cpu_count() or 1)
    decodeWorkers = _getDecodeWorkers('cpu')
    intra = max(1, cpuCnt - decodeWorkers)
    intra = min(intra, _envInt('DEDUP_TORCH_THREADS', intra, 1, cpuCnt))
    try:
        torch.set_num_threads(intra)
    except Exception as e:
        lg.warning(f"[imgs] unable to set torch CPU threads: {e}")
    try:
        torch.set_num_interop_threads(1)
    except Exception:
        pass
    _cpu_threads_configured = True
    lg.info(f"[imgs] torch CPU threads[{intra}] decodeWorkers[{decodeWorkers}]")


def _loadModel():
    torch = _torch()
    from torchvision.models import resnet152, ResNet152_Weights

    device = conf.getDevice()
    model_dir = os.path.join(envs.ddupData, 'models')
    os.makedirs(model_dir, exist_ok=True)
    torch.hub.set_dir(model_dir)

    logMemory('before model load')
    base_model = resnet152(weights=ResNet152_Weights.DEFAULT)
    model = FeatureExtractor(base_model).to(device)
    model.eval()
    _configureCpuThreads()
    logMemory('after model load')
    return model


def _idleTimeout() -> int:
    return _envInt('DEDUP_MODEL_IDLE_TIMEOUT', 600, 0)


def _startModelMonitor() -> None:
    global _model_monitor_started
    with _model_lock:
        if _model_monitor_started or _idleTimeout() <= 0:
            return
        _model_monitor_started = True

    def monitor() -> None:
        while True:
            timeout = _idleTimeout()
            if timeout <= 0:
                time.sleep(60)
                continue
            time.sleep(min(60, max(5, timeout // 2)))
            with _model_lock:
                loaded = _model is not None
                active = _model_active
                idleFor = time.monotonic() - _model_last_used if _model_last_used else 0
            if loaded and active == 0 and idleFor >= timeout:
                unloadModel(reason=f"idle {int(idleFor)}s")

    threading.Thread(target=monitor, name='deduper-model-idle', daemon=True).start()


def getModel():
    global _model, _model_last_used
    with _model_lock:
        if _model is None:
            _model = _loadModel()
            _startModelMonitor()
        _model_last_used = time.monotonic()
        return _model


@contextmanager
def modelSession():
    global _model_active, _model_last_used
    with _model_lock:
        model = getModel()
        _model_active += 1
        _model_last_used = time.monotonic()
    try:
        yield model
    finally:
        with _model_lock:
            _model_active = max(0, _model_active - 1)
            _model_last_used = time.monotonic()


def modelIsLoaded() -> bool:
    with _model_lock:
        return _model is not None


def unloadModel(*, force: bool = False, reason: str = 'manual') -> bool:
    global _model, _model_last_used
    with _model_lock:
        if _model is None:
            return False
        if _model_active and not force:
            return False
        lg.info(f"[imgs] unloading model ({reason})")
        logMemory('before model unload')
        _model = None
        _model_last_used = 0.0

    trimMemory(collect=True, clear_device_cache=True)
    logMemory('after model unload')
    return True


def getOptimalBatchSize() -> int:
    device_type = conf.device.type
    if device_type == 'cpu':
        return _envInt('DEDUP_CPU_BATCH_SIZE', 4, 1, 32)

    if not db.dto.gpuAutoMode and db.dto.gpuBatchSize:
        return max(1, int(db.dto.gpuBatchSize))

    torch = _torch()
    if device_type == 'cuda':
        try:
            gpu_memory = torch.cuda.get_device_properties(0).total_memory
            if gpu_memory > 12 * 1024 ** 3: return 16
            if gpu_memory > 8 * 1024 ** 3: return 12
            if gpu_memory > 6 * 1024 ** 3: return 8
            if gpu_memory > 4 * 1024 ** 3: return 6
            if gpu_memory > 2 * 1024 ** 3: return 4
            return 2
        except Exception:
            return 8

    if device_type == 'mps':
        try:
            import psutil
            total_memory = psutil.virtual_memory().total
            if total_memory > 32 * 1024 ** 3: return 32
            if total_memory > 16 * 1024 ** 3: return 16
            if total_memory > 8 * 1024 ** 3: return 8
            return 4
        except Exception:
            return 8
    return 4


def _getDecodeWorkers(device_type: str) -> int:
    cpuCnt = max(1, multiprocessing.cpu_count() or 1)
    if device_type in ('cuda', 'mps'):
        return min(4, cpuCnt)
    if not db.dto.cpuAutoMode:
        return max(1, min(int(db.dto.cpuWorkers or 1), cpuCnt, 16))
    return max(1, min(cpuCnt // 2, 4))


def _normalizeFeatureShape(features, batch_size: int):
    torch = _torch()
    if len(features.shape) == 1:
        features = features.view(batch_size, -1)
    feature_dim = features.shape[1]
    if feature_dim > 2048:
        features = features[:, :2048]
    elif feature_dim < 2048:
        padded = torch.zeros(batch_size, 2048, device=features.device, dtype=features.dtype)
        padded[:, :feature_dim] = features
        features = padded
    return torch.nn.functional.normalize(features, p=2, dim=1)


def _extractTensorBatch(tensors: List[Any]) -> List[np.ndarray]:
    if not tensors:
        return []
    torch = _torch()
    device = conf.getDevice()
    batch_tensor = torch.stack(tensors).to(device, non_blocking=False)

    with modelSession() as model:
        with torch.inference_mode():
            features = model(batch_tensor)
            features = _normalizeFeatureShape(features, batch_tensor.shape[0])
            batch_numpy = features.detach().cpu().numpy().astype(np.float32, copy=False)

    result = []
    for vec in batch_numpy:
        if vec.size != 2048 or not np.isfinite(vec).all():
            raise ValueError("Extracted vector is empty or contains invalid values")
        result.append(vec.copy())
    return result


def extractFeatures(image) -> np.ndarray:
    tensor = _getTransform()(image)
    return _extractTensorBatch([tensor])[0]


def extractFeaturesBatch(images: List[Any]) -> List[np.ndarray]:
    if not images:
        return []
    tensors = [_getTransform()(image) for image in images]
    try:
        return _extractTensorBatch(tensors)
    finally:
        tensors.clear()


def toB64(path):
    from PIL import Image
    if isinstance(path, str):
        with open(path, 'rb') as f:
            image = f.read()
        return 'data:image/png;base64,' + base64.b64encode(image).decode('utf-8')
    if isinstance(path, bytes):
        return 'data:image/png;base64,' + base64.b64encode(path).decode('utf-8')
    if isinstance(path, Image.Image):
        buffer = BytesIO()
        path.save(buffer, format='PNG')
        return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode('utf-8')
    return None


def getImg(path):
    from PIL import Image, ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    path = rtm.pth.full(path)
    try:
        if not os.path.exists(path):
            lg.error(f"File not found: {path}")
            return None
        with Image.open(path) as src:
            src.load()
            return src.copy()
    except Exception as e:
        lg.error(f"Error opening image from local path: {str(e)}")
        return None


def getImgB64(path) -> Optional[str]:
    img = getImg(path)
    if img:
        try:
            return toB64(img)
        finally:
            try: img.close()
            except Exception: pass
    return toB64(path) if os.path.exists(path) else None


def _loadTensor(asset: models.Asset, photoQ):
    from PIL import Image, ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    path = rtm.pth.full(asset.getImagePath(photoQ))
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with Image.open(path) as image:
        return _getTransform()(image)


def loadTensorsParallel(assets: List[models.Asset], photoQ, maxWorkers: Optional[int] = None):
    if not assets:
        return [], []
    workers = maxWorkers or _getDecodeWorkers(conf.device.type)
    ok: list[tuple[models.Asset, Any]] = []
    failed: list[tuple[models.Asset, Optional[str]]] = []

    def load(asset):
        try:
            return asset, _loadTensor(asset, photoQ), None
        except Exception as e:
            return asset, None, f"image load failed: {asset.id} - {e}"

    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(assets)))) as executor:
        futures = [executor.submit(load, asset) for asset in assets]
        for future in as_completed(futures):
            asset, tensor, error = future.result()
            if tensor is not None:
                ok.append((asset, tensor))
            else:
                failed.append((asset, error))
    return ok, failed


def loadImagesParallel(assets: List[models.Asset], photoQ, maxWorkers=10):
    # Compatibility helper used by older tests/callers. Vector processing uses the
    # tensor loader above so full-resolution PIL images are not retained.
    imgs = []
    rstOKs = []
    rstNos = []

    def load(asset):
        try:
            img = getImg(asset.getImagePath(photoQ))
            return asset, img, None if img is not None else 'image load failed'
        except Exception as e:
            return asset, None, str(e)

    with ThreadPoolExecutor(max_workers=max(1, min(maxWorkers, len(assets) or 1))) as executor:
        futures = [executor.submit(load, asset) for asset in assets]
        for future in as_completed(futures):
            asset, img, error = future.result()
            if img is not None:
                imgs.append(img)
                rstOKs.append(asset)
            else:
                rstNos.append((asset, error))
    return imgs, rstOKs, rstNos


def _saveVectors(assets: List[models.Asset], vecs: List[np.ndarray]):
    from db import vec_batch
    batchSize = _envInt('DEDUP_QDRANT_BATCH_SIZE', 128, 1, 1000)
    items = [(int(asset.autoId), vec, asset.id) for asset, vec in zip(assets, vecs)]
    status = vec_batch.saveBatchWithFallback(items, batchSize=batchSize)
    result = []
    for asset in assets:
        error = status.get(int(asset.autoId))
        result.append((asset, error))
    return result


def _processBatch(assets: List[models.Asset], photoQ):
    loaded, failed = loadTensorsParallel(assets, photoQ)
    result = list(failed)
    if not loaded:
        return result

    okAssets = [asset for asset, _ in loaded]
    tensors = [tensor for _, tensor in loaded]
    try:
        vecs = _extractTensorBatch(tensors)
        result.extend(_saveVectors(okAssets, vecs))
    except Exception as e:
        lg.warning(f"[imgs] batch inference failed; retrying individually: {e}")
        for asset, tensor in loaded:
            try:
                vec = _extractTensorBatch([tensor])[0]
                result.extend(_saveVectors([asset], [vec]))
            except Exception as singleError:
                result.append((asset, f"feature extraction failed: {asset.id} - {singleError}"))
    finally:
        tensors.clear()
        loaded.clear()
    return result


def saveVectorBy(asset: models.Asset, photoQ) -> Tuple[models.Asset, Optional[str]]:
    result = _processBatch([asset], photoQ)
    return result[0] if result else (asset, 'unknown vector processing error')


def saveVectorBatch(assets: List[models.Asset], photoQ, preloaded=None):
    if preloaded:
        imgs, rstOKs, rstNos = preloaded
        result = list(rstNos)
        try:
            vecs = extractFeaturesBatch(imgs)
            result.extend(_saveVectors(rstOKs, vecs))
            return result
        finally:
            for img in imgs:
                try: img.close()
                except Exception: pass
    return _processBatch(assets, photoQ)


def processVectors(assets: List[models.Asset], photoQ, onUpdate: models.IFnProg, isCancelled: models.IFnCancel) -> models.ProcessInfo:
    tS = time.time()
    pi = models.ProcessInfo(all=len(assets), done=0, skip=0, erro=0)
    if not assets:
        return pi

    batchSize = getOptimalBatchSize()
    device_type = conf.device.type
    decodeWorkers = _getDecodeWorkers(device_type)
    commitBatch = 100
    updAssets: list[models.Asset] = []
    cntDone = 0
    lastUpdate = 0.0

    logMemory(f"vector chunk start assets={len(assets)} device={device_type}")
    if onUpdate:
        onUpdate(15, f"Processing [{pi.all}] images on {device_type.upper()} (batch={batchSize}, decode={decodeWorkers})")

    def commitReady(force: bool = False):
        nonlocal updAssets
        if not updAssets or (not force and len(updAssets) < commitBatch):
            return
        batch = updAssets
        updAssets = []
        with db.pics.mkConn() as conn:
            cur = conn.cursor()
            db.pics.setVectoredBy(batch, cur=cur)
            conn.commit()

    def consume(results, batchIndex: int, totalBatches: int):
        nonlocal cntDone, lastUpdate
        for asset, error in results:
            cntDone += 1
            if error:
                lg.error(error)
                pi.erro += 1
            else:
                pi.done += 1
                updAssets.append(asset)
        commitReady(False)

        now = time.time()
        if onUpdate and (now - lastUpdate > 1 or batchIndex == totalBatches - 1):
            lastUpdate = now
            pct = 15 + int((cntDone / max(1, pi.all)) * 85)
            elapsed = max(0.001, now - tS)
            speed = cntDone / elapsed
            onUpdate(min(100, pct), f"{device_type.upper()}: {cntDone}/{pi.all} ok[{pi.done}] error[{pi.erro}] ({speed:.1f} items/sec)")

    try:
        batches = [assets[i:i + batchSize] for i in range(0, len(assets), batchSize)]
        prefetchDepth = 2 if device_type in ('cuda', 'mps') and len(batches) > 1 else 0

        if prefetchDepth:
            with ThreadPoolExecutor(max_workers=prefetchDepth) as pfExec:
                queue = deque()
                for idx in range(min(prefetchDepth, len(batches))):
                    queue.append((idx, pfExec.submit(loadTensorsParallel, batches[idx], photoQ, decodeWorkers)))

                for batchIdx, batch in enumerate(batches):
                    if isCancelled and isCancelled():
                        pi.erro += pi.all - cntDone
                        break
                    idx, future = queue.popleft()
                    loaded, failed = future.result()
                    nextIdx = batchIdx + prefetchDepth
                    if nextIdx < len(batches):
                        queue.append((nextIdx, pfExec.submit(loadTensorsParallel, batches[nextIdx], photoQ, decodeWorkers)))

                    results = list(failed)
                    if loaded:
                        okAssets = [asset for asset, _ in loaded]
                        tensors = [tensor for _, tensor in loaded]
                        try:
                            vecs = _extractTensorBatch(tensors)
                            results.extend(_saveVectors(okAssets, vecs))
                        except Exception as e:
                            lg.warning(f"[imgs] prefetched batch inference failed: {e}")
                            for asset, tensor in loaded:
                                try:
                                    vec = _extractTensorBatch([tensor])[0]
                                    results.extend(_saveVectors([asset], [vec]))
                                except Exception as singleError:
                                    results.append((asset, str(singleError)))
                        finally:
                            tensors.clear()
                            loaded.clear()
                    consume(results, batchIdx, len(batches))
        else:
            for batchIdx, batch in enumerate(batches):
                if isCancelled and isCancelled():
                    pi.erro += pi.all - cntDone
                    break
                consume(_processBatch(batch, photoQ), batchIdx, len(batches))

        commitReady(True)
        if onUpdate and not (isCancelled and isCancelled()):
            elapsed = max(0.001, time.time() - tS)
            onUpdate(100, f"Completed! done[{pi.done}] error[{pi.erro}] ({pi.done / elapsed:.1f} items/sec)")
        return pi
    except Exception as e:
        raise mkErr("Failed to generate vectors for assets", e)
    finally:
        gc.collect()
        logMemory(f"vector chunk end done={pi.done} error={pi.erro}")
