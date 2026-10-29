"""用 mllm_test demo 中 gpt-4o 的真实回答验证评分移植是否一致（原评分 40 分）。"""
import json

from common.paths import DATA_DIR
from lessons_import import load_lesson_module

t = load_lesson_module("L03_提示词优化", "tmax_task")


def test_truth_matches_demo():
    demo = json.loads((DATA_DIR / "tmax" / "demo_gpt4o_task5.json").read_text(encoding="utf-8"))
    tr = t.truth("2024010120")
    assert tr["threshold"] == 27 and tr["Count"] == 2
    assert {s["County"] for s in tr["Stations"]} == {"信宜", "高州"}
    assert demo["prompt"]["result"]["Count"] == 2


def test_score_matches_original_40():
    demo = json.loads((DATA_DIR / "tmax" / "demo_gpt4o_task5.json").read_text(encoding="utf-8"))
    s = t.score("2024010120", demo["llm_result"])
    assert s["count_pred"] == 25
    assert s["numerical"] == 0.0 and s["geographical"] == 100.0
    assert s["final"] == 40.0


def test_count_score_rules():
    assert t.count_score(10, 10) == 1.0
    assert t.count_score(10, 8) == 0.7
    assert t.count_score(10, 5) == 0.3
    assert t.count_score(10, 4) == 0.0
