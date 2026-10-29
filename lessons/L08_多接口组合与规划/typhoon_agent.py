"""台风专题智能体（台风专线 T8 参考答案）。

系统提示词要点来自 huishang_demo/src/typhoon_case_deep_agent.py，按课程离线数据裁剪。
运行：uv run python "lessons/L08_多接口组合与规划/typhoon_agent.py" "2026-08-11 08:00:00"
"""
import sys

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain.agents.middleware import ToolCallLimitMiddleware

from common import llm
from common.paths import COURSE_ROOT
from weather_tools.agent_tools import (
    get_beijing_time,
    get_typhoon_data_by_datetime,
    interpret_tc_env_chart,
    interpret_tc_genesis_prob_chart,
    interpret_tc_track_forecast_chart,
)

TOOLS = [
    get_beijing_time,
    get_typhoon_data_by_datetime,
    interpret_tc_track_forecast_chart,
    interpret_tc_env_chart,
    interpret_tc_genesis_prob_chart,
]

SYSTEM_PROMPT = """你是广东省气象台的台风分析员，负责写台风专题分析。用户说的时间都是北京时。

## 工作步骤
1. 先用 write_todos 列出计划。
2. 调用 get_typhoon_data_by_datetime 查询活动台风。直接传北京时，不要自己加减 8 小时。
   - 返回 status 为 not_applicable：说明过去 24 小时没有活动台风，跳到第 5 步，不要调用路径图工具。
   - 返回多个台风：每个台风都要有概况和路径趋势结论，不能因为它不影响广东就省略。
3. 对每个台风，用查询结果里的 tsid 调用 interpret_tc_track_forecast_chart。tsid 必须来自查询结果，不要自己编。
4. 用 interpret_tc_env_chart 分析引导气流和垂直风切变，解释路径和强度的成因。
5. 用 interpret_tc_genesis_prob_chart 分析未来 72～120 小时活动概率。
   图示是“活动概率”，包含已有台风的未来活动。先把高值区和已有台风的位置、路径对照：
   对得上的说明为该台风的活动概率；只有排除已有台风且有独立扰动证据时才讨论新生潜势；对不上的写“归属不明”。
6. 写报告。

## 工具调用
- 工具一次只调用一个。
- 每次调用写清判读要求：区域、要素、要量化的信息。

## 报告
- 第一行用 Markdown 一级标题概括最值得关注的台风动态。
- 章节：台风概况 / 路径预报 / 环境场与成因 / 活动概率与潜势 / 对广东和南海的影响 / 结论 / 资料说明。
- 每个台风写清编号、名称、位置、强度、移动趋势。等级按 typhoon-grade 技能判断。
- 时间一律写北京时，写成“8 月 11 日 08 时”。资料时次是回查得到的，要在“资料说明”里写明。
- 只写工具结果里有的内容，没有资料的写“资料缺失”，不要编。
"""


def build_typhoon_agent(model=None, *, tool_limit: int = 15):
    return create_deep_agent(
        model=model or llm.main_llm(),
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        skills=["/skills/"],
        backend=FilesystemBackend(root_dir=str(COURSE_ROOT), virtual_mode=True),
        middleware=[ToolCallLimitMiddleware(run_limit=tool_limit)],
    )


if __name__ == "__main__":
    when = sys.argv[1] if len(sys.argv) > 1 else "2026-08-11 08:00:00"
    agent = build_typhoon_agent()
    result = agent.invoke({"messages": [{"role": "user", "content": f"请分析北京时 {when} 的台风形势。"}]})
    print(result["messages"][-1].text)
