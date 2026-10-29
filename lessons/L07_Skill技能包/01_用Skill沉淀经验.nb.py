# %% [markdown]
# # L7 Skill：把预报经验做成技能包
#
# <!-- course-meta: real-llm -->
#
# 从这一讲开始，智能体换成 deepagents 的 `create_deep_agent`。
#
# Skill 和系统提示词的区别：
#
# | | 系统提示词 | Skill |
# |---|---|---|
# | 加载时机 | 每次都全文加载 | 平时只露出名字和简介，用到时才读全文 |
# | 适合放 | 角色、通用规则 | 某个专题的规范、步骤、参考表 |
# | 维护 | 一大段，改一处牵一片 | 一个专题一个文件夹，各管各的 |
#
# 课程包的 `skills/` 下已有两个示例：`tmax-description`（最高气温描述规范）、`typhoon-grade`（台风等级标准）。
#
# 这一讲要用**真实模型**，`.env` 里的 `MAIN_API_KEY` 必须填好（Skill 会不会被读，取决于模型自己的判断）。
# 暂时没有 Key，就先看同目录的 `99_假模型剧本.ipynb`：那里用预设剧本演示同样的流程。

# %%
# 改了 common/、weather_tools/ 里的代码后自动重新加载，不用重启内核
# %load_ext autoreload
# %autoreload 2

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

from common import llm
from common.paths import COURSE_ROOT, SKILLS_DIR
from common.trace import show, tool_calls

for d in sorted(SKILLS_DIR.iterdir()):
    print(d.name, "→", (d / "SKILL.md").read_text(encoding="utf-8").splitlines()[2][:80])

# %% [markdown]
# ## 1. SKILL.md 的结构
#
# - 开头 `---` 之间是“名片”：`name` 和 `description`。智能体只看名片决定要不要用，**所以 description 要写清“什么时候用”**。
# - 正文写步骤和规范，用到时才读。

# %%
print((SKILLS_DIR / "typhoon-grade" / "SKILL.md").read_text(encoding="utf-8"))

# %% [markdown]
# ## 2. 接到智能体上
#
# `backend=FilesystemBackend(root_dir=课程包目录, virtual_mode=True)` 让智能体能读课程包里的文件；
# `skills=["/skills/"]` 告诉它技能包在哪。`virtual_mode=True` 限制它只能访问课程包目录内的文件。


# %%
def build_agent(model, skills=True):
    return create_deep_agent(
        model=model,
        system_prompt="你是广东省气象台的预报助手，用中文回答。",
        skills=["/skills/"] if skills else None,
        backend=FilesystemBackend(root_dir=str(COURSE_ROOT), virtual_mode=True),
    )


model = llm.main_llm()
r = build_agent(model).invoke({"messages": [{"role": "user", "content": "台风中心最大风速 23 米/秒，阵风 28 米/秒，是什么等级？"}]})
show(r, max_tool_chars=200)
print("读取了哪些文件：", [c["args"].get("file_path") for c in tool_calls(r) if c["name"] == "read_file"])

# %% [markdown]
# 检查点：
#
# - 智能体读了 `typhoon-grade/SKILL.md` 吗？
# - 它用的是平均风 23，还是阵风 28？（23 是热带风暴，28 会被判成强热带风暴。）

# %% [markdown]
# ## 3. 无关问题不应触发
#
# 问“现在几点”，智能体不应该去读台风等级的技能。

# %%
model = llm.main_llm()
r = build_agent(model).invoke({"messages": [{"role": "user", "content": "现在几点？"}]})
print("读取的文件：", [c["args"].get("file_path") for c in tool_calls(r) if c["name"] == "read_file"])

# %% [markdown]
# ## 4. 练习：写你自己的 Skill
#
# 1. 选一项你最熟悉的业务经验（例如“回南天判断要点”“龙舟水期间强降水关注点”“寒潮预警发布条件”）。
# 2. 先口述给 Claude Code，让它用 `skill-creator` 的格式整理成 `skills/<英文名>/SKILL.md`。
# 3. 你自己修改：description 写清什么时候用；正文写成步骤。
# 4. 回到第 2 节，问一个应该触发它的问题，再问一个不该触发的问题。
#
# 对比实验：用 L2 的最高气温图，`skills=True` 和 `skills=False` 各写一段描述，按 9 项指标打分。
