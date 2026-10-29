# %% [markdown]
# # L4-2 按世界时查询台风（台风专线 T1）
#
# <!-- course-meta: real-llm -->
#
# 这一步还原 huishang_demo 早期的做法：台风查询工具**只接受世界时**。
# 用户却总是用北京时提问。看看让模型自己减 8 小时会出什么问题。
#
# 工具调用的是真实的台风数据接口（getyphdata，仅内网可访问），接口本身只认北京时。
# 这一讲要用**真实模型**，`.env` 里的 `MAIN_API_KEY` 必须填好。
# 没有 API Key 时先看同目录的 `99_假模型剧本.ipynb`：那里用预设剧本演示同样的流程。

# %%
# 改了 common/、weather_tools/ 里的代码后自动重新加载，不用重启内核
# %load_ext autoreload
# %autoreload 2

import json

from langchain.agents import create_agent
from langchain_core.tools import tool

from common import llm
from common.trace import show, tool_calls
from weather_tools.agent_tools import get_beijing_time

# %% [markdown]
# ## 1. 工具：只收世界时
#
# 下面是参考写法。注意 docstring 写了“世界时”，但模型会不会照做？


# %%
import requests

from weather_tools.timeutil import convert_tz
from weather_tools.typhoon import data_endpoint

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
        resp = requests.get(url, timeout=20)
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
# 同一天，传 00 时（世界时）查的是北京时 08 时；把北京时 08 时直接当世界时传进去，查的其实是北京时 16 时，两次返回的台风资料会不一样（时次不对，可能为空）。

# %% [markdown]
# ## 2. 交给智能体
#
# 真实模型下请多问几次，统计换算对了几次。没有 API Key 时先看同目录的 `99_假模型剧本.ipynb`：那里用预设剧本（故意让模型“忘了换算”，演示常见错误）演示同样的流程。

# %%
model = llm.main_llm()
agent = create_agent(model=model, tools=[get_beijing_time, get_typhoon_data_utc],
                     system_prompt="你是广东省气象台的值班助手。用户说的时间都是北京时。")
r = agent.invoke({"messages": [{"role": "user", "content": "今天早上 8 点有没有台风？"}]})
show(r)

# %% [markdown]
# ## 3. 怎么发现结果错了
#
# 检查模型传给工具的时间：北京时 08 时应该传 `2026-08-11 00:00:00`。

# %%
for c in tool_calls(r):
    if c["name"] == "get_typhoon_data_utc":
        ok = c["args"]["datetime"] == "2026-08-11 00:00:00"
        print(c["args"], "换算正确" if ok else "换算错误：把北京时当成了世界时")

# %% [markdown]
# ## 4. 真实情景：真模型 + 真时钟 + 真接口
#
# 这一节不用任何预设：模型自己决定调哪个工具、传什么时间，
# 工具真的请求台风接口。需要 `.env` 填好 Key，并在内网环境运行。
#
# 判断标准：用户说的是北京时，模型传给工具的世界时应当等于「当前北京时 − 8 小时」。

# %%
from datetime import datetime

from weather_tools.agent_tools import now_bj
from weather_tools.timeutil import convert_tz

real_agent = create_agent(
    model=llm.main_llm(),
    tools=[get_beijing_time, get_typhoon_data_utc],
    system_prompt="你是广东省气象台的值班助手。用户说的时间都是北京时。",
)
real_r = real_agent.invoke({"messages": [{"role": "user", "content": "现在西北太平洋有没有活动台风？"}]})
show(real_r)

# 用真实时钟算出“应当传入的世界时”，与模型实际传入的对比（允许相差 1 小时内）
expect = convert_tz(now_bj().strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S", "UTC+8", "UTC")
for c in tool_calls(real_r):
    if c["name"] == "get_typhoon_data_utc":
        got = c["args"]["datetime"]
        diff = abs((datetime.strptime(got, "%Y-%m-%d %H:%M:%S")
                    - datetime.strptime(expect, "%Y-%m-%d %H:%M:%S")).total_seconds()) / 3600
        print(f"模型传入 {got}，应传约 {expect}，相差 {diff:.1f} 小时",
              "→ 换算正确" if diff <= 1 else "→ 换算错误：很可能没减 8 小时")

# %% [markdown]
# ## 5. 练习
#
# 1. 真实模型下把同一个问题问 5 次，记录换算正确几次。
# 2. 在系统提示词里加一句“调用台风工具前，先把北京时减 8 小时”，再问 5 次。
# 3. 讨论：靠提示词提醒模型做减法，可靠吗？还有什么更好的办法？（答案在 L5 的 T2。）
