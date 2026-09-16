#!/usr/bin/env python3

"""Regression guard for persistent model-cache setup ordering."""

import ast
from pathlib import Path


IMGS = Path(__file__).resolve().parent.parent / "src" / "imgs.py"


def test_model_cache_directory_exists_before_torch_cache_and_weight_load():
    tree = ast.parse(IMGS.read_text(encoding="utf-8"), filename=str(IMGS))
    get_model = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "getModel"
    )

    calls = [node for node in ast.walk(get_model) if isinstance(node, ast.Call)]
    makedirs = [
        node for node in calls
        if isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "os"
        and node.func.attr == "makedirs"
    ]
    set_dirs = [
        node for node in calls
        if isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Attribute)
        and isinstance(node.func.value.value, ast.Name)
        and node.func.value.value.id == "torch"
        and node.func.value.attr == "hub"
        and node.func.attr == "set_dir"
    ]
    resnets = [
        node for node in calls
        if isinstance(node.func, ast.Name) and node.func.id == "resnet152"
    ]

    assert len(makedirs) == len(set_dirs) == len(resnets) == 1
    assert makedirs[0].lineno < set_dirs[0].lineno < resnets[0].lineno, (
        "getModel must create the persistent model directory before configuring torch.hub, "
        "and configure torch.hub before ResNet weights are loaded"
    )

    guards = [
        node for node in ast.walk(get_model)
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "_model"
    ]
    assert len(guards) == 1
    guarded = set(ast.walk(guards[0]))
    assert all(node in guarded for node in (makedirs[0], set_dirs[0], resnets[0])), (
        "cache setup and weight loading must stay inside lazy initialization"
    )


if __name__ == "__main__":
    test_model_cache_directory_exists_before_torch_cache_and_weight_load()
    print("model cache setup order test passed")
