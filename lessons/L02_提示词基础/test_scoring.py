"""用 sysu_vlm_test 的人工评分记录验证总分计算公式。"""
import csv

from common.paths import DATA_DIR
from lessons_import import load_lesson_module

scoring = load_lesson_module("L02_提示词基础", "scoring")


def test_total_matches_human_records():
    path = DATA_DIR / "tmax_desc" / "scores_刘鑫杭_gemini-3-flash.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    checked = 0
    for r in rows:
        scores = {i: float(r[f"指标{i}分数"]) for i in range(1, 10)}
        assert abs(scoring.total_score(scores) - float(r["总分"])) < 0.15, r["图片名称"]
        checked += 1
    assert checked == 30
