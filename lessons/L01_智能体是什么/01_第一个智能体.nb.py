# %% [markdown]
# # L1 第一个智能体
#
# <!-- course-meta: real-llm -->
#
# 本 notebook 演示四件事：
#
# 1. 只有模型、没有工具时，模型回答不了“现在几点”这类问题。
# 2. 给模型一个工具，它就会自己决定去调用。
# 3. 工具说明（docstring）写得好不好，决定模型会不会用它。
# 4. 同一套工具交给 deepagents 的 `create_deep_agent`，它会多带一整套内置工具和规划流程。
#
# 运行方式：在 VS Code 或 Jupyter 中逐格运行（Shift+Enter）。
# 这一讲要用**真实模型**，`.env` 里的 `MAIN_API_KEY` 必须填好。
# 暂时没有 Key，就先看 `99_假模型剧本.ipynb`：那里用预设剧本演示同样的流程。

# %%
# 改了 common/、weather_tools/ 里的代码后自动重新加载，不用重启内核
# %load_ext autoreload
# %autoreload 2

from langchain.agents import create_agent
from langchain_core.tools import tool

from common import llm
from common.clock import now_bj
from common.trace import show

print("使用的模型：", llm.main_llm().model_name)

# %% [markdown]
# ## 1. 只有模型
#
# 直接问模型“现在几点”。模型没有手表，只能凭训练数据猜，或者老实说不知道。

# %%
print(llm.ask("现在北京时间几点？今天适合做哪个时次的早间会商？"))

# %% [markdown]
# ## 2. 给模型一个工具
#
# `@tool` 把一个普通 Python 函数变成工具。模型能看到三样东西：
#
# - 工具名：`get_beijing_time`
# - 说明：函数下面的三引号文字（docstring）
# - 参数：这里没有参数
#
# 课程里“当前时间”由 `.env` 的 `COURSE_NOW` 固定（默认 2026-08-11 08:30），方便后面几讲的离线台风数据对得上。
# 所以这个工具返回的可能是这个固定时间。把 `COURSE_NOW` 留空，就会返回电脑当前的北京时间。


# %%
@tool
def get_beijing_time() -> str:
    """获取当前北京时间，格式 YYYY-MM-DD HH:MM。回答与“现在”“今天”有关的问题前先调用。"""
    return now_bj().strftime("%Y-%m-%d %H:%M")


from common.clock import course_now_setting

print(get_beijing_time.invoke({}))
if course_now_setting():
    print("（这是 .env 中 COURSE_NOW 固定的课程时间，不是电脑时钟。想看真实时间，把 COURSE_NOW 留空；做 L4 之前再改回来。）")
else:
    print("（COURSE_NOW 为空，使用电脑当前的北京时间。）")

# %%
agent = create_agent(
    model=llm.main_llm(),
    tools=[get_beijing_time],
    system_prompt="你是广东省气象台的值班助手，用中文简洁回答。",
)
result = agent.invoke({"messages": [{"role": "user", "content": "现在几点？今天适合做哪个时次的早间会商？"}]})
show(result)

# %% [markdown]
# 读上面的运行过程：
#
# - [1] 用户提问
# - [2] 模型决定调用 `get_beijing_time`（这是模型自己的决定，不是程序写死的）
# - [3] 程序执行工具，把结果交回模型
# - [4] 模型根据工具结果回答
#
# 这就是“智能体循环”：模型想 → 调工具 → 看结果 → 再想，直到能回答为止。
#
# 真实模型每次跑的顺序、措辞都可能不一样，这是正常的；把同一格多跑几次，看看它会不会改主意。

# %% [markdown]
# ## 3. 说明写得含糊会怎样
#
# 把同一个工具的说明改成“时间”两个字，再问一次。真实模型下多试几次，观察它是否还会调用。
#
# 这一格再把工具改成返回**世界时**（UTC），说明仍然只写“时间”。模型看到一串时间，不知道是世界时还是北京时，多半会当北京时报出去。


