#!/usr/bin/env python3

"""Regression guard for publishing the shared image model atomically."""

import ast
from pathlib import Path


IMGS = Path(__file__).resolve().parent.parent / "src" / "imgs.py"


def _tree():
    return ast.parse(IMGS.read_text(encoding="utf-8"), filename=str(IMGS))


def _get_model():
    return next(
        node for node in _tree().body
        if isinstance(node, ast.FunctionDef) and node.name == "getModel"
    )


def test_model_cache_starts_empty_at_module_scope():
    assignments = [
        node for node in _tree().body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "_model" for target in node.targets)
    ]
    assert len(assignments) == 1, "the shared model cache should have one module-level initializer"
    initializer = assignments[0].value
    assert isinstance(initializer, ast.Constant) and initializer.value is None, (
        "the shared model cache must start empty so importing imgs cannot eagerly allocate ResNet"
    )


def test_all_model_publication_stays_inside_cache_miss_guard():
    get_model = _get_model()
    guards = [
        node for node in ast.walk(get_model)
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "_model"
        and len(node.test.ops) == 1
        and isinstance(node.test.ops[0], ast.Is)
        and len(node.test.comparators) == 1
        and isinstance(node.test.comparators[0], ast.Constant)
        and node.test.comparators[0].value is None
    ]
    assert len(guards) == 1, "getModel must keep one cache-miss initialization guard"

    guard = guards[0]
    guarded_nodes = set(ast.walk(guard))
    publications = [
        node for node in ast.walk(get_model)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "_model" for target in node.targets)
    ]
    assert publications, "getModel must publish the initialized model"
    assert all(node in guarded_nodes for node in publications), (
        "every shared-model publication must stay inside the cache-miss guard so the full "
        "construction/device-transfer sequence can be protected by one lock"
    )


if __name__ == "__main__":
    test_model_cache_starts_empty_at_module_scope()
    test_all_model_publication_stays_inside_cache_miss_guard()
    print("model initialization guard tests passed")
