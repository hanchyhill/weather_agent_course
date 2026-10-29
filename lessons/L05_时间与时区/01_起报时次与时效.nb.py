# %% [markdown]
# # L5-1 起报时次与时效
#
# 四个容易混的概念：
#
# | 概念 | 含义 | 例子 |
# |---|---|---|
# | 起报时间 | 模式从哪个时刻开始算，ECMWF 只有 00、12 UTC | 2025061400（北京时 6 月 14 日 08 时） |
# | 资料到达时间 | 产品什么时候能拿到，通常比起报晚几个小时 | 00 UTC 的资料北京时 7 点后才齐 |
# | 预报时效 | 从起报时间往后多少小时 | 30 小时 |
# | 有效时间 | 起报时间 + 时效，写稿时要换成北京时 | 6 月 15 日 14 时（北京时） |

# %%
# 改了 common/、weather_tools/ 里的代码后自动重新加载，不用重启内核
# %load_ext autoreload
# %autoreload 2

from datetime import datetime

from common.clock import BJ_TZ, now_bj
from weather_tools import timeutil

print("课程当前北京时：", now_bj())

# %% [markdown]
# ## 1. 换算小测
#
# 先在纸上算，再运行核对：北京时 2025-06-15 14 时，
#
# - 对应 2025061400 起报的哪个时效？
# - 对应 2025061312 起报的哪个时效？

# %%
print(timeutil.lead_time_for("2025061400", "2025-06-15 14:00"))
print(timeutil.lead_time_for("2025061312", "2025-06-15 14:00"))

# %% [markdown]
# ## 2. “现在该用哪个起报时次”
#
# 规则来自 agent_dev `src/tools/ToolBase.py:64-73`（北京时，只有 08、20 两个时次）：
#
# | 北京时 | 用哪个起报时次 | 对应 UTC |
# |---|---|---|
# | 06:00～13:59 | 当天 08 时 | 当天 00 |
# | 14:00～23:59 | 当天 20 时 | 当天 12 |
# | 00:00～05:59 | 前一天 20 时 | 前一天 12 |
#
# 这是“资料大约几点到”的业务经验，写成了代码。全项目只用这一套，不另立规则。

# %%
for s in ["2025-06-14 05:59", "2025-06-14 06:00", "2025-06-14 13:59", "2025-06-14 14:00", "2025-06-14 23:59"]:
    dt = datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=BJ_TZ)
    print(s, "→", timeutil.latest_init_time(dt))

# %% [markdown]
# ## 3. 一条规则，逐时过一遍
#
# 0～23 时全跑一遍，确认切换点只落在 06 时和 14 时两处；代码和上表对不上就是改坏了。

# %%
def rule_label(hour: int) -> str:
    """把 ToolBase 规则翻译成人话，用来和代码结果对照。"""
    if hour >= 14:
        return "当天20时"
    if hour >= 6:
        return "当天08时"
    return "前一天20时"


for h in range(24):
    dt = datetime(2025, 6, 14, h, 0, tzinfo=BJ_TZ)
    print(f"{h:02d} 时：{rule_label(h)} → {timeutil.latest_init_time(dt)} UTC")

# %% [markdown]
# 边界提早了，意味着 06:00 就假定当天 08 时次的资料已到。真遇到资料迟到，改的是这两个边界值，
# 不是另起一套规则——两三处各写一套，才是这类 bug 的根源。

# %% [markdown]
# ## 4. 常见隐患（读代码发现，未运行验证）
#
# - 不带时区的时间字符串被当成 UTC，再和北京时的“现在”比较，差 8 小时。
# - 用服务器本地时区取当前时间，换一台服务器结果就变。
# - 时效补零：`24` 要写成 `024`，否则拼出的图片地址不存在。
#
# 下面演示第一条。

# %%
naive = datetime.strptime("2025-09-01 08:00:00", "%Y-%m-%d %H:%M:%S")
print("不带时区：", naive, naive.tzinfo)
aware_bj = naive.replace(tzinfo=BJ_TZ)
from common.clock import UTC

print("当成北京时：", aware_bj, "= UTC", aware_bj.astimezone(UTC))
print("当成 UTC：  ", naive.replace(tzinfo=UTC), "= 北京时", naive.replace(tzinfo=UTC).astimezone(BJ_TZ))
