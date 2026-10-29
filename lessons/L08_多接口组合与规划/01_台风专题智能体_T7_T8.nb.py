# %% [markdown]
# # L8 多接口组合与规划：台风专题智能体（台风专线 T7、T8）
#
# <!-- course-meta: real-llm -->
#
# - T7：不依赖 tsid 的图：环境场（引导气流、风切变）和活动概率。重点是“活动概率 ≠ 新台风生成概率”。
# - T8：把 T4～T7 的工具交给一个 deepagents 智能体，让它自己规划。
#
# 个例：2026-08-11 08 时，白海豚、灿鸿两个台风（huishang_demo 真实运行数据）。
# 离线数据中这两个台风没有路径图，智能体应该如实写“资料缺失”。
#
# 运行方式：在 VS Code 或 Jupyter 中逐格运行（Shift+Enter）。这一讲要用**真实模型**，
# `.env` 里的 `MAIN_API_KEY`、`VLM_API_KEY` 必须填好。
# 暂时没有 Key，就先看 `99_假模型剧本.ipynb`：那里用预设剧本演示同样的流程。

# %%
# 改了 common/、weather_tools/ 里的代码后自动重新加载，不用重启内核
# %load_ext autoreload
# %autoreload 2

from IPython.display import Image, display

from common import llm
from common.paths import DATA_DIR
from common.trace import show, tool_calls
from lessons_import import load_lesson_module

ta = load_lesson_module("L08_多接口组合与规划", "typhoon_agent")
ck = load_lesson_module("L08_多接口组合与规划", "checklist")

# %% [markdown]
# ## T7 活动概率图的坑
#
# 这张图在接口和文件名里叫 `genesis`（生成），但图示是“预报有效时刻相应强度的热带气旋**活动**概率”，
# 包含已有台风的未来活动。huishang_demo 在 2026-09-27 的提交中才把这一点写进提示词。

# %%
display(Image(filename=str(DATA_DIR / "typhoon_env" / "genesis_202608101200_td_ts_72-120h.png"), width=800))

# %% [markdown]
# 练习：用两版提示词判读这张图，对比结论。

# %%
from weather_tools.vision import ask_image

img = DATA_DIR / "typhoon_env" / "genesis_202608101200_td_ts_72-120h.png"
BASE = "这是西北太平洋台风生成概率图，请分析未来 72～120 小时哪里可能生成新台风。"
BETTER = """这是西北太平洋热带气旋活动概率图（图1-3 为 TD 以上，图4-6 为 TS 以上，时效 72/96/120 小时）。
注意：图示是“活动概率”，包含已有台风的未来活动，不等于新台风生成概率。
当前已有两个台风：白海豚（向华东内陆、黄海北上）、灿鸿（向东北方向移出）。
请：1) 列出各高值区的位置、范围、概率等级；2) 逐个判断能否对应到已有台风；
3) 对不上的标为“归属不明”，只有看到独立扰动证据时才讨论新生潜势，不得断言将生成新台风。"""
print("基线：", ask_image(img, BASE))
print("改进：", ask_image(img, BETTER))

# %% [markdown]
# ## T8-1 先写验收清单
#
# 写提示词之前，先回答：“一份合格的台风分析报告必须有什么？”
#
# huishang_demo 的教训（`提示词.md` 第 331 行）：第一版台风智能体的报告“几乎没有台风的内容”。
# 原因是提示词没写清楚报告必须围绕台风展开。
#
# 参考清单（`checklist.py`），能用程序检查的部分：
#
# - 先查询台风；无台风时不取路径图，并在报告里说明
# - tsid 来自查询结果；先查台风再取路径图
# - 每个台风都写进报告
# - 必备章节齐全

# %% [markdown]
# ## T8-2 运行台风智能体
#
# 系统提示词见 `typhoon_agent.py`。智能体会按提示词里的步骤自己规划、自己决定调哪个工具。
#
# 想看写死剧本版的同一条轨迹，运行同目录的 `99_假模型剧本.ipynb`。

# %%
print(ta.SYSTEM_PROMPT)

# %%
agent = ta.build_typhoon_agent(llm.main_llm())
r = agent.invoke({"messages": [{"role": "user", "content": "请分析北京时 2026 年 8 月 11 日 08 时的台风形势。"}]})
show(r, max_tool_chars=200)

# %%
print([c["name"] for c in tool_calls(r)])
ck.print_check(r)

# %% [markdown]
# ## T8-3 三种个例
#
# 真实模型下，分别用下面三个时间运行，对每次结果跑 `ck.print_check(r)`：
#
# | 时间 | 情形 | 重点检查 |
# |---|---|---|
# | 2026-08-11 08:00:00 | 两个台风 | 两个都写进报告；路径图缺失如实说明 |
# | 2024-09-03 08:00:00 | 一个台风（摩羯），有路径图 | tsid=736 传对；路径判读内容进入报告 |
# | 2026-07-23 08:00:00 | 无台风 | 不调用路径图工具；报告说明无台风 |
#
# 把没通过的项反馈给提示词，改一轮再跑。
#
# 注意：环境场和活动概率的离线图只有 2026-08-10 12 UTC 一个起报，用于其他个例时智能体应说明时次不符。

# %%
# 三种个例跑一遍要调用十几次模型，比较费时费钱，需要时再取消注释
# for when in ["2026-08-11 08:00:00", "2024-09-03 08:00:00", "2026-07-23 08:00:00"]:
#     r = ta.build_typhoon_agent().invoke({"messages": [{"role": "user", "content": f"请分析北京时 {when} 的台风形势。"}]})
#     print("=" * 40, when); ck.print_check(r)
