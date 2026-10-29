# %% [markdown]
# # L6-1 图像类工具与判读提示词
#
# <!-- course-meta: real-llm -->
#
# 图像工具有两种做法：
#
# 1. **只拼地址**：按命名规则拼出图片 URL，直接给人看（agent_dev 的 `rainFore`）。
# 2. **交给视觉模型判读**：下载图片 → 缩放 → base64 → 视觉模型 → 返回文字（huishang_demo 的 `interpret_*`）。
#
# huishang_demo 采用“双模型”：主模型只规划和写稿，不直接看图；图像工具内部调用视觉模型。
#
# 判读部分要用**真实视觉模型**，`.env` 里的 `VLM_API_KEY` 必须填好。
# 暂时没有 Key，就先看同目录的 `99_假模型剧本.ipynb`：那里用预设剧本演示同样的流程。

# %%
# 改了 common/、weather_tools/ 里的代码后自动重新加载，不用重启内核
# %load_ext autoreload
# %autoreload 2

from IPython.display import Image, display

from common.paths import DATA_DIR
from weather_tools.vision import ask_image

# %% [markdown]
# ## 1. 只拼地址
#
# agent_dev 的逐日雨量预报图地址规则（`src/tools/ToolDecision.py` 的 `rainFore`）：
#
# ```
# {base}/prroaweb/filelist/hs/{year}/{date}/hs_fore_day_rain_10d_daily_08_{date}_{leadtime}.png
# ```
#
# 时效要补零成 3 位：`024`、`048`。


# %%
def rain_fore_url(base: str, date: str, day: int) -> str:
    lead = str(day * 24).zfill(3)
    return f"{base}/prroaweb/filelist/hs/{date[:4]}/{date}/hs_fore_day_rain_10d_daily_08_{date}_{lead}.png"


for d in (1, 2, 3):
    print(rain_fore_url("{BASE_URL_DECISION}", "20250614", d))

# %% [markdown]
# 练习：时效如果忘了补零，会拼出什么？为什么图片会打不开？

# %% [markdown]
# ## 2. 交给视觉模型
#
# 用 agent_dev `static/img` 里的数值模式四宫格样例（EC、NCEP、CMA-GD、CMA-TRAMS 的 24 小时降水）。

# %%
img = DATA_DIR / "nwp" / "2025090208_024_rain24.png"
display(Image(filename=str(img), width=700))

# %%
DEFAULT = "请描述这张图。"
print(ask_image(img, DEFAULT))

# %% [markdown]
# ## 3. 写一版好的判读提示词
#
# 默认提示词太笼统。用 L2、L3 学到的方法：说清图是什么、按什么顺序描述、要什么量化信息、不要什么。

# %%
GOOD = """这是 4 个数值模式（左上 EC、右上 NCEP、左下 CMA-GD、右下 CMA-TRAMS）对同一时段 24 小时降水的预报对比图。
请按以下顺序回答：
1. 每个模式：广东主要雨带的位置和走向，50mm 以上落区涉及的地市，最大中心的位置和量级。
2. 四个模式的共同点。
3. 四个模式的主要分歧（落区偏东/偏西、量级偏大/偏小）。
只写图上能看到的内容，看不清的写“看不清”，不要猜测。"""
print(ask_image(img, GOOD))

# %% [markdown]
# ## 4. 模型对比
#
# 同一个提示词，换一个视觉模型（`.env` 的 `ALT_VLM_*`，如 Agnes）再判读一次，对照原图看谁更准。

# %%
import os

if os.getenv("ALT_VLM_API_KEY"):
    print(ask_image(img, GOOD, alt=True))
else:
    print("未配置 ALT_VLM_API_KEY，跳过")
