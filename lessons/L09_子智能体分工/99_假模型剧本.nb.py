# %% [markdown]
# # L9 附：假模型剧本（会商中枢 T9）
#
# 这个 notebook 是 `01_会商中枢_T9.ipynb` 的**剧本版**，专门给还没配好 Key 的学员熟悉流程。
#
# 三点要说清：
#
# 1. 这里模型**不会思考**，只是照剧本念台词。中枢和两个子智能体各有一份剧本（写在 `llm.agent_model(...)` 里）。
# 2. 轨迹结构、消息顺序和真实模型一样，可以照着看懂“中枢派活 → 子智能体交回结论 → 中枢汇总”。
# 3. 派不派活、派给谁，全是写死的，所以看不出 `description` 写得好不好。想体会真实行为，请回 `01_会商中枢_T9.ipynb`。

# %%
import os

# 这一讲专门演假模型，强制打开（不依赖 .env 的设置）
os.environ["COURSE_FAKE_LLM"] = "1"

from common import llm
from common.fake import call, scripted
from common.trace import show, tool_calls
from lessons_import import load_lesson_module

hub = load_lesson_module("L09_子智能体分工", "consult_hub")

print("FAKE 模式" if llm.use_fake_llm() else "真实模型模式")

# %%
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
# `description` 决定中枢什么时候派活。这一节和真实模型无关，可以照做。

# %% [markdown]
# ## 2. 运行中枢（剧本）
#
# **这是剧本**：中枢依次派两个活，再汇总；两个子智能体各自按剧本回一句结论。

# %%
main = scripted(
    call("task", "t1", description="查询并分析北京时 2026-07-23 08 时的台风形势", subagent_type="typhoon-analyst"),
    call("task", "t2", description="判读 20240114 的最高气温实况", subagent_type="obs-analyst"),
    "## 会商意见\n### 台风\n过去 24 小时西北太平洋无活动台风。\n### 实况\n粤西、珠三角南部最高气温较高……\n### 关注建议\n……",
)
subs = {
    "typhoon-analyst": scripted(call("get_typhoon_data_by_datetime", datetime="2026-07-23 08:00:00"),
                                "过去 24 小时没有活动台风，未调用路径图工具。"),
    "obs-analyst": scripted(call("interpret_tmax_obs_chart", date="20240114"),
                            "1. 粤西、珠三角南部最高气温较高……"),
}
agent = hub.build_hub(main, subs)

r = agent.invoke({"messages": [{"role": "user", "content": "请给出北京时 2026 年 7 月 23 日 08 时的早间会商意见，包括台风情况。"}]})
show(r, max_tool_chars=300)

# %%
for c in tool_calls(r):
    if c["name"] == "task":
        print("派给", c["args"].get("subagent_type"), "：", c["args"].get("description"))

# %% [markdown]
# 注意：中枢的轨迹里只能看到 `task` 调用和子智能体交回的一句话，看不到台风组内部调用了哪些工具。
# 这就是“上下文隔离”：中枢不被大量工具结果淹没。
#
# 这个结构在真模型下也是这样；不同的是真模型会自己判断该派给谁、要不要派。

# %% [markdown]
# ## 3. 练习：把 description 改含糊
#
# 把台风组的 description 改成“分析员”，再问一次，看中枢还会不会派给它。
#
# 这里模型是剧本，改了 description 也看不出效果，需要在 `01_会商中枢_T9.ipynb` 用真实模型做。

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
# 然后问“明天广东降水怎么样”，看中枢是否派给降水组（同样要用真实模型才看得出效果）。