# %%
from common.clock import UTC


@tool
def get_time_vague() -> str:
    """时间"""
    return now_bj().astimezone(UTC).strftime("%Y-%m-%d %H:%M")


agent = create_agent(model=llm.main_llm(), tools=[get_time_vague],
                     system_prompt="你是广东省气象台的值班助手，用中文简洁回答。")
show(agent.invoke({"messages": [{"role": "user", "content": "现在几点？"}]}))

print("对照——北京时：", now_bj().strftime("%Y-%m-%d %H:%M"),
      "世界时：", get_time_vague.invoke({}))

# %% [markdown]
# 检查点：
#
# - 模型调用 `get_time_vague` 了吗？说明只有“时间”，它凭什么决定调用？
# - 它报出来的时间是世界时还是北京时？把工具返回值和上面的“对照”比一比。
#
# 说明写不清，不只是“调不调用”的问题，还有“拿到的到底是什么时间”。L5 会专门讲这件事。

# %% [markdown]
# ## 4. 练习：加一个“区县属于哪个市”的工具
#
# 数据：`data/tmax_desc/地理划分_去除空列.csv`，列“区县”是县名，列“分区1”是所属地市。
#
# 下面给出参考写法。请你：
#
# 1. 读懂它的 docstring，想想模型怎么知道该传什么参数。
# 2. 运行后问“连州属于哪个市？”“乐昌和南雄都属于哪个市？”
# 3. 把 docstring 改差一点（比如删掉参数说明），看效果变化。

# %%
import pandas as pd

from common.paths import DATA_DIR

GEO = pd.read_csv(DATA_DIR / "tmax_desc" / "地理划分_去除空列.csv")


@tool
def find_city_of_county(county: str) -> str:
    """查询广东某个区县所属的地市和所在分区。

    参数 county：区县名称，可以带或不带“市/县/区”，例如“连州”或“连州市”。
    """
    hit = GEO[GEO["区县"].str.startswith(county.rstrip("市县区"))]
    if hit.empty:
        return f"没有找到区县：{county}"
    row = hit.iloc[0]
    return f"{row['区县']} 属于 {row['分区1']}，位于{row['行政区划']}（{row['分区2']}）"


print(find_city_of_county.invoke({"county": "连州"}))

# %%
agent = create_agent(model=llm.main_llm(), tools=[get_beijing_time, find_city_of_county],
                     system_prompt="你是广东省气象台的值班助手，用中文简洁回答。")
show(agent.invoke({"messages": [{"role": "user", "content": "连州属于哪个市？"}]}))

# %% [markdown]
# ## 5. 同一套工具，换成 deepagents 的 `create_deep_agent`
#
# 前四节都用 LangChain 的 `create_agent`。这里把**同样两个工具**交给 deepagents，问同一个问题：**你能使用哪些工具？**
#
# | | `create_agent`（LangChain） | `create_deep_agent`（deepagents 0.7.23） |
# |---|---|---|
# | 传入的工具 | `get_beijing_time`、`find_city_of_county` | 同样这两个 |
# | 智能体实际能用的工具 | **只有**这两个 | 这两个 **+ 内置工具箱** |
# | 内置工具箱 | 无 | `ls`/`read_file`/`write_file`/`edit_file`/`delete`/`glob`/`grep` 读写文件、`task` 派活给子智能体 |
# | 系统提示词 | 你写的那几句 | 你写的 + deepagents 自动附加的工作规范 |
# | 文件后端 | 无 | 默认 `StateBackend`，文件存在会话状态里、不碰磁盘；要读课程包才传 `FilesystemBackend`（L7 讲） |
# | 适合 | 一两个工具的小循环 | 多步骤、要查资料、要分工的专题任务 |
#
# 两个细节容易踩：
#
# - `write_todos`（列计划）**默认没有**，要自己加 `middleware=[TodoListMiddleware()]`，见第 6 节。
# - `execute`（跑命令）只有沙箱后端才有，默认后端下不会出现。
#
# 也就是说：工具还是你写的那些，deepagents 额外塞了一套“办公用品”和一份工作规范。

