#!/usr/bin/env python3

"""Regression guard for the shared image-model cache declaration."""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
IMGS = ROOT / "src" / "imgs.py"


def test_model_cache_has_one_lazy_module_declaration():
    tree = ast.parse(IMGS.read_text(encoding="utf-8"), filename=str(IMGS))
    assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "_model" for target in node.targets)
    ]

    assert len(assignments) == 1, (
        "the shared model cache must have exactly one module-level declaration; "
        f"found {len(assignments)}"
    )
    value = assignments[0].value
    assert isinstance(value, ast.Constant) and value.value is None, (
        "the shared model cache must start empty so model construction stays lazy"
    )


if __name__ == "__main__":
    test_model_cache_has_one_lazy_module_declaration()
    print("model cache declaration test passed")
