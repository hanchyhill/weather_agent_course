# %% [markdown]
# # L9 子智能体分工：会商中枢（台风专线 T9）
#
# <!-- course-meta: real-llm -->
#
# 会商的分工：首席（中枢）派活，各组分析，首席汇总定调。
#
# - 台风组：直接复用 L8 的台风专题智能体（系统提示词和工具都不变）。
# - 实况组：判读最高气温实况图。
#
# 子智能体之间不共享对话，只把结论交回中枢。
#
# 运行方式：在 VS Code 或 Jupyter 中逐格运行（Shift+Enter）。这一讲要用**真实模型**，
# `.env` 里的 `MAIN_API_KEY`、`VLM_API_KEY` 必须填好。
# 暂时没有 Key，就先看 `99_假模型剧本.ipynb`：那里用预设剧本演示同样的流程。

# %%
# 改了 common/、weather_tools/ 里的代码后自动重新加载，不用重启内核
# %load_ext autoreload
# %autoreload 2

from common.trace import show, tool_calls
from lessons_import import load_lesson_module

hub = load_lesson_module("L09_子智能体分工", "consult_hub")

for s in hub.subagent_specs():
    print(s["name"], "：", s["description"])

# %% [markdown]
# ## 1. 分工表（小组练习）
#
# | 子智能体 | 负责什么 | 用哪些工具 | 交回什么格式 |
# |---|---|---|---|
# | typhoon-analyst | | | |
# | obs-analyst | | | |
# | （你们组加的） | | | |
#
# `description` 决定中枢什么时候派活。写得含糊，中枢就会派错或不派。

# %% [markdown]
# ## 2. 运行中枢
#
# 中枢和两个子智能体都用真实模型，各自按系统提示词决定怎么干活。
#
# 想看写死剧本版的同一条轨迹（中枢派活、子智能体交回结论），运行同目录的 `99_假模型剧本.ipynb`。

# %%
agent = hub.build_hub()

r = agent.invoke({"messages": [{"role": "user", "content": "请给出北京时 2026 年 7 月 23 日 08 时的早间会商意见，包括台风情况。"}]})
show(r, max_tool_chars=300)

# %%
for c in tool_calls(r):
    if c["name"] == "task":
        print("派给", c["args"].get("subagent_type"), "：", c["args"].get("description"))

# %% [markdown]
# 注意：中枢的轨迹里只能看到 `task` 调用和子智能体交回的一句话，看不到台风组内部调用了哪些工具。
# 这就是“上下文隔离”：中枢不被大量工具结果淹没。

# %% [markdown]
# ## 3. 练习：把 description 改含糊
#
# 把台风组的 description 改成“分析员”，再问一次，看中枢还会不会派给它。

# %%
specs = hub.subagent_specs()
specs[0]["description"] = "分析员"
print([s["description"] for s in specs])
# 用 create_deep_agent(..., subagents=specs) 重建中枢再运行

# %% [markdown]
# ## 4. 练习：新增一个降水组
#
# 让 Claude Code 在 `consult_hub.py` 的 `subagent_specs` 里加一个 `rain-analyst`，
# 工具可用 L6 的四宫格降水判读（`data/nwp/2025090208_024_rain24.png`）。
# 然后问“明天广东降水怎么样”，看中枢是否派给降水组。
