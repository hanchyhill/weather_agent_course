# 预报员智能体开发实操课程：课程包

每讲一个目录，内含教案和示例代码。课程计划见上级目录的 `plan/`。

## 快速开始

```powershell
cd course
uv sync                     # 按 uv.lock 安装全部依赖（含 ipykernel、jupyterlab），Python 3.13
copy .env.example .env      # 填写 DeepSeek Key；没有 Key 时设 COURSE_FAKE_LLM=1
uv run python lessons/L00_环境检查/check_env.py
```

打开 notebook：用 VS Code 打开 `course` 目录（`.vscode/` 已配置默认使用 `.venv`，并推荐安装 Python、Jupyter、Claude Code 等扩展），双击 `.ipynb` 即可运行；不用 VS Code 时运行 `uv run jupyter lab`。

依赖清单与课前环境包 `installers/python-env/` 完全一致（同一份 `uv.lock`）。学员课前已装好环境包的，这里 `uv sync` 只用本机缓存。讲师需要重新生成 notebook 时，用 `uv sync`（包含 dev 组：jupytext、nbclient）；学员用 `uv sync --no-dev` 即可，不装也不影响上课。

## 目录

| 讲次 | 目录 | 教案 | 示例代码 | 台风专线 |
|---|---|---|---|---|
| L0 | `lessons/L00_环境检查` | 环境检查、AI 编程助手入门 | `check_env.py`、`01_时效表演示.py` | |
| L1 | `lessons/L01_智能体是什么` | 智能体循环、工具说明 | `01_第一个智能体.ipynb`（需真实模型）、`99_假模型剧本.ipynb` | |
| L2 | `lessons/L02_提示词基础` | 图片提示词设计、测试与幻灯片分享 | `课程2_提示词设计.html`（浏览器打开） | |
| L3 | `lessons/L03_提示词优化` | A/B 实验、提示词找茬 | `01_提示词AB实验.ipynb`、`tmax_task.py`、`prompts/` | |
| L4 | `lessons/L04_文本类工具` | 工具三要素 | `01_读懂台风数据_T0.ipynb`、`02_按世界时查询_T1.ipynb` | T0、T1 |
| L5 | `lessons/L05_时间与时区` | 时次、时效、回查 | `01_起报时次与时效.ipynb`、`02_台风北京时与回查_T2_T4.ipynb`、`练习_台风回查.py` | T2～T4 |
| L6 | `lessons/L06_图像类工具` | 看图工具、tsid 串联 | `01_看图工具与判读提示词.ipynb`、`02_用tsid取路径图与诊断图_T5_T6.ipynb` | T5、T6 |
| L7 | `lessons/L07_Skill技能包` | Skill | `01_用Skill沉淀经验.ipynb`、`skills/` | |
| L8 | `lessons/L08_多接口组合与规划` | 规划、验收清单 | `01_台风专题智能体_T7_T8.ipynb`、`typhoon_agent.py`、`checklist.py` | T7、T8 |
| L9 | `lessons/L09_子智能体分工` | 会商中枢 | `01_会商中枢_T9.ipynb`、`consult_hub.py` | T9 |
| L10 | `lessons/L10_人工把关与评测` | 人工确认、判官 | `01_人工确认保存_HITL.ipynb`、`02_判官与人工一致性_T10.ipynb` | T10 |
| L11 | `lessons/L11_结课项目` | 迷你会商助手 | `starter_mini_consult.py`、`评分表.md` | |
| L12 | `lessons/L12_天气查询专线` | 天气查询渐进式案例（可独立开课） | `01_三个工具_W1_W3.ipynb`、`02_今天要查两个工具_W4.ipynb`、`03_北京时与世界时_W5.ipynb`、`weather_agent.py` | 天气专线 W1～W5 |

除改为 HTML 教学的 L2 外，每个 notebook 讲次的目录下还有一个 `99_假模型剧本.ipynb`：正式 notebook 全用真实模型，写死的剧本（假模型照台词回答）集中放在这个文件里。没有 API Key 时用它看流程。两份的源文件都是 `.nb.py`。

