# %% [markdown]
# # L10-2 评测：评分表、模型判官与人工一致性（台风专线 T10）
#
# <!-- course-meta: real-llm -->
#
# 三种评测方式：
#
# | 方式 | 适合 | 例子 |
# |---|---|---|
# | 规则评分 | 结构化结果 | L3 的计数和地市匹配 |
# | 人工评分 | 开放文本 | L2 的 9 项指标 |
# | 模型判官（LLM-as-judge） | 量大时代替部分人工 | 本节 |
#
# 判官本身也要验证：拿已有的人工打分对比，看一致性。
#
# 运行方式：在 VS Code 或 Jupyter 中逐格运行（Shift+Enter）。这一讲要用**真实模型**，
# `.env` 里的 `MAIN_API_KEY` 必须填好。
# 暂时没有 Key，就先看 `99_假模型剧本.ipynb`：那里用预设剧本演示同样的流程（判官全给满分）。

# %%
# 改了 common/、weather_tools/ 里的代码后自动重新加载，不用重启内核
# %load_ext autoreload
# %autoreload 2

import json

import pandas as pd

from common import llm
from common.paths import DATA_DIR
from lessons_import import load_lesson_module

scoring = load_lesson_module("L02_提示词基础", "scoring")
rubric = load_lesson_module("L10_人工把关与评测", "typhoon_rubric")

# %% [markdown]
# ## 1. 最高气温描述：判官 vs 人工
#
# sysu_vlm_test 有 30 条人工打分（本课程包带 6 条图片）。先看人工分。

# %%
human = pd.read_csv(DATA_DIR / "tmax_desc" / "scores_刘鑫杭_gemini-3-flash.csv", encoding="utf-8-sig")
samples = json.loads((DATA_DIR / "tmax_desc" / "gemini-3-flash.json").read_text(encoding="utf-8"))
names = [s["image_path"] for s in samples]
human = human[human["图片名称"].isin(names)].set_index("图片名称")
human[[f"指标{i}分数" for i in range(1, 10)] + ["总分"]]

# %% [markdown]
# 判官提示词：把 9 项指标的打分方法和真值一起给它。
# 改进方向（练习）：把站点真值和地理分区表也提供给判官，看指标 3、6 的一致性是否提升。

# %%
CRITERIA = (DATA_DIR / "tmax_desc" / "task4_评分指标.md").read_text(encoding="utf-8")


def judge_tmax(desc: str) -> dict[int, float]:
    prompt = f"""你是最高气温描述的评分员。按下面的评分指标给描述打分，输出 JSON：{{"1": 分, ..., "9": 分}}。

{CRITERIA}

## 待评描述
{desc}"""
    text = llm.ask(prompt)
    data = json.loads(text[text.find("{"): text.rfind("}") + 1])
    return {int(k): float(v) for k, v in data.items()}


rows = []
for s in samples:
    j = judge_tmax(s["model_output"])
    rows.append({"图片": s["image_path"], "判官总分": scoring.total_score(j), "人工总分": human.loc[s["image_path"], "总分"]})
cmp = pd.DataFrame(rows)
cmp["差"] = cmp["判官总分"] - cmp["人工总分"]
print(cmp)
print("平均绝对误差：", round(cmp["差"].abs().mean(), 1))

# %% [markdown]
# 注意：判官没看图，只看描述和评分标准，所以“数值准确性”“区间准确性”这类要对照真值的指标它很难判准。
# 这是练习的改进方向：把真值 CSV 一起交给判官。

# %% [markdown]
# ## 2. 台风报告评分表（T10）

# %%
for r in rubric.RUBRIC:
    print(r["id"], r["name"], "—", r["rule"])

# %% [markdown]
# 拿 L8 台风智能体的报告来打分。下面用一份示例报告演示判官流程。

# %%
from weather_tools import typhoon

data = json.dumps(typhoon.query_typhoon_with_lookback("2026-08-11 08:00:00"), ensure_ascii=False)[:3000]
REPORT = """# 白海豚北上减弱
## 台风概况
白海豚（tsid 547）位于……，强度为台风级。
## 活动概率与潜势
菲律宾以东概率高值区显示未来将有新台风生成。
## 结论
……"""

judge_text = llm.ask(rubric.judge_prompt(REPORT, data))
print(judge_text)
j = rubric.parse_judge(judge_text)
print("判官总分：", rubric.total(j))

# %% [markdown]
# 这份示例报告有两个明显问题：漏写了灿鸿（第 3 项），把活动概率说成生成新台风（第 4 项）。看判官能否查出来。
#
# ## 3. 练习
#
# 1. 用 L8 真实运行的 3 份台风报告，每人按评分表人工打分。
# 2. 让判官打分，计算每项的一致率。
# 3. 把扣分原因分成三类：改提示词能解决 / 要改工具 / 数据本身的问题。
# 4. 写出评分表里最难让判官自动判断的一项，并说明原因。
