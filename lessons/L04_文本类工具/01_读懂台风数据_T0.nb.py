# %% [markdown]
# # L4-1 读懂台风数据（台风专线 T0）
#
# <!-- course-meta: real-llm -->
#
# 先不写工具，只看台风接口返回的原始 JSON。
# 数据是 huishang_demo 在 2026-08-11 08 时真实查询到的结果：两个活动台风。
#
# 这一格只读离线数据，不需要模型；本讲 T1 才要模型，`.env` 里要填好 `MAIN_API_KEY`。
# 没有 API Key 时先看同目录的 `99_假模型剧本.ipynb`：那里用预设剧本演示 T1 的同样流程。

# %%
# 改了 common/、weather_tools/ 里的代码后自动重新加载，不用重启内核
# %load_ext autoreload
# %autoreload 2

import json

from common.paths import DATA_DIR
from weather_tools.typhoon import summarize

raw = json.loads((DATA_DIR / "typhoon_api" / "sample_two_typhoons.json").read_text(encoding="utf-8"))
print(json.dumps({k: raw[k] for k in ("status", "tsid", "datetime")}, ensure_ascii=False))
print(json.dumps(raw["data"][0]["路径信息"][:2], ensure_ascii=False, indent=1))

# %% [markdown]
# ## 字段含义
#
# | 字段 | 含义 | 样例 |
# |---|---|---|
# | `tsid` | 台风业务编号，每个台风一个。后面取路径图要用它 | `[547, 550]` |
# | `datetime` | 每个台风的资料时次（北京时） | `2026-08-11 08:00:00` |
# | `台风信息` | 年份、编号、名称 | `2026年第13号台风白海豚` |
# | `预报时间` | 这份预报的发布时间 | `2026-08-11 02:00:00` |
# | `预报时效` | 从预报时间起算的小时数，0 小时就是当时的实况 | `0小时`、`24小时` |
# | `中心风力` / `中心最大风力` | 米/秒 | |
# | `移动方向` | 度，正北为 0，顺时针 | `315度` 是西北 |
#
# ## 练习
#
# 1. 用你的话说：白海豚这份预报是几点发布的？24 小时后它在哪里？
# 2. `datetime` 是 08 时，`预报时间` 却是 02 时，为什么不一样？
#    （提示：资料时次和预报发布时间是两回事。接口在 08 时能拿到的最新预报，可能是 02 时发布的。）
# 3. 让 Claude Code 把这段 JSON 翻译成一段台风简介，再和下面程序生成的简介对比。

# %%
print(summarize(raw))

# %%
for item in raw["data"]:
    track = {p["预报时效"]: p for p in item["路径信息"]}
    p24 = track.get("24小时")
    print(item["台风信息"], "24 小时后：", p24 and f"{p24['纬度']}°N {p24['经度']}°E，{p24['中心风力']}")
