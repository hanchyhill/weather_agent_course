# %% [markdown]
# # L3 提示词优化：用分数说话
#
# <!-- course-meta: real-llm -->
#
# 任务（mllm_test tmax task5）：统计最高气温**高于**阈值的区县数量，并列出名单。
# 阈值取全省最高值向下取整。评分：计数 60% + 地理 40%，满分 100。
#
# 先看一个真实错题：gpt-4o 在 2024-01-01 这张图上数出了 25 个县，真值只有 2 个，得 40 分。
# 然后做一次 A/B 实验：v1 基线提示词 vs v2 拆步骤提示词。
#
# 这一讲要用**真实模型**，`.env` 里的 `VLM_API_KEY` 必须填好。
# 没有 API Key 时先看同目录的 `99_假模型剧本.ipynb`：那里用预设剧本演示同样的流程。

# %%
# 改了 common/、weather_tools/ 里的代码后自动重新加载，不用重启内核
# %load_ext autoreload
# %autoreload 2

import json
from pathlib import Path

from IPython.display import Image, display

from common.paths import DATA_DIR, OUTPUT_DIR
from lessons_import import load_lesson_module
from weather_tools.vision import ask_image

t = load_lesson_module("L03_提示词优化", "tmax_task")
HERE = Path(t.__file__).parent

# %% [markdown]
# ## 1. 看错题

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

# %%
V1 = (HERE / "prompts" / "v1_基线.txt").read_text(encoding="utf-8")
V2 = (HERE / "prompts" / "v2_拆步骤.txt").read_text(encoding="utf-8")
print(V2[:600])

# %% [markdown]
# ## 3. 跑实验
#
# 控制变量：同一个模型、同样的图、同样的温度参数，只换提示词。
# 3 张图 × 2 版提示词 = 6 次调用。

# %%
def run(version: str, template: str) -> list[dict]:
    rows = []
    for day in t.DAYS:
        tr = t.truth(day)
        prompt = template.format(threshold=tr["threshold"], geo_table=t.geo_table())
        answer = ask_image(t.image(day), prompt)
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
(OUTPUT_DIR / "L03_ab_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

# %% [markdown]
# 模型的输出每次都不一样，多跑几次看平均分和波动。没有 API Key 时先看同目录的 `99_假模型剧本.ipynb`：那里用预设剧本演示同样的流程。
#
# ## 4. 写 A/B 报告
#
# | 项目 | 内容 |
# |---|---|
# | 改了什么 | |
# | 为什么这么改 | |
# | v1 平均分 → v2 平均分 | |
# | 还有哪些失分改不了，原因 | |
#
# ## 5. 进阶：自己写 v3
#
# 复制 `prompts/v2_拆步骤.txt` 为 `v3_xxx.txt`，试试：
#
# - 先列全省所有读数，再过滤（更慢，但漏得少？）
# - 去掉地理对照表，看地理分会不会掉
# - 要求“读不清的数字标 ?，不要猜”
