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


def test_failed_initialization_leaves_cache_empty_and_allows_retry():
    lock = threading.Lock()
    model = None
    attempts = 0

    def get_model():
        nonlocal model, attempts
        if model is None:
            with lock:
                if model is None:
                    attempts += 1
                    if attempts == 1:
                        raise RuntimeError("simulated model load failure")
                    model = object()
        return model

    try:
        get_model()
    except RuntimeError as exc:
        assert str(exc) == "simulated model load failure"
    else:
        raise AssertionError("the first model load should fail")

    assert model is None, "failed initialization must not publish a partial cached model"

    recovered = get_model()
    assert recovered is model
    assert attempts == 2
    assert get_model() is recovered
    assert attempts == 2, "successful retry should restore the lock-free cached path"


def test_failed_candidate_setup_is_not_published_and_retry_rebuilds_it():
    lock = threading.Lock()
    model = None
    attempts = 0
    candidates = []

    class Candidate:
        ready = False

    def get_model():
        nonlocal model, attempts
        if model is None:
            with lock:
                if model is None:
                    attempts += 1
                    candidate = Candidate()
                    candidates.append(candidate)
                    if attempts == 1:
                        raise RuntimeError("simulated device setup failure")
                    candidate.ready = True
                    model = candidate
        return model

    try:
        get_model()
    except RuntimeError as exc:
        assert str(exc) == "simulated device setup failure"
    else:
        raise AssertionError("candidate setup should fail before publication")

    assert model is None, "a candidate that fails setup must never enter the shared cache"
    assert len(candidates) == 1 and not candidates[0].ready

    recovered = get_model()
    assert recovered is model
    assert recovered.ready
    assert attempts == 2
    assert len(candidates) == 2
    assert recovered is candidates[1], "retry must publish a freshly configured candidate"


def test_concurrent_readers_never_observe_model_before_initialization_finishes():
    lock = threading.Lock()
    model = None
    initialization_started = threading.Event()
    allow_initialization_to_finish = threading.Event()

    class Candidate:
        ready = False

    def get_model():
        nonlocal model
        if model is None:
            with lock:
                if model is None:
                    candidate = Candidate()
                    initialization_started.set()
                    assert allow_initialization_to_finish.wait(timeout=1)
                    candidate.ready = True
                    model = candidate
        return model

    with ThreadPoolExecutor(max_workers=8) as executor:
        first = executor.submit(get_model)
        assert initialization_started.wait(timeout=1)
        readers = [executor.submit(get_model) for _ in range(7)]
        time.sleep(0.01)
        allow_initialization_to_finish.set()

        models = [first.result(timeout=1)] + [future.result(timeout=1) for future in readers]

    assert all(value.ready for value in models), (
        "the shared cache must not expose a model until device/setup initialization is complete"
    )
    assert len({id(value) for value in models}) == 1


def test_concurrent_waiters_recover_after_first_initializer_fails():
    lock = threading.Lock()
    model = None
    attempts = 0
    first_attempt_started = threading.Event()
    allow_first_attempt_to_fail = threading.Event()

    def get_model():
        nonlocal model, attempts
        if model is None:
            with lock:
                if model is None:
                    attempts += 1
                    if attempts == 1:
                        first_attempt_started.set()
                        assert allow_first_attempt_to_fail.wait(timeout=1)
                        raise RuntimeError("simulated first initializer failure")
                    model = object()
        return model

    with ThreadPoolExecutor(max_workers=8) as executor:
        first = executor.submit(get_model)
        assert first_attempt_started.wait(timeout=1)
        waiters = [executor.submit(get_model) for _ in range(7)]
        time.sleep(0.01)
        allow_first_attempt_to_fail.set()

        try:
            first.result(timeout=1)
        except RuntimeError as exc:
            assert str(exc) == "simulated first initializer failure"
        else:
            raise AssertionError("the first initializer should fail")

        recovered = [future.result(timeout=1) for future in waiters]

    assert attempts == 2, "only one waiter should retry initialization after the failure"
    assert model is not None
    assert all(value is model for value in recovered), (
        "all waiters must converge on the one model published by the successful retry"
    )


if __name__ == "__main__":
    test_double_checked_lock_serializes_lazy_initialization_and_keeps_hot_path_lock_free()
    test_failed_initialization_leaves_cache_empty_and_allows_retry()
    test_failed_candidate_setup_is_not_published_and_retry_rebuilds_it()
    test_concurrent_readers_never_observe_model_before_initialization_finishes()
    test_concurrent_waiters_recover_after_first_initializer_fails()
    print("model lock primitive tests passed")
