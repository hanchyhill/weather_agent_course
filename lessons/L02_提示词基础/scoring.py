"""最高气温分布描述的 9 项评分表（来自 sysu_vlm_test/task4_评分指标.md 与 src/stores/scoring.js）。

总分 = Σ(得分 / 满分 × 权重)，满分 100。
"""
METRICS = [
    {"id": 1, "name": "最高气温数值准确性", "max": 1, "weight": 5},
    {"id": 2, "name": "最高气温地理准确性", "max": 2, "weight": 10},
    {"id": 3, "name": "温度区间准确性", "max": 5, "weight": 20},
    {"id": 4, "name": "温度区间不能重叠", "max": 1, "weight": 10},
    {"id": 5, "name": "地理范围不能重叠", "max": 1, "weight": 10},
    {"id": 6, "name": "地理和气温范围表述的完整性", "max": 1, "weight": 10},
    {"id": 7, "name": "气温范围聚类合理性", "max": 4, "weight": 20},
    {"id": 8, "name": "气温描述顺序", "max": 1, "weight": 5},
    {"id": 9, "name": "用语规范性", "max": 5, "weight": 10},
]


def total_score(scores: dict[int, float]) -> float:
    """scores 形如 {1: 1, 2: 2, 3: 4.5, ...}，返回 0～100 的总分。"""
    total = 0.0
    for m in METRICS:
        s = scores.get(m["id"], 0)
        if not 0 <= s <= m["max"]:
            raise ValueError(f"指标{m['id']}（{m['name']}）得分应在 0～{m['max']}，实际 {s}")
        total += s / m["max"] * m["weight"]
    return round(total, 1)


def score_sheet() -> str:
    """打印给学员的打分表。"""
    lines = ["| 序号 | 指标 | 满分 | 权重 | 得分 |", "|---|---|---|---|---|"]
    lines += [f"| {m['id']} | {m['name']} | {m['max']} | {m['weight']} |  |" for m in METRICS]
    return "\n".join(lines)
