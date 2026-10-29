# %% [markdown]
# # L8 附：假模型剧本（T7、T8）
#
# 这个 notebook 是 `01_台风专题智能体_T7_T8.ipynb` 的**剧本版**，专门给还没配好 Key 的学员熟悉流程。
#
# 三点要说清：
#
# 1. 这里模型**不会思考**，只是照剧本念台词。剧本写在代码里（`llm.agent_model(...)` 的参数），不是模型自己想出来的。
# 2. 轨迹结构、消息顺序和真实模型一样，可以照着看懂“先查台风 → 再取图 → 写报告”的链式调用和任务规划。
# 3. 判读结论、报告内容都是写死的，检验不出提示词好坏。想体会真实行为，请回 `01_台风专题智能体_T7_T8.ipynb`。

# %%
import os

# 这一讲专门演假模型，强制打开（不依赖 .env 的设置）
os.environ["COURSE_FAKE_LLM"] = "1"

from IPython.display import Image, display

from common import llm
from common.fake import call
from common.paths import DATA_DIR
from common.trace import show, tool_calls
from lessons_import import load_lesson_module

ta = load_lesson_module("L08_多接口组合与规划", "typhoon_agent")
ck = load_lesson_module("L08_多接口组合与规划", "checklist")

print("FAKE 模式" if llm.use_fake_llm() else "真实模型模式")

# %% [markdown]
# ## T7 活动概率图的坑
#
# 图和正式 notebook 一样是真的，只有判读结论是剧本。

# %%
display(Image(filename=str(DATA_DIR / "typhoon_env" / "genesis_202608101200_td_ts_72-120h.png"), width=800))

# %% [markdown]
# 同一张图问两版提示词。**这是剧本**：两段判读都是写死的，看不出提示词改进的效果。

# %%
from weather_tools.vision import ask_image

img = DATA_DIR / "typhoon_env" / "genesis_202608101200_td_ts_72-120h.png"
BASE = "这是西北太平洋台风生成概率图，请分析未来 72～120 小时哪里可能生成新台风。"
BETTER = """这是西北太平洋热带气旋活动概率图（图1-3 为 TD 以上，图4-6 为 TS 以上，时效 72/96/120 小时）。
注意：图示是“活动概率”，包含已有台风的未来活动，不等于新台风生成概率。
当前已有两个台风：白海豚（向华东内陆、黄海北上）、灿鸿（向东北方向移出）。
请：1) 列出各高值区的位置、范围、概率等级；2) 逐个判断能否对应到已有台风；
3) 对不上的标为“归属不明”，只有看到独立扰动证据时才讨论新生潜势，不得断言将生成新台风。"""
print("基线：", ask_image(img, BASE, fake_answer="（FAKE）菲律宾以东将生成新台风……"))
print("改进：", ask_image(img, BETTER, fake_answer="（FAKE）高值区 1 对应白海豚……"))

# %% [markdown]
# ## T8-1 验收清单
#
# `checklist.py` 是真的：它只看运行轨迹和报告文字，与模型是不是剧本无关。

# %% [markdown]
# ## T8-2 运行台风智能体
#
# **这是剧本**：先 `write_todos` 列计划，再依次查台风、取两张路径图、取环境场和活动概率图，最后交一份写好的报告。
# 真实模型会自己决定顺序、自己写报告，那一份在 `01_台风专题智能体_T7_T8.ipynb`。

# %%
print(ta.SYSTEM_PROMPT)

# %%
FAKE_REPORT = """# 白海豚北上减弱，灿鸿东北移出，对广东无直接影响

## 台风概况
- 白海豚（tsid 547）……
- 灿鸿（tsid 550）……

## 路径预报
两个台风的路径图资料缺失……

## 环境场与成因
……

## 活动概率与潜势
……

## 对广东和南海的影响
……

## 结论
……

## 资料说明
台风资料时次为北京时 8 月 11 日 08 时。"""

model = llm.agent_model(
    call("write_todos", todos=[{"content": "查询台风", "status": "in_progress"},
                               {"content": "路径、环境场、活动概率", "status": "pending"},
                               {"content": "写报告", "status": "pending"}]),
    call("get_typhoon_data_by_datetime", "c2", datetime="2026-08-11 08:00:00"),
    call("interpret_tc_track_forecast_chart", "c3", tsid="547", forecast_time="2026-08-11 08:00:00"),
    call("interpret_tc_track_forecast_chart", "c4", tsid="550", forecast_time="2026-08-11 08:00:00"),
    call("interpret_tc_env_chart", "c5"),
    call("interpret_tc_genesis_prob_chart", "c6"),
    FAKE_REPORT,
)
agent = ta.build_typhoon_agent(model)
r = agent.invoke({"messages": [{"role": "user", "content": "请分析北京时 2026 年 8 月 11 日 08 时的台风形势。"}]})
show(r, max_tool_chars=200)

# %%
print([c["name"] for c in tool_calls(r)])
ck.print_check(r)

# %% [markdown]
# 清单是通过的，但注意：**报告是剧本里写好的**，所以清单全过并不说明“智能体会写合格报告”。
#
# 这一节真正的用处是看结构：`write_todos` → 查询 → 取图 → 写报告，以及清单检查了哪些项。
# 配好 Key 之后回 `01_台风专题智能体_T7_T8.ipynb`，用三种个例各跑一次，那才是真的在检验提示词。
