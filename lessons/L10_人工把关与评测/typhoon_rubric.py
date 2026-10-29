"""台风报告评分表（台风专线 T10）与判官提示词。

6 项，每项 0～2 分，满分 12 分，换算成百分制。
"""
import json
import re

RUBRIC = [
    {"id": 1, "name": "基本信息与资料一致", "rule": "编号、名称、位置、强度与台风查询结果一致。2 分全对；1 分有 1 处不一致；0 分多处不一致或编造。"},
    {"id": 2, "name": "时间正确", "rule": "统一用北京时，资料时次（含回查）说明清楚。2 分正确；1 分有混用但不影响结论；0 分时间错误。"},
    {"id": 3, "name": "每个活动台风都有结论", "rule": "查询结果中的每个台风都有概况和路径趋势。2 分全有；1 分有遗漏但提到名字；0 分漏掉台风。"},
    {"id": 4, "name": "活动概率不误作生成概率", "rule": "高值区先与已有台风对照，对不上的标“归属不明”。2 分做到；1 分有对照但措辞不严；0 分直接说将生成新台风。"},
    {"id": 5, "name": "影响结论有依据", "rule": "对广东和南海的影响结论能在图或数据中找到依据。2 分有依据；1 分部分有；0 分无依据。"},
    {"id": 6, "name": "无影响或资料缺失时说明清楚", "rule": "不影响广东时说明原因；资料缺失时写明，不编造。2 分做到；1 分说明不完整；0 分编造或回避。"},
]


def total(scores: dict[int, int]) -> float:
    return round(sum(scores.get(r["id"], 0) for r in RUBRIC) / (2 * len(RUBRIC)) * 100, 1)


def judge_prompt(report: str, typhoon_data: str) -> str:
    rules = "\n".join(f"{r['id']}. {r['name']}：{r['rule']}" for r in RUBRIC)
    return f"""你是台风报告审核员。请按评分表给下面的台风分析报告打分，每项 0～2 分，并写扣分理由。

## 评分表
{rules}

## 台风查询结果（作为事实依据）
{typhoon_data}

## 待审报告
{report}

## 输出
只输出一个 JSON 代码块：
```json
{{"scores": {{"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0}}, "reasons": {{"1": "", "2": "", "3": "", "4": "", "5": "", "6": ""}}}}
```"""


def parse_judge(text: str) -> dict[int, int]:
    m = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    data = json.loads(m[-1] if m else text)
    return {int(k): int(v) for k, v in data["scores"].items()}
