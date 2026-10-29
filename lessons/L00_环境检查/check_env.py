"""环境自检：逐项检查 Python、依赖、模型、离线数据和课程时间。

运行：uv run python lessons/L00_环境检查/check_env.py
"""
import importlib
import os
import sys

from common.paths import COURSE_ROOT, DATA_DIR

results: list[tuple[str, bool, str]] = []


def check(name: str):
    def deco(fn):
        try:
            detail = fn() or ""
            results.append((name, True, detail))
        except Exception as exc:  # 自检脚本要把所有错误都展示出来
            results.append((name, False, f"{type(exc).__name__}: {exc}"))
        return fn
    return deco


@check("Python 版本 ≥ 3.13")
def _():
    v = sys.version_info
    assert v >= (3, 13), f"当前 {v.major}.{v.minor}"
    return f"{v.major}.{v.minor}.{v.micro}"


@check("依赖可以导入")
def _():
    names = ["langchain", "langchain_openai", "deepagents", "langgraph", "PIL", "pandas"]
    for n in names:
        importlib.import_module(n)
    import deepagents
    import langchain
    return f"langchain {langchain.__version__}，deepagents {deepagents.__version__}"


@check("Jupyter 内核（运行 .ipynb）")
def _():
    import ipykernel
    from jupyter_client.kernelspec import KernelSpecManager
    specs = KernelSpecManager().find_kernel_specs()
    assert "python3" in specs, "没有找到 python3 内核，请重新执行 uv sync"
    in_venv = ".venv" in sys.executable
    assert in_venv, f"当前 Python 不在课程包的 .venv 里：{sys.executable}"
    return f"ipykernel {ipykernel.__version__}，内核位置 {specs['python3']}"


@check(".env 文件存在")
def _():
    assert (COURSE_ROOT / ".env").exists(), "请复制 .env.example 为 .env 并填写"


@check("离线数据完整")
def _():
    need = ["typhoon_api/getyphdata.json", "typhoon_track/images/736_2024090300.png",
            "tmax_desc/gemini-3-flash.json", "tmax/truth/hs_temp_max_from20_2024010120.csv"]
    missing = [p for p in need if not (DATA_DIR / p).exists()]
    assert not missing, f"缺少 {missing}"


@check("课程时间与起报时次换算")
def _():
    from common.clock import now_bj
    from weather_tools.timeutil import latest_init_time
    now = now_bj()
    return f"当前北京时 {now:%Y-%m-%d %H:%M}，最新 ECMWF 起报 {latest_init_time(now)} UTC"


@check("主模型（文字 + 工具调用）")
def _():
    from common import llm
    if llm.use_fake_llm():
        return "COURSE_FAKE_LLM=1，已跳过"
    from langchain.agents import create_agent
    from weather_tools.agent_tools import get_beijing_time
    agent = create_agent(llm.main_llm(), tools=[get_beijing_time])
    r = agent.invoke({"messages": [{"role": "user", "content": "现在北京时间几点？只回答时间。"}]})
    called = any(getattr(m, "tool_calls", None) for m in r["messages"])
    assert called, "模型没有调用工具"
    return f"{os.getenv('MAIN_MODEL')} 回答：{r['messages'][-1].text[:40]}"


@check("视觉模型（看图）")
def _():
    from common import llm
    if llm.use_fake_llm():
        return "COURSE_FAKE_LLM=1，已跳过"
    from weather_tools.vision import ask_image
    img = DATA_DIR / "typhoon_track" / "images" / "736_2024090300.png"
    a = ask_image(img, "这张图是什么气象产品？用一句话回答。")
    return f"{os.getenv('VLM_MODEL')} 回答：{a[:60]}"


@check("备用视觉模型（可选）")
def _():
    from common import llm
    if llm.use_fake_llm() or not os.getenv("ALT_VLM_API_KEY"):
        return "未配置，已跳过"
    from weather_tools.vision import ask_image
    img = DATA_DIR / "typhoon_track" / "images" / "736_2024090300.png"
    a = ask_image(img, "这张图是什么气象产品？用一句话回答。", alt=True)
    return f"{os.getenv('ALT_VLM_MODEL')} 回答：{a[:60]}"


if __name__ == "__main__":
    print("=" * 60)
    for name, ok, detail in results:
        print(f"{'通过' if ok else '失败'}  {name}  {detail}")
    print("=" * 60)
    failed = [r for r in results if not r[1]]
    print("全部通过" if not failed else f"{len(failed)} 项未通过，请对照《课前准备》第 11 节处理")
    sys.exit(1 if failed else 0)
