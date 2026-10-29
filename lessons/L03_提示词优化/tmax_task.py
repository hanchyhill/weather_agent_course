"""L3 任务：统计最高气温高于阈值的区县（mllm_test tmax task5）。

- 真值与阈值规则：mllm_test/src/prompt_generator.py get_count_above_temp
- 评分规则：mllm_test/src/get_score.py score_task_5（S1.4 计数 60% + S2.3 地理 40%）
"""
import json
import math
import re
from pathlib import Path

import pandas as pd

from common.paths import DATA_DIR

TMAX = DATA_DIR / "tmax"
DAYS = ["2024010120", "2024010620", "2024011420"]


def truth(day: str) -> dict:
    """返回 {'threshold': X, 'Count': n, 'Stations': [...]}。阈值取全省最大值向下取整，最高 35。"""
    df = pd.read_csv(TMAX / "truth" / f"hs_temp_max_from20_{day}.csv")
    thr = min(35, math.floor(df["tmax"].max()))
    above = df[df["tmax"] > thr]
    return {"threshold": thr, "Count": len(above),
            "Stations": above[["County", "City", "tmax"]].to_dict(orient="records")}


def image(day: str) -> Path:
    return TMAX / "images" / f"hs_temp_max_from20_{day}.png"


def geo_table() -> str:
    """区县-地市-方位对照表（与 mllm_test 的 geo_prompt 同源：真值 CSV 的三列）。"""
    df = pd.read_csv(TMAX / "truth" / f"hs_temp_max_from20_{DAYS[0]}.csv")
    rows = [f"|{r.County}|{r.City}|{r.Region}|" for r in df.itertuples()]
    return "|County|City|Region|\n|---|---|---|\n" + "\n".join(rows)


def extract_json(text: str) -> dict | None:
    """从模型回答里取最后一个 ```json 代码块；没有就尝试整段解析。"""
    blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    for cand in reversed(blocks or [text]):
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            continue
    return None


def count_score(actual: int, predicted: int) -> float:
    """S1.4：完全相等 1.0；min/max ≥0.8 得 0.7；≥0.5 得 0.3；否则 0。"""
    if actual == predicted:
        return 1.0
    if actual == 0 or predicted == 0:
        return 0.0
    ratio = min(actual, predicted) / max(actual, predicted)
    return 0.7 if ratio >= 0.8 else 0.3 if ratio >= 0.5 else 0.0


def geo_score(actual: list[dict], predicted: list[dict]) -> float:
    """S2.3：先按区县一一配对（1.0），剩下的按地市配对（0.6），除以真值个数。"""
    if not actual:
        return 1.0
    used, total, matched = set(), 0.0, set()
    for i, a in enumerate(actual):
        for j, p in enumerate(predicted):
            if j not in used and a["County"] == p.get("County"):
                used.add(j); matched.add(i); total += 1.0
                break
    for i, a in enumerate(actual):
        if i in matched:
            continue
        for j, p in enumerate(predicted):
            if j not in used and a["City"] == p.get("City"):
                used.add(j); total += 0.6
                break
    return total / len(actual)


def score(day: str, answer_text: str) -> dict:
    """给一次模型回答打分。final = 计数 60% + 地理 40%，满分 100。"""
    t = truth(day)
    data = extract_json(answer_text)
    if data is None:
        return {"day": day, "final": 0.0, "count_pred": None, "count_true": t["Count"], "note": "没有解析出 JSON"}
    pred = data.get("Stations", [])
    c = count_score(t["Count"], int(data.get("Count", len(pred))))
    g = geo_score(t["Stations"], pred)
    return {"day": day, "final": round((0.6 * c + 0.4 * g) * 100, 1),
            "count_pred": data.get("Count"), "count_true": t["Count"],
            "numerical": round(c * 100, 1), "geographical": round(g * 100, 1)}
