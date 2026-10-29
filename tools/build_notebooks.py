"""讲师用：把 lessons 下的 *.nb.py（jupytext percent 格式）转换成 .ipynb，并可选执行验证。

用法：
    uv run python tools/build_notebooks.py            # 只转换
    uv run python tools/build_notebooks.py --execute  # 转换并在 FAKE 模式下执行全部 notebook

.nb.py 是 notebook 的源文件，方便用 git 查看改动；学员使用 .ipynb。
"""
import argparse
import os
import sys
from pathlib import Path

import jupytext
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent.parent


def convert(src: Path) -> Path:
    nb = jupytext.read(src)
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    dst = src.with_name(src.name.replace(".nb.py", ".ipynb"))
    nbformat.write(nb, dst)
    return dst


def needs_real_llm(src: Path) -> bool:
    """源文件头部标了 course-meta: real-llm 的，只转换、不执行（执行需要真实模型，会花钱且结果不稳定）。"""
    return "course-meta: real-llm" in src.read_text(encoding="utf-8")[:500]


def execute(path: Path) -> None:
    nb = nbformat.read(path, as_version=4)
    NotebookClient(nb, timeout=600, kernel_name="python3",
                   resources={"metadata": {"path": str(path.parent)}}).execute()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("pattern", nargs="?", default="*")
    args = ap.parse_args()
    if args.execute:
        os.environ["COURSE_FAKE_LLM"] = "1"
    failed = []
    for src in sorted((ROOT / "lessons").glob(f"{args.pattern}/*.nb.py")):
        dst = convert(src)
        status = "已转换"
        if args.execute:
            if needs_real_llm(src):
                status = "已转换（需真实模型，跳过执行）"
                print(f"{dst.relative_to(ROOT)}  {status}")
                continue
            try:
                execute(dst)
                status = "已转换，执行通过"
            except Exception as exc:
                status = f"执行失败：{type(exc).__name__}: {str(exc)[-300:]}"
                failed.append(dst)
        print(f"{dst.relative_to(ROOT)}  {status}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
