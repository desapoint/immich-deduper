#!/usr/bin/env python3

"""Lightweight contract checks for the image-model runtime.

These checks deliberately inspect the source instead of importing imgs: importing
that module currently loads torch/torchvision, which would make this regression
check itself consume the memory it is intended to help reduce in later steps.
"""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
IMGS = ROOT / "src" / "imgs.py"


def _tree():
    return ast.parse(IMGS.read_text(encoding="utf-8"), filename=str(IMGS))


def _function(name):
    for node in _tree().body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"missing imgs.{name}")


def _calls(function, name):
    return [
        node for node in ast.walk(function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name
    ]


def test_model_is_created_lazily():
    tree = _tree()
    assignments = [
        node for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "_model" for target in node.targets)
    ]
    assert assignments, "imgs must define a module-level model cache"
    assert isinstance(assignments[0].value, ast.Constant) and assignments[0].value.value is None, (
        "the model cache must start empty so ResNet weights are not instantiated until needed"
    )


def test_feature_extraction_uses_shared_model_cache():
    single = _function("extractFeatures")
    batch = _function("extractFeaturesBatch")
    assert _calls(single, "getModel"), "single-image extraction bypasses the shared model cache"
    assert _calls(batch, "getModel"), "batch extraction bypasses the shared model cache"


def test_get_model_keeps_singleton_contract():
    get_model = _function("getModel")
    source = ast.get_source_segment(IMGS.read_text(encoding="utf-8"), get_model) or ""
    assert "if _model is None" in source, "getModel must not rebuild the model on every extraction"
    assert any(
        isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == "_model"
        for node in ast.walk(get_model)
    ), "getModel must return the cached model"


if __name__ == "__main__":
    test_model_is_created_lazily()
    test_feature_extraction_uses_shared_model_cache()
    test_get_model_keeps_singleton_contract()
    print("model runtime contract tests passed")