# %%
from deepagents import create_deep_agent

TOOLS = [get_beijing_time, find_city_of_county]
PROMPT = "你是广东省气象台的值班助手，用中文简洁回答。"
QUESTION = "你能使用哪些工具？"

plain_agent = create_agent(model=llm.main_llm(), tools=TOOLS, system_prompt=PROMPT)
deep_agent = create_deep_agent(model=llm.main_llm(), tools=TOOLS, system_prompt=PROMPT)

for name, agent in [("create_agent", plain_agent), ("create_deep_agent", deep_agent)]:
    print(f"===== {name} =====")
    show(agent.invoke({"messages": [{"role": "user", "content": QUESTION}]}))

# %% [markdown]
# 模型的回答可能不全、也可能把工具描述得不准。想拿到**确切**的工具清单，用下一格的探针：它不调用模型，只问一句“你被绑定了哪些工具”。

# %%
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class ToolSpy(BaseChatModel):
    """不调用任何模型接口：只记录被绑定了哪些工具，然后回一句话。"""

    seen: list[str] = []

    @property
    def _llm_type(self) -> str:
        return "tool-spy"

    def bind_tools(self, tools, **kwargs):
        if not self.seen:
            self.seen = sorted(getattr(t, "name", str(t)) for t in tools)
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="我看看我的工具。"))])


for name, build in [
    ("create_agent", lambda m: create_agent(model=m, tools=TOOLS, system_prompt=PROMPT)),
    ("create_deep_agent", lambda m: create_deep_agent(model=m, tools=TOOLS, system_prompt=PROMPT)),
]:
    spy = ToolSpy()
    build(spy).invoke({"messages": [{"role": "user", "content": QUESTION}]})
    print(f"{name} 绑定的工具（{len(spy.seen)} 个）：{spy.seen}")

# %% [markdown]
# 探针数出来的是**事实**，比模型自述可靠：2 个 vs 10 个，多出来的 8 个都是 deepagents 装的。

# %% [markdown]
# ## 6. 同一道多步骤问题，看规划差异
#
# 问“现在几点？连州属于哪个市？”。`create_agent` 只有那两个工具；deepagents 多了 `write_todos`，理论上可以先列计划、做完一条更新一条。
#
# 不过这类只有两问的小任务，真实模型常常觉得“不用计划”，直接调工具就答了。想更容易看到 todo 出现在轨迹里，把问题换得多步骤一点，比如“帮我核对连州、乐昌、南雄的归属，再汇总成一行一条”。

# %%
from langchain.agents.middleware import TodoListMiddleware

Q = "现在几点？连州属于哪个市？"

agent_lc = create_agent(model=llm.main_llm(), tools=TOOLS, system_prompt=PROMPT)

agent_deep = create_deep_agent(
    model=llm.main_llm(),
    tools=TOOLS,
    system_prompt=PROMPT,
    middleware=[TodoListMiddleware()],
)

for name, agent in [("create_agent", agent_lc), ("create_deep_agent", agent_deep)]:
    print(f"===== {name} =====")
    show(agent.invoke({"messages": [{"role": "user", "content": Q}]}))

# %% [markdown]
# 检查点：轨迹里有没有 `write_todos`？没有也正常——说明写的是“可以用”，不是“必须用”。工具**可用**和模型**决定用**是两件事，L8 专门练这个“该不该规划”。

# %% [markdown]
# 小结：什么时候用哪个
#
# - 工具少、流程固定（查时间、查区县）：`create_agent`，两行就够，轨迹好读。
# - 任务长、要查资料写报告、要分工（L7 起的台风专题、会商中枢）：`create_deep_agent`，文件、规划、技能包、子智能体的能力现成的。
# - 从 L7 开始课程统一用 `create_deep_agent`。这里先混个脸熟：**换框架不等于换工具，工具还是你写的那些。**
