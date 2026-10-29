"""让测试和 notebook 能导入 lessons/中文目录 下的模块。

中文目录名不能直接 import，用这个函数按路径加载。
"""
import importlib.util
import sys
from pathlib import Path

LESSONS = Path(__file__).resolve().parent / "lessons"


def load_lesson_module(lesson_dir: str, module: str):
    path = LESSONS / lesson_dir / f"{module}.py"
    name = f"lesson_{lesson_dir}_{module}".replace("-", "_")
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod
