# %% [markdown]
# # L10 附：假模型剧本（人工确认保存 + 判官评测）
#
# 这个 notebook 是 L10 两个正式 notebook 的**剧本版**，专门给还没配好 Key 的学员熟悉流程：
#
# - 第 1～2 节对应 `01_人工确认保存_HITL.ipynb`
# - 第 3～4 节对应 `02_判官与人工一致性_T10.ipynb`
#
# 三点要说清：
#
# 1. 这里模型**不会思考**，只是照剧本念台词。剧本写在代码里（`llm.agent_model(...)`、`fake_answer=...`）。
# 2. 暂停、批准、修改、拒绝、文件读写、清单检查都是真的，与模型真假无关，可以照看流程。
# 3. 判官给的分、会商意见都是写死的。想体会真实行为（尤其是拒绝之后模型怎么说、判官判得准不准），
#    请回对应的正式 notebook。

# %%
import os

# 这一讲专门演假模型，强制打开（不依赖 .env 的设置）
os.environ["COURSE_FAKE_LLM"] = "1"

import json
import uuid

import pandas as pd
from deepagents import create_deep_agent
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from common import llm
from common.fake import call
from common.paths import DATA_DIR, OUTPUT_DIR
from common.trace import show
from lessons_import import load_lesson_module

scoring = load_lesson_module("L02_提示词基础", "scoring")
rubric = load_lesson_module("L10_人工把关与评测", "typhoon_rubric")

print("FAKE 模式" if llm.use_fake_llm() else "真实模型模式")

# %% [markdown]
# # 第一部分：人工确认保存（L10-1）

# %%
@tool
def save_report(title: str, content: str) -> str:
    """把会商稿保存为 Markdown 文件。保存前需人工确认。"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{title}.md"
    path.write_text(content, encoding="utf-8")
    return f"已保存到 {path.name}"


def build(model):
    return create_deep_agent(
        model=model,
        tools=[save_report],
        system_prompt="你是会商助手。写好会商稿后调用 save_report 保存。用户拒绝保存时，如实告知未保存。",
        interrupt_on={"save_report": {"allowed_decisions": ["approve", "edit", "reject"]}},
        checkpointer=InMemorySaver(),
    )


DRAFT = "# 早间会商\n过去 24 小时无活动台风……"

# %% [markdown]
# ## 1. 暂停：智能体要保存，先停下来等人
#
# **这是剧本**：模型第一步就要求调用 `save_report`。真实模型会先写稿，再决定要不要保存。

# %%
agent = build(llm.agent_model(call("save_report", title="早间会商", content=DRAFT), "会商稿已保存。"))
cfg = {"configurable": {"thread_id": str(uuid.uuid4())}}
r = agent.invoke({"messages": [{"role": "user", "content": "把这份会商稿保存下来：" + DRAFT}]}, config=cfg)

req = r["__interrupt__"][0].value["action_requests"][0]
print("待确认的操作：", req["name"])
print("参数：", req["args"])

# %% [markdown]
# ## 2. 三种处理
#
# | 决定 | 写法 | 效果 |
# |---|---|---|
# | 批准 | `{"type": "approve"}` | 按原参数执行 |
# | 修改 | `{"type": "edit", "edited_action": {"name": ..., "args": {...}}}` | 按修改后的参数执行 |
# | 拒绝 | `{"type": "reject", "message": "原因"}` | 不执行，把原因告诉智能体 |
#
# 改下面的 `decision` 试三种情况。三种都由程序处理，和模型真假无关，所以这一节在剧本版里照样有意义。

# %%
decision = {"type": "edit", "edited_action": {
    "name": "save_report", "args": {"title": "早间会商_已审核", "content": DRAFT + "\n\n（值班首席已审核）"}}}
# decision = {"type": "approve"}
# decision = {"type": "reject", "message": "台风资料时次不对，先不要保存"}

r2 = agent.invoke(Command(resume={"decisions": [decision]}), config=cfg)
show(r2, max_tool_chars=200)

# %% [markdown]
# 把 `decision` 换成 `reject` 再跑一遍：文件不会生成，但**剧本里的模型仍然说“已保存”**。
# 这就是为什么不能只看模型说了什么，要看工具实际做了什么。

# %%
print(sorted(p.name for p in OUTPUT_DIR.glob("早间会商*.md")))

# %% [markdown]
# # 第二部分：判官评测（L10-2）

# %% [markdown]
# ## 3. 最高气温描述：判官 vs 人工
#
# 人工分和图片都是真的；**判官的分是剧本**——全部给满分，所以下面的平均绝对误差没有意义，只用来跑通流程。
# 真实判官请用 `02_判官与人工一致性_T10.ipynb`。

# %%
human = pd.read_csv(DATA_DIR / "tmax_desc" / "scores_刘鑫杭_gemini-3-flash.csv", encoding="utf-8-sig")
samples = json.loads((DATA_DIR / "tmax_desc" / "gemini-3-flash.json").read_text(encoding="utf-8"))
names = [s["image_path"] for s in samples]
human = human[human["图片名称"].isin(names)].set_index("图片名称")
human[[f"指标{i}分数" for i in range(1, 10)] + ["总分"]]

# %%
CRITERIA = (DATA_DIR / "tmax_desc" / "task4_评分指标.md").read_text(encoding="utf-8")


def judge_tmax(desc: str) -> dict[int, float]:
    prompt = f"""你是最高气温描述的评分员。按下面的评分指标给描述打分，输出 JSON：{{"1": 分, ..., "9": 分}}。

{CRITERIA}

## 待评描述
{desc}"""
    fake = json.dumps({str(m["id"]): m["max"] for m in scoring.METRICS}, ensure_ascii=False)
    text = llm.ask(prompt, fake_answer=fake)  # 剧本：全给满分
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
# ## 4. 台风报告评分表（T10）
#
# **这也是剧本**：判官分是写死的，模拟“查出漏写灿鸿、把活动概率说成生成概率”这一档。

# %%
for r_ in rubric.RUBRIC:
    print(r_["id"], r_["name"], "—", r_["rule"])

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

FAKE_JUDGE = '```json\n{"scores": {"1": 1, "2": 1, "3": 0, "4": 0, "5": 1, "6": 1}, "reasons": {}}\n```'
judge_text = llm.ask(rubric.judge_prompt(REPORT, data), fake_answer=FAKE_JUDGE)
print(judge_text)
j = rubric.parse_judge(judge_text)
print("判官总分：", rubric.total(j))

# %% [markdown]
# 这份示例报告有两个明显问题：漏写了灿鸿（第 3 项），把活动概率说成生成新台风（第 4 项）。
# 剧本里的判官“正好”扣了这两项——真实判官会不会这么判，要回 `02_判官与人工一致性_T10.ipynb` 验证。
