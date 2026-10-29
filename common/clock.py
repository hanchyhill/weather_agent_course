"""课程时间：离线模式下用 COURSE_NOW 固定“当前北京时间”。

为什么要固定：离线数据只覆盖几个个例，如果按电脑的真实时间去查，
永远查不到数据。讲师考核时改 .env 里的 COURSE_NOW，就能检验
学员的时间处理是否正确。

每次取时间都重新读 .env，所以改了 COURSE_NOW 不用重启 notebook 内核。
优先级：set_course_now() > .env 里的 COURSE_NOW > 系统环境变量 COURSE_NOW > 电脑时钟。
"""
import os
from datetime import datetime, timedelta, timezone

from dotenv import dotenv_values

from common.paths import COURSE_ROOT

BJ_TZ = timezone(timedelta(hours=8), name="北京时")
UTC = timezone.utc

_override: str | None = None


def set_course_now(value: str | None) -> None:
    """在程序里临时指定课程时间（格式 YYYY-MM-DD HH:MM）；传 None 取消。"""
    global _override
    _override = value


def course_now_setting() -> str:
    """当前生效的 COURSE_NOW 设置；为空表示使用电脑时钟。"""
    if _override is not None:
        return _override.strip()
    env_file = COURSE_ROOT / ".env"
    if env_file.exists():
        values = dotenv_values(env_file)
        if "COURSE_NOW" in values:
            return (values["COURSE_NOW"] or "").strip()
    return os.getenv("COURSE_NOW", "").strip()


def now_bj() -> datetime:
    """返回当前北京时间（带时区）。设置了 COURSE_NOW 时返回该时间。"""
    fixed = course_now_setting()
    if fixed:
        return datetime.strptime(fixed, "%Y-%m-%d %H:%M").replace(tzinfo=BJ_TZ)
    return datetime.now(BJ_TZ)
