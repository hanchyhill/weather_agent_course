# %% [markdown]
# # L2 附：提示词基础（假模型剧本）
#
# 这个 notebook 是 `01_最高气温描述提示词.ipynb` 的**假模型剧本版**，专门给还没配好 Key 的学员熟悉流程。
#
# 三点要说清：
#
# 1. 这里模型**不会思考**，也不会真的看图，只是照剧本念台词。剧本写在代码里（`ask_image(..., fake_answer=...)` 的参数），不是模型自己想出来的。
# 2. 步骤顺序和正式 notebook 一样，可以照着看懂“看评分标准 → 写提示词 → 打分”的流程。
# 3. 想知道提示词对读图结果的真实影响，必须回 `01_最高气温描述提示词.ipynb` 用真实模型。

# %%
import os

# 这一讲专门演假模型，强制打开（不依赖 .env 的设置）
os.environ["COURSE_FAKE_LLM"] = "1"

import json

from IPython.display import Image, Markdown, display

from common import llm
from common.paths import DATA_DIR, OUTPUT_DIR
from lessons_import import load_lesson_module
from weather_tools.vision import ask_image

scoring = load_lesson_module("L02_提示词基础", "scoring")
D = DATA_DIR / "tmax_desc"
samples = json.loads((D / "gemini-3-flash.json").read_text(encoding="utf-8"))

print("FAKE 模式" if llm.use_fake_llm() else "真实模型模式")

# %% [markdown]
# ## 1. 好答案长什么样
#
# 这一节不调模型，图片和描述都是真实素材，和正式 notebook 完全一样。
# 第一张图人工打了 93 分。

# %%
first = samples[0]
display(Image(filename=str(D / "images" / first["image_path"]), width=600))
print(first["model_output"])

# %% [markdown]
# 评分标准共 9 项，权重合计 100。完整说明见 `data/tmax_desc/task4_评分指标.md`。

# %%
display(Markdown(scoring.score_sheet()))

# %%
print(scoring.total_score({1: 1, 2: 2, 3: 4.5, 4: 1, 5: 1, 6: 1, 7: 3, 8: 1, 9: 5}))

# %% [markdown]
# ## 2. 基线提示词
#
# **这是剧本**：下面这段“模型回答”是写死的，它并没有看过这张图。

# %%
BASELINE = "请描述图中广东最高气温的分布。"

img = D / "images" / samples[3]["image_path"]  # 2024-03-25，人工分只有 65，比较难
display(Image(filename=str(img), width=600))
baseline_out = ask_image(
    img, BASELINE,
    fake_answer="（剧本）图中显示广东最高气温分布不均：粤北气温较低，南部沿海和雷州半岛气温较高，"
                "全省最高气温出现在雷州半岛，约 34℃，其余地区多在 28～31℃。",
)
print(baseline_out)

# %% [markdown]
# ## 3. 改进提示词
#
# 提示词和正式 notebook 一模一样。方法：评分标准里的每一条，提示词里都要有一句对应的约束。
#
# **这也是剧本**：下面这段回答同样是写死的，而且剧本特意写得比基线规范，用来对比格式差异。
# 真实模型不一定能写得这么好，也不一定能读对数值。

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

improved_out = ask_image(
    img, IMPROVED,
    fake_answer="最高气温具体分布为：粤北、清远、肇庆市县介于25～28℃之间，"
                "湛江、茂名、阳江、珠海介于31～34℃之间，其余大部分市县介于28～31℃之间，"
                "其中徐闻录得全省最高气温34.1℃。",
)
print(improved_out)

# %% [markdown]
# ## 4. 对比打分
#
# 这一节不调模型。把两版输出和人工 65 分的 gemini 描述放在一起，按 9 项指标逐项打分。
#
# 注意：剧本版的分差是写剧本的人“设计”出来的，不能用来证明提示词有效。

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
# ## 5. 批量跑 6 张图
#
# **这是剧本**：6 张图都返回同一段话——这正好说明假模型不会看图，也不会按图读数。
#
# 结果另存成 `outputs/L02_improved_假模型剧本.json`，不覆盖真实模型跑出来的 `L02_improved.json`。

# %%
OUTPUT_DIR.mkdir(exist_ok=True)
batch = [{"image_path": s["image_path"],
          "model_output": ask_image(D / "images" / s["image_path"], IMPROVED,
                                    fake_answer="（剧本）最高气温具体分布为：粤北市县介于22～25℃之间，"
                                                "其余大部分市县介于25～28℃之间，"
                                                "其中徐闻录得全省最高气温29.8℃。")}
         for s in samples]
out = OUTPUT_DIR / "L02_improved_假模型剧本.json"
out.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
print("已保存", out)

# %% [markdown]
# 配好 Key 之后回 `01_最高气温描述提示词.ipynb`：真实模型会真的看图，它写出来的数、它犯的错，才是这一讲要体会的东西。
