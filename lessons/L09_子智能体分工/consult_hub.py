"""会商中枢 + 专题子智能体（台风专线 T9 参考答案）。

结构参照 huishang_demo/src/new_weather_situation_agent.py 的 build_subagents：
子智能体用字典声明（name / description / system_prompt / tools / model）。
中枢通过 deepagents 内置的 task 工具派活，子智能体只把结论交回中枢。
"""
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

from common import llm
from common.paths import COURSE_ROOT
from lessons_import import load_lesson_module
from weather_tools.agent_tools import get_beijing_time

ta = load_lesson_module("L08_多接口组合与规划", "typhoon_agent")


def obs_tools():
    """实况组用的工具：最高气温实况图判读（离线：2024 年冬季 3 张图）。"""
    from langchain_core.tools import tool

    from common.paths import DATA_DIR
    from weather_tools.vision import interpret_image

    @tool
    def interpret_tmax_obs_chart(date: str, prompt: str = "") -> str:
        """判读广东最高气温实况图。date 为日期 YYYYMMDD，离线仅有 20240101、20240106、20240114。"""
        p = DATA_DIR / "tmax" / "images" / f"hs_temp_max_from20_{date}20.png"
        if not p.exists():
            return f"没有 {date} 的最高气温实况图"
        return interpret_image(p, prompt or "请描述广东各区域最高气温分布，指出全省最高值所在区县。",
                               meta=f"产品：最高气温实况\n日期：{date}")

    return [interpret_tmax_obs_chart]


HUB_PROMPT = """你是广东省气象台的会商首席。你的任务是组织各专题组，形成会商意见。

工作方式：
1. 先用 write_todos 列出计划。
2. 用 task 工具把专题任务交给对应的子智能体，一次交一个，写清楚时间（北京时）和要回答的问题。
3. 台风组：只有用户问到台风、或需要判断台风影响时才调用。台风组报告“没有活动台风”时，会商意见里写一句即可。
4. 汇总各组结论，写成会商意见：重点天气 / 实况 / 台风 / 关注建议。各组结论有冲突时指出来。
5. 只用各组交回的内容，不要自己编数据。
"""


def subagent_specs(models: dict | None = None) -> list[dict]:
    """models 可为每个子智能体指定模型（FAKE 模式下传入各自的剧本模型）。"""
    models = models or {}
    return [
        {
            "name": "typhoon-analyst",
            "description": "台风组。查询西北太平洋活动台风，分析路径、强度、环境场和对广东的影响。"
                           "用户问到台风或需要判断台风影响时调用。任务里要写明北京时。",
            "system_prompt": ta.SYSTEM_PROMPT,
            "tools": ta.TOOLS,
            **({"model": models["typhoon-analyst"]} if "typhoon-analyst" in models else {}),
        },
        {
            "name": "obs-analyst",
            "description": "实况组。判读最高气温等实况图，给出过去 24 小时实况要点。",
            "system_prompt": "你是实况分析员。调用工具判读实况图，用 3～5 条要点交回结论，只写图上有的内容。",
            "tools": obs_tools(),
            **({"model": models["obs-analyst"]} if "obs-analyst" in models else {}),
        },
    ]


def build_hub(model=None, sub_models: dict | None = None):
    return create_deep_agent(
        model=model or llm.main_llm(),
        tools=[get_beijing_time],
        system_prompt=HUB_PROMPT,
        subagents=subagent_specs(sub_models),
        skills=["/skills/"],
        backend=FilesystemBackend(root_dir=str(COURSE_ROOT), virtual_mode=True),
    )
