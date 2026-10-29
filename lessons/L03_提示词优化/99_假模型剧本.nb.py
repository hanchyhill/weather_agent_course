# %% [markdown]
# # L3 附：提示词优化 A/B 实验（假模型剧本）
#
# 这个 notebook 是 `01_提示词AB实验.ipynb` 的**假模型剧本版**，专门给还没配好 Key 的学员熟悉流程。
#
# 三点要说清：
#
# 1. 这里模型**不会思考**，也不会真的看图，只是照剧本念台词。剧本写在代码里（`ask_image(..., fake_answer=...)` 的参数），不是模型自己想出来的。
# 2. 步骤顺序和正式 notebook 一样，可以照着看懂“错题 → 两版提示词 → 跑实验 → 打分 → 写报告”的流程。
# 3. 这里的分数**没有意义**：v1 用的是 gpt-4o 的历史回答，v2 直接抄真值，都是为了让流程跑通。想比较两版提示词的真实效果，必须回 `01_提示词AB实验.ipynb` 用真实模型。

# %%
import os

# 这一讲专门演假模型，强制打开（不依赖 .env 的设置）
os.environ["COURSE_FAKE_LLM"] = "1"

import json
from pathlib import Path

from IPython.display import Image, display

from common import llm
from common.paths import DATA_DIR, OUTPUT_DIR
from lessons_import import load_lesson_module
from weather_tools.vision import ask_image

t = load_lesson_module("L03_提示词优化", "tmax_task")
HERE = Path(t.__file__).parent

print("FAKE 模式" if llm.use_fake_llm() else "真实模型模式")

# %% [markdown]
# ## 1. 看错题
#
# 这一节不调模型，图片、真值和 gpt-4o 的历史回答都是真实素材。

# %%
demo = json.loads((DATA_DIR / "tmax" / "demo_gpt4o_task5.json").read_text(encoding="utf-8"))
display(Image(filename=str(t.image("2024010120")), width=600))
print("真值：", t.truth("2024010120"))

# %%
print(demo["llm_result"][-1200:])
print(t.score("2024010120", demo["llm_result"]))

# %% [markdown]
# 错在哪？
#
# - 把等于 27.0 的（阳春、恩平）也算了进去：“高于”理解成了“高于或等于”。
# - 把 26.x 的县也列进来了，而且列表里明明写着 26.9，却还说它“高于 27”。
# - 自己数的 Count 和列表长度对不上的问题这里没出现，但很常见。
#
# 这些都是**提示词能管住的**：拆步骤、明确“严格大于”、最后自检。
#
# 也有提示词管不住的：如果模型把 26.6 读成了 27.6，那是读图能力问题。

# %% [markdown]
# ## 2. 两版提示词
#
# 这一节不调模型，两版提示词就是正式 notebook 用的那两份文件。

# %%
V1 = (HERE / "prompts" / "v1_基线.txt").read_text(encoding="utf-8")
V2 = (HERE / "prompts" / "v2_拆步骤.txt").read_text(encoding="utf-8")
print(V2[:600])

# %% [markdown]
# ## 3. 跑实验
#
# **这是剧本**：v1 每次调用都返回 gpt-4o 的那条历史回答，v2 每次调用都返回真值。
# 6 次“调用”一次模型都没发生，图也没看。

# %%
FAKE_V1 = demo["llm_result"]  # 剧本：用 gpt-4o 的真实回答代替 v1 的输出


def run(version: str, template: str) -> list[dict]:
    rows = []
    for day in t.DAYS:
        tr = t.truth(day)
        prompt = template.format(threshold=tr["threshold"], geo_table=t.geo_table())
        fake = FAKE_V1 if version == "v1" else (
            '```json\n' + json.dumps({"Count": tr["Count"], "Stations": tr["Stations"]}, ensure_ascii=False) + '\n```')
        answer = ask_image(t.image(day), prompt, fake_answer=fake)
        rows.append({"version": version, **t.score(day, answer), "answer": answer})
    return rows


results = run("v1", V1) + run("v2", V2)
for r in results:
    print(r["version"], r["day"], "得分", r["final"], f"计数 {r['count_pred']}/{r['count_true']}")

# %%
import pandas as pd

df = pd.DataFrame(results).drop(columns="answer")
summary = df.groupby("version")["final"].mean().round(1)
print(summary)

OUTPUT_DIR.mkdir(exist_ok=True)
(OUTPUT_DIR / "L03_ab_results_假模型剧本.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

# %% [markdown]
# 所以上面的平均分不能用：v2 满分是因为它抄了真值，v1 低分是因为剧本抄了一条错题。
#
# ## 4. 写 A/B 报告（剧本版只能练格式）
#
# | 项目 | 内容 |
# |---|---|
# | 改了什么 | |
# | 为什么这么改 | |
# | v1 平均分 → v2 平均分 | 剧本版的分数没有意义，配好 Key 之后填真实的 |
# | 还有哪些失分改不了，原因 | |
#
# ## 5. 进阶：自己写 v3
#
# 复制 `prompts/v2_拆步骤.txt` 为 `v3_xxx.txt`，试试：
#
# - 先列全省所有读数，再过滤（更慢，但漏得少？）
# - 去掉地理对照表，看地理分会不会掉
# - 要求“读不清的数字标 ?，不要猜”
#
# 这三条都要真实模型才看得出差别，回 `01_提示词AB实验.ipynb` 做。
