"""课程时间：改 .env 后不用重启即可生效；程序指定的时间优先。"""
from datetime import datetime

import pytest

from common import clock


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    monkeypatch.setattr(clock, "COURSE_ROOT", tmp_path)
    monkeypatch.delenv("COURSE_NOW", raising=False)
    clock.set_course_now(None)
    yield f
    clock.set_course_now(None)


def test_fixed_time_from_env_file(env_file):
    env_file.write_text("COURSE_NOW=2026-08-11 08:30\n", encoding="utf-8")
    assert clock.now_bj().strftime("%Y-%m-%d %H:%M") == "2026-08-11 08:30"


def test_edit_env_file_takes_effect_without_restart(env_file):
    env_file.write_text("COURSE_NOW=2026-08-11 08:30\n", encoding="utf-8")
    assert clock.now_bj().year == 2026 and clock.now_bj().month == 8
    env_file.write_text("COURSE_NOW=\n", encoding="utf-8")
    assert abs((clock.now_bj() - datetime.now(clock.BJ_TZ)).total_seconds()) < 5


def test_env_file_wins_over_stale_process_env(env_file, monkeypatch):
    # 模拟 VS Code 在内核启动时注入的旧值
    monkeypatch.setenv("COURSE_NOW", "2026-08-11 08:30")
    env_file.write_text("COURSE_NOW=\n", encoding="utf-8")
    assert clock.course_now_setting() == ""


def test_set_course_now_wins(env_file):
    env_file.write_text("COURSE_NOW=2026-08-11 08:30\n", encoding="utf-8")
    clock.set_course_now("2026-07-23 08:30")
    assert clock.now_bj().strftime("%Y-%m-%d %H:%M") == "2026-07-23 08:30"


def test_process_env_used_when_env_file_has_no_key(env_file, monkeypatch):
    env_file.write_text("MAIN_MODEL=x\n", encoding="utf-8")
    monkeypatch.setenv("COURSE_NOW", "2026-07-29 08:00")
    assert clock.now_bj().strftime("%Y-%m-%d %H:%M") == "2026-07-29 08:00"
