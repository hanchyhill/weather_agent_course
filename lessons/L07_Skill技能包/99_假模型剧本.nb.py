# %% [markdown]
# # L7 附：假模型剧本（Skill 会不会被读到）
#
# 这一份是 `01_用Skill沉淀经验.ipynb` 第 2、3 节的**剧本版**，给还没配好 Key 的学员看流程。
#
# 三点要说清：
#
# 1. 这里模型**不会思考**，只是照剧本念台词。剧本写在代码里（`llm.agent_model(...)` 的参数），不是模型自己决定去读 Skill。
# 2. Skill 列表注入、`read_file` 真的读了哪个文件、轨迹结构，这些都是真的；只有“读不读”的决策是剧本写死的。
# 3. 想知道模型的 description 写得够不够清楚、它会不会主动读，必须回 `01_用Skill沉淀经验.ipynb` 用真实模型。

# %%
import os

# 这一份专门演假模型，强制打开（不依赖 .env 的设置）
os.environ["COURSE_FAKE_LLM"] = "1"

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

from common import llm
from common.fake import call
from common.paths import COURSE_ROOT, SKILLS_DIR
from common.trace import show, tool_calls

print("FAKE 模式" if llm.use_fake_llm() else "真实模型模式")

# %% [markdown]
# ## 0. 先看技能包名片（这一段是真的）
#
# deepagents 会把每个 Skill 的名字、description、路径写进系统提示词，模型只凭名片决定要不要读全文。

# %%
for d in sorted(SKILLS_DIR.iterdir()):
    print(d.name, "→", (d / "SKILL.md").read_text(encoding="utf-8").splitlines()[2][:80])

# %%
def build_agent(model, skills=True):
    return create_deep_agent(
        model=model,
        system_prompt="你是广东省气象台的预报助手，用中文回答。",
        skills=["/skills/"] if skills else None,
        backend=FilesystemBackend(root_dir=str(COURSE_ROOT), virtual_mode=True),
    )


# %% [markdown]
# ## 1. 这是剧本：问风速等级，先去读台风等级 Skill
#
# 剧本第一步 `read_file` 读 `typhoon-grade/SKILL.md`，第二步按里面的标准回答。
# 注意：**“想到要去读”这一步是剧本写的**，所以这里看不出模型会不会真的去读。

# %%
model = llm.agent_model(
    call("read_file", file_path="/skills/typhoon-grade/SKILL.md"),
    "中心附近最大平均风速 23 米/秒属于热带风暴（TS），9 级。",
)
r = build_agent(model).invoke({"messages": [{"role": "user", "content": "台风中心最大风速 23 米/秒，阵风 28 米/秒，是什么等级？"}]})
show(r, max_tool_chars=200)
print("读取了哪些文件：", [c["args"].get("file_path") for c in tool_calls(r) if c["name"] == "read_file"])

# %% [markdown]
# 真模型下这一节要盯两点：有没有读 `typhoon-grade/SKILL.md`；用的是平均风 23 还是阵风 28（23 是热带风暴，28 会被判成强热带风暴）。

# %% [markdown]
# ## 2. 这是剧本：无关问题不该触发 Skill
#
# 问“现在几点”，剧本里模型直接说不知道，不读任何文件。

# %%
model = llm.agent_model("抱歉，我没有获取时间的工具。")
r = build_agent(model).invoke({"messages": [{"role": "user", "content": "现在几点？"}]})
print("读取的文件：", [c["args"].get("file_path") for c in tool_calls(r) if c["name"] == "read_file"])

# %% [markdown]
# 剧本册里这一格永远是空的，因为剧本没写读取动作。要说“无关问题不触发 Skill”，得在正式 notebook 里用真实模型验证。

# %% [markdown]
# ## 3. 自己写 Skill 的练习（剧本册不复制）
#
# `01_用Skill沉淀经验.ipynb` 第 4 节要你写 `skills/<英文名>/SKILL.md`，再用真模型试它该不该被触发。
# 这件事离不开真实模型，剧本册没法替你做。写完 Skill 回正式 notebook 第 2 节验证。
