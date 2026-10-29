# %% [markdown]
# # L6 附：假模型剧本（图像判读与 tsid 串联）
#
# 这一份把 `01_看图工具与判读提示词.ipynb`、`02_用tsid取路径图与诊断图_T5_T6.ipynb` 里需要模型的格子换成**剧本**，给还没配好 Key 的学员看流程。
#
# 三点要说清：
#
# 1. 这里模型和视觉模型**都不会思考**，只是照剧本念台词。台词写在代码里（`fake_answer=`、`llm.agent_model(...)` 的参数），不是模型看出来的。
# 2. 图片下载、时次回退、tsid 传递这些**程序部分是真的**，轨迹结构也和真实模型一样。
# 3. 想看视觉模型对着一张真图会怎么编、会不会瞎猜，必须回正式 notebook 用真实模型。

# %%
import os

# 这一份专门演假模型，强制打开（不依赖 .env 的设置）
os.environ["COURSE_FAKE_LLM"] = "1"

from IPython.display import Image, display
from langchain.agents import create_agent

from common import llm
from common.fake import call
from common.paths import DATA_DIR
from common.trace import show, tool_calls
from weather_tools import typhoon
from weather_tools.agent_tools import get_typhoon_data_by_datetime, interpret_tc_track_forecast_chart
from weather_tools.vision import ask_image

print("FAKE 模式" if llm.use_fake_llm() else "真实模型模式")

# %% [markdown]
# ## 1. 这是剧本：笼统提示词
#
# 原图照看，回答是 `fake_answer` 写好的。真模型下这一句往往很空泛，剧本册看不出差别。

# %%
img = DATA_DIR / "nwp" / "2025090208_024_rain24.png"
display(Image(filename=str(img), width=700))

# %%
DEFAULT = "请描述这张图。"
print(ask_image(img, DEFAULT, fake_answer="（FAKE）这是一张降水预报图。"))

# %% [markdown]
# ## 2. 这是剧本：写好的判读提示词
#
# 提示词本身是真的，换来的回答还是剧本。所以“提示词写好以后模型会多说哪些地市和量级”，这里看不到。

# %%
GOOD = """这是 4 个数值模式（左上 EC、右上 NCEP、左下 CMA-GD、右下 CMA-TRAMS）对同一时段 24 小时降水的预报对比图。
请按以下顺序回答：
1. 每个模式：广东主要雨带的位置和走向，50mm 以上落区涉及的地市，最大中心的位置和量级。
2. 四个模式的共同点。
3. 四个模式的主要分歧（落区偏东/偏西、量级偏大/偏小）。
只写图上能看到的内容，看不清的写“看不清”，不要猜测。"""
print(ask_image(img, GOOD, fake_answer="（FAKE）1. EC：……"))

# %% [markdown]
# ## 3. 先跑工具：查台风、拿 tsid（这一段是真的）

# %%
r = typhoon.query_typhoon_with_lookback("2024-09-03 08:00:00")
print(typhoon.summarize(r))
tsid = str(r["tsid"][0])

path, used, fb = typhoon.track_image_path(tsid, "2024-09-03 08:00:00")
print("路径图：", path.name, "实际时次", used, "（回退）" if fb else "")

# %% [markdown]
# ## 4. 这是剧本：交给智能体的 T5-3
#
# 剧本第一步查台风，第二步拿 tsid=736 取路径图，第三步写结论。程序照样真的去查、真的去取图，
# 只有“先查再取”的顺序是剧本写的——真实模型也可能顺序搞反，所以这一节不能当检查点的结论。

# %%
SYSTEM = """你是广东省气象台的台风值班助手。用户说的时间都是北京时。
取路径图前，必须先调用 get_typhoon_data_by_datetime 拿到 tsid。
返回多个台风时，每个台风都要给出结论。"""

model = llm.agent_model(
    call("get_typhoon_data_by_datetime", datetime="2024-09-03 08:00:00"),
    call("interpret_tc_track_forecast_chart", "call_2", tsid="736", forecast_time="2024-09-03 08:00:00"),
    "台风摩羯目前位于南海东北部，预计向西偏北移动，强度逐渐加强……",
)
agent = create_agent(model=model, system_prompt=SYSTEM,
                     tools=[get_typhoon_data_by_datetime, interpret_tc_track_forecast_chart])
res = agent.invoke({"messages": [{"role": "user", "content": "2024 年 9 月 3 日 08 时的台风路径怎么走？"}]})
show(res, max_tool_chars=300)

# %%
calls = tool_calls(res)
queried = [c for c in calls if c["name"] == "get_typhoon_data_by_datetime"]
track = [c for c in calls if c["name"] == "interpret_tc_track_forecast_chart"]
print("先查台风再取路径图：", bool(queried) and calls.index(queried[0]) < calls.index(track[0]))
print("tsid 来自查询结果：", all(c["args"]["tsid"] == tsid for c in track))

# %% [markdown]
# 这里两个 `True` 只说明**剧本**是按规矩写的，不说明模型会这么干。要判断模型会不会自己编 tsid，得用真实模型跑正式 notebook。

# %% [markdown]
# ## 5. 换视觉模型对比（剧本册没有这一节）
#
# `01_看图工具与判读提示词.ipynb` 第 4 节要拿同一张图问第二个视觉模型（`ALT_VLM_*`）再对照原图。
# 这件事只有真模型能做，剧本册不复制——没有 Key 时这一节跳过不影响后面。

# %% [markdown]
# 配好 Key 之后回 `01_看图工具与判读提示词.ipynb`、`02_用tsid取路径图与诊断图_T5_T6.ipynb`：
# 判读有没有编造、tsid 是不是编的，都要看模型的真实回答。
