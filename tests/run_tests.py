#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import inspect
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def invoke_test(func):
    params = inspect.signature(func).parameters
    if not params:
        func()
        return
    kwargs = {}
    for name in params:
        if name == "tmp_path":
            kwargs[name] = Path(tempfile.mkdtemp(prefix="rss-workflow-test-"))
        else:
            raise RuntimeError(f"unsupported test fixture: {name}")
    func(**kwargs)


def main() -> int:
    failures = []
    test_files = sorted(path for path in ROOT.glob("test_*.py") if path.name != "run_tests.py")
    for test_file in test_files:
        module = load_module(test_file)
        for name in sorted(dir(module)):
            if not name.startswith("test_"):
                continue
            obj = getattr(module, name)
            if callable(obj):
                try:
                    invoke_test(obj)
                    print(f"PASS {test_file.name}::{name}")
                except Exception as exc:
                    failures.append((test_file.name, name, exc))
                    print(f"FAIL {test_file.name}::{name} :: {exc}")
    if failures:
        return 1
    print(f"ALL PASS ({len(test_files)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