公共代码：

| 目录 | 内容 |
|---|---|
| `common/` | 模型配置（`llm.py`）、课程时间（`clock.py`）、假模型（`fake.py`）、运行轨迹打印（`trace.py`） |
| `weather_tools/` | 气象工具离线版：时间换算、台风查询与回查、路径图、看图、给智能体用的 `@tool` 、天气查询（`weather.py`）。内网台风取数地址由 `typhoon.data_endpoint()` 提供，讲义里不出现明文（可用 `.env` 的 `TYPHOON_API_URL` 覆盖） |
| `skills/` | 示例技能：`tmax-description`、`typhoon-grade` |
| `data/` | 离线数据，来源见下表 |
| `tests/` | 时间工具、台风工具的验收用例 |
| `tools/build_notebooks.py` | 讲师用：`.nb.py` 转 `.ipynb`，可选执行验证 |

## 两种运行模式

| 模式 | 设置 | 用途 |
|---|---|---|
| 真实模型 | `.env` 填 Key，`COURSE_FAKE_LLM=0` | 正式上课 |
| 假模型 | `COURSE_FAKE_LLM=1` | 没有 Key 时熟悉流程；讲师验证代码。模型按剧本册里写好的台词回答 |

正式 notebook 全用真实模型，不写剧本，免得学员把预设台词当成模型自己的话。剧本统一放在各讲目录下的 `99_假模型剧本.ipynb`（第一格强制 `COURSE_FAKE_LLM=1`，打开就能跑）。正式 notebook 的源文件头部标了 `<!-- course-meta: real-llm -->`，`build_notebooks.py --execute` 只转换、不执行它们。

“当前时间”由 `.env` 的 `COURSE_NOW` 固定（默认 2026-08-11 08:30），这样离线数据才对得上。

## 离线数据来源

| 目录 | 内容 | 来源 |
|---|---|---|
| `data/typhoon_api/getyphdata.json` | 台风接口返回，按北京时索引 | 2026 年各条：huishang_demo 真实运行日志；摩羯：由 mllm_test BCGZ 数据转换；一条教学构造的异常返回 |
| `data/typhoon_track/` | 摩羯（tsid 736）路径图 6 张、实况与预报 JSON | mllm_test `data/typhoon` |
| `data/typhoon_env/` | 环境场、活动概率合成图（2026-08-10 12 UTC 起报） | huishang_demo 2026-08-11 运行的 `merged_charts` |
| `data/tmax/` | 最高气温实况图 3 张、站点真值、gpt-4o 错题 | mllm_test `data/tmax`、`demo/` |
| `data/tmax_desc/` | 最高气温图 6 张、gemini 描述、人工 9 项评分、地理分区、评分指标 | sysu_vlm_test `data/` |
| `data/nwp/` | 数值模式四宫格样例图 | agent_dev `static/img` |
| `data/weather/` | 地名库、实况站点、预报格点（L12） | **教学构造**，接口字段参照 agent_dev `ToolGameWeather`；`tools/gen_weather_data.py` 生成 |

没有复制任何 `.env`、密钥或内网地址。

## 讲师检查

```powershell
uv run pytest                                   # 参考答案与各讲测试（学员练习默认跳过）
uv run python tools/build_notebooks.py --execute # 重新生成全部 notebook 并在假模型下执行
```

`--execute` 只执行能在假模式下跑的 notebook；源文件头部标了 `<!-- course-meta: real-llm -->` 的正式 notebook 只转换、不执行，输出里会写「需真实模型，跳过执行」。要在假模式下验证各讲流程，靠的是 `99_假模型剧本.ipynb`。

验证情况：以上两条命令在假模型下全部通过（2026-10-08，deepagents 0.7.23、langchain 1.4.4；2026-10-28 拆分剧本后重跑）。L1 的 `01_第一个智能体.ipynb` 已于 2026-10-28 用真实模型完整跑通一遍。**其余各讲在真实模型（DeepSeek、Agnes）下没有运行过**，讲师须在试讲时用真实 Key 跑一遍，按实际效果调整提示词。
