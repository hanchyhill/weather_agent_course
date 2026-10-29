# %% [markdown]
# # L4 附：文本类工具（假模型剧本）
#
# 这个 notebook 是本讲两个正式 notebook 的**假模型剧本版**：
# 第 1 节对应 `01_读懂台风数据_T0.ipynb`（不调模型，内容与正式版一样），
# 第 2～4 节对应 `02_按世界时查询_T1.ipynb`（智能体部分用剧本）。
#
# 三点要说清：
#
# 1. 这里模型**不会思考**，只是照剧本念台词。剧本写在代码里（`llm.agent_model(...)` 的参数），不是模型自己想出来的。
# 2. 轨迹结构和真实模型一样，可以照着看懂“模型决定调工具 → 程序执行 → 结果交回模型”的循环。
# 3. 想知道模型会不会自己换算时区，必须回 `02_按世界时查询_T1.ipynb` 用真实模型。

# %%
import os

# 这一讲专门演假模型，强制打开（不依赖 .env 的设置）
os.environ["COURSE_FAKE_LLM"] = "1"

import json

from langchain.agents import create_agent
from langchain_core.tools import tool

from common import llm
from common.fake import call
from common.paths import DATA_DIR
from common.trace import show, tool_calls
from weather_tools import typhoon
from weather_tools.agent_tools import get_beijing_time

print("FAKE 模式" if llm.use_fake_llm() else "真实模型模式")

# %% [markdown]
# ## 1. 读懂台风数据（T0）
#
# 这一节不调模型，数据和代码与正式 notebook 一样。

# %%
raw = json.loads((DATA_DIR / "typhoon_api" / "sample_two_typhoons.json").read_text(encoding="utf-8"))
print(json.dumps({k: raw[k] for k in ("status", "tsid", "datetime")}, ensure_ascii=False))
print(json.dumps(raw["data"][0]["路径信息"][:2], ensure_ascii=False, indent=1))

# %%
print(typhoon.summarize(raw))

# %%
for item in raw["data"]:
    track = {p["预报时效"]: p for p in item["路径信息"]}
    p24 = track.get("24小时")
    print(item["台风信息"], "24 小时后：", p24 and f"{p24['纬度']}°N {p24['经度']}°E，{p24['中心风力']}")

# %% [markdown]
# ## 2. 工具：只收世界时（T1）
#
# 工具本身是真的：它会请求台风接口（仅内网可访问，连不上就返回一句错误说明）。假的是下面模型的选择。

# %%
import requests

from weather_tools.timeutil import convert_tz
from weather_tools.typhoon import data_endpoint
from common.weather_http import get as weather_get

# 真实接口地址由 data_endpoint() 提供（内网，不在讲义里明文给出）


@tool
def get_typhoon_data_utc(datetime: str) -> str:
    """按世界时（UTC）查询西北太平洋活动台风，返回 JSON。

    参数 datetime：世界时，格式 YYYY-MM-DD HH:MM:SS。
    """
    # 接口只认北京时，所以工具内部把世界时 +8 小时后再请求
    datetime_bj = convert_tz(datetime, "%Y-%m-%d %H:%M:%S", "UTC", "UTC+8")
    url = data_endpoint(datetime_bj)
    try:
        resp = weather_get(url, timeout=20)
        resp.raise_for_status()
        return json.dumps(resp.json(), ensure_ascii=False)
    except requests.exceptions.Timeout:
        return f"查询超时：世界时 {datetime}"
    except requests.exceptions.ConnectionError:
        return "无法连接到台风数据服务（需在内网环境）"
    except requests.exceptions.HTTPError as exc:
        return f"HTTP 错误（{exc.response.status_code}）"
    except ValueError as exc:
        return f"返回数据非有效 JSON：{exc}"


print(get_typhoon_data_utc.invoke({"datetime": "2026-08-11 00:00:00"})[:200])
print(get_typhoon_data_utc.invoke({"datetime": "2026-08-11 08:00:00"})[:200])

# %% [markdown]
# ## 3. 交给智能体
#
# **这是剧本**：剧本故意让模型“忘了换算”，把北京时 08 时直接当世界时传给工具，这也是学员最容易犯的错。

# %%
model = llm.agent_model(
    call("get_beijing_time"),
    call("get_typhoon_data_utc", "call_2", datetime="2026-08-11 08:00:00"),
    "目前西北太平洋没有活动台风。",
)
agent = create_agent(model=model, tools=[get_beijing_time, get_typhoon_data_utc],
                     system_prompt="你是广东省气象台的值班助手。用户说的时间都是北京时。")
r = agent.invoke({"messages": [{"role": "user", "content": "今天早上 8 点有没有台风？"}]})
show(r)

# %% [markdown]
# ## 4. 怎么发现结果错了
#
# 检查模型传给工具的时间：北京时 08 时应该传 `2026-08-11 00:00:00`。

# %%
for c in tool_calls(r):
    if c["name"] == "get_typhoon_data_utc":
        ok = c["args"]["datetime"] == "2026-08-11 00:00:00"
        print(c["args"], "换算正确" if ok else "换算错误：把北京时当成了世界时")

# %% [markdown]
# 剧本里 100% 会错，真实的换算正确率要靠真实模型多问几次统计。正式 notebook 第 4 节就是这个“真实情景”，配好 Key 之后回 `02_按世界时查询_T1.ipynb` 做。
#
# 练习：把剧本里 `datetime="2026-08-11 08:00:00"` 改成 `"2026-08-11 00:00:00"`，再跑一遍第 3～4 节，看“换算正确”那行怎么变——剧本是可以随便改的，模型不行。
