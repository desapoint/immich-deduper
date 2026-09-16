#!/usr/bin/env python3

"""Regression proof for the synchronization primitive used by lazy model loading.

This stays independent of torch/torchvision so CI can exercise concurrent startup
without allocating the real ResNet. The production integration can reuse the same
double-checked locking pattern while the existing source-contract tests protect
publication, device placement, eval mode, and lazy loading.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor


def test_double_checked_lock_serializes_lazy_initialization_and_keeps_hot_path_lock_free():
    lock = threading.Lock()
    model = None
    initializations = 0
    lock_acquisitions = 0

    def get_model():
        nonlocal model, initializations, lock_acquisitions
        if model is None:
            with lock:
                lock_acquisitions += 1
                if model is None:
                    # Release the GIL long enough for competing workers to reach the lock.
                    time.sleep(0.01)
                    initializations += 1
                    model = object()
        return model

    with ThreadPoolExecutor(max_workers=8) as executor:
        models = list(executor.map(lambda _: get_model(), range(32)))

    assert initializations == 1
    assert len({id(value) for value in models}) == 1

    acquisitions_after_startup = lock_acquisitions
    for _ in range(32):
        assert get_model() is model
    assert lock_acquisitions == acquisitions_after_startup, (
        "cached model acquisition should not contend on the initialization lock"
    )


if __name__ == "__main__":
    test_double_checked_lock_serializes_lazy_initialization_and_keeps_hot_path_lock_free()
    print("model lock primitive test passed")
