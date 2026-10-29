"""L5 学员练习的测试。前两个已写好做示范，其余由学员补全。

学员练习未完成时这些测试会失败，这是正常的。
讲师检查参考答案时用：uv run pytest tests/test_typhoon.py
"""
import pytest

from lessons_import import load_lesson_module

ex = load_lesson_module("L05_时间与时区", "练习_台风回查")

pytestmark = pytest.mark.skipif(
    "not config.getoption('--run-exercises')",
    reason="学员练习：加 --run-exercises 运行",
)


def test_t2_bj_default():
    r = ex.query_typhoon("2026-08-11 08:00:00")
    assert r["tsid"] == [547, 550]


def test_t2_utc_converted():
    r = ex.query_typhoon("2026-08-11 00:00:00", "UTC")
    assert r["tsid"] == [547, 550]


def test_t2_bad_format():
    # TODO 学员：传 "2026-08-11 08:00" 应该报 ValueError
    pytest.fail("TODO：请补全这个测试")


def test_t4_hit_first_try():
    # TODO 学员：2026-08-11 08:00:00 第一次就命中，lookback_hours == 0
    pytest.fail("TODO：请补全这个测试")


def test_t4_lookback_21h():
    # TODO 学员：2026-07-29 08:00:00 要回查到 2026-07-28 11:00:00（21 小时）
    pytest.fail("TODO：请补全这个测试")


def test_t4_none_24h():
    # TODO 学员：2026-07-23 08:00:00 返回 not_applicable，共尝试 9 次
    pytest.fail("TODO：请补全这个测试")


def test_t4_unknown_shape():
    # TODO 学员：2026-09-01 08:00:00 返回结构不认识，原样返回
    pytest.fail("TODO：请补全这个测试")
