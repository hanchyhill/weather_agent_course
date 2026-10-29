# %% [markdown]
# # L2 提示词基础：把业务规范写给模型
#
# <!-- course-meta: real-llm -->
#
# 任务：看 08～16 时最高气温图，写一段业务化的分布描述。
# 素材来自 `sysu_vlm_test`：6 张图、gemini-3-flash 的描述、人工按 9 项指标打的分。
#
# 本 notebook 的步骤：
#
# 1. 看“好答案”和评分标准
# 2. 基线提示词：只说一句话
# 3. 改进提示词：把评分标准逐条写成约束
# 4. 对比两版输出，用 9 项指标人工打分
#
# 这一讲要用**真实模型**，`.env` 里的 `VLM_API_KEY` 必须填好。
# 没有 API Key 时先看同目录的 `99_假模型剧本.ipynb`：那里用预设剧本演示同样的流程。

# %%
# 改了 common/、weather_tools/ 里的代码后自动重新加载，不用重启内核
# %load_ext autoreload
# %autoreload 2

import json

from IPython.display import Image, Markdown, display

from common.paths import DATA_DIR
from lessons_import import load_lesson_module
from weather_tools.vision import ask_image

scoring = load_lesson_module("L02_提示词基础", "scoring")
D = DATA_DIR / "tmax_desc"
samples = json.loads((D / "gemini-3-flash.json").read_text(encoding="utf-8"))
[s["image_path"] for s in samples]

# %% [markdown]
# ## 1. 好答案长什么样
#
# 第一张图人工打了 93 分。先看图，再看描述。

# %%
first = samples[0]
display(Image(filename=str(D / "images" / first["image_path"]), width=600))
print(first["model_output"])

# %% [markdown]
# 评分标准共 9 项，权重合计 100。完整说明见 `data/tmax_desc/task4_评分指标.md`。

# %%
display(Markdown(scoring.score_sheet()))

# %% [markdown]
# 核对：这条描述的人工分项得分代入公式，应得到 93 分。

# %%
print(scoring.total_score({1: 1, 2: 2, 3: 4.5, 4: 1, 5: 1, 6: 1, 7: 3, 8: 1, 9: 5}))

# %% [markdown]
# ## 2. 基线提示词

# %%
BASELINE = "请描述图中广东最高气温的分布。"

img = D / "images" / samples[3]["image_path"]  # 2024-03-25，人工分只有 65，比较难
display(Image(filename=str(img), width=600))
baseline_out = ask_image(img, BASELINE)
print(baseline_out)

# %% [markdown]
# ## 3. 改进提示词
#
# 方法：评分标准里的每一条，提示词里都要有一句对应的约束。
# 下面是一版参考。请先自己写，再对照。
#
# | 评分指标 | 提示词里对应的约束 |
# |---|---|
# | 1、2 最高气温数值与位置 | 末尾写“其中××（地市+区县）录得全省最高气温××.×℃”，数值照图上读，保留一位小数 |
# | 3 温度区间准确 | 区间上下限要包住该区域的实际读数 |
# | 4、5 不重叠 | 不同区域的温度区间不能交叉；地理范围不能互相包含 |
# | 6 完整 | 用“其余大部分市县”兜底，保证所有区域都被描述 |
# | 7 聚类合理 | 每个区间跨度 2～4℃；同区间的区域合并；优先用大区名；类别尽量少 |
# | 8 顺序 | 先写特例和小范围，最后写普遍区域 |
# | 9 用语 | 用“××市县介于X～Y℃之间”；写“气温”不写“温度”；不加“注意防暑”等服务用语 |

# %%
GEO_HINT = """广东分区参考：
- 粤北：韶关、清远、河源、梅州北部
- 粤东：汕头、潮州、揭阳、汕尾
- 粤西：湛江、茂名、阳江、云浮
- 珠三角：广州、深圳、佛山、东莞、中山、珠海、江门、肇庆、惠州"""

IMPROVED = f"""你是广东省气象台的预报员，请根据图中 08～16 时最高气温分布，写一段业务化描述。

要求：
1. 开头固定写“最高气温具体分布为：”。
2. 按温度把区域分成 2～4 类，每类温度区间跨度 2～4℃。温度相同的区域合并写，优先用粤北、粤东、粤西、珠三角等大区名，不再逐个列出市县。
3. 先写特例或范围较小的区域，最后用“其余大部分市县”概括普遍区域，保证全省都被描述到。
4. 不同区域的温度区间不能交叉，地理范围不能互相包含。
5. 每类的句式为“××市县介于X～Y℃之间”。
6. 末尾写“其中××（地市+区县）录得全省最高气温××.×℃。”，数值以图上读数为准，保留一位小数。
7. 用“气温”，不用“温度”；不要写“天气炎热”“注意防暑”“总之”等多余的话。
8. 只输出这一段描述，不要输出分析过程。

{GEO_HINT}

示例（另一天的高分描述，仅供参考格式）：
{samples[0]["model_output"]}"""

improved_out = ask_image(img, IMPROVED)
print(improved_out)

# %% [markdown]
# ## 4. 对比打分
#
# 把两版输出和人工 65 分的 gemini 描述放在一起，按 9 项指标逐项打分（两人一组交换打）。
# 把分项分填进下面的字典，计算总分。

# %%
print("gemini 原描述（人工 65 分）：", samples[3]["model_output"])
print("基线：", baseline_out)
print("改进：", improved_out)

# %%
my_baseline_scores = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0}   # ← 填你的打分
my_improved_scores = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0}
print("基线总分", scoring.total_score(my_baseline_scores))
print("改进总分", scoring.total_score(my_improved_scores))

# %% [markdown]
# ## 5. 批量跑 6 张图（可选）
#
# 把结果存成 sysu_vlm_test 打分界面能导入的格式（`[{image_path, model_output}]`），
# 讲师可以导入界面，让全班用同一套界面打分。

# %%
from common.paths import OUTPUT_DIR

OUTPUT_DIR.mkdir(exist_ok=True)
batch = [{"image_path": s["image_path"],
          "model_output": ask_image(D / "images" / s["image_path"], IMPROVED)}
         for s in samples]
out = OUTPUT_DIR / "L02_improved.json"
out.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
print("已保存", out)
