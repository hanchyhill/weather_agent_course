"""课程包内的常用路径。"""
from pathlib import Path

COURSE_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = COURSE_ROOT / "data"
OUTPUT_DIR = COURSE_ROOT / "outputs"
SKILLS_DIR = COURSE_ROOT / "skills"
