"""看图：把图片交给视觉模型判读，返回“图片信息 + 解读内容”。

做法来自 huishang_demo 的 interpret_* 工具：
下载图片 → 缩放转 PNG → base64 → 视觉模型 → 文字。
主模型不直接看图，上下文更干净。
"""
import base64
import io
from pathlib import Path

from langchain_core.messages import HumanMessage
from PIL import Image

from common import llm


def image_to_data_url(path: Path, max_side: int = 2048) -> str:
    """把本地图片缩放到不超过 max_side 像素，转成 data URL。"""
    im = Image.open(path).convert("RGB")
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def ask_image(path: Path, prompt: str, *, alt: bool = False,
              fake_answer: str = "（COURSE_FAKE_LLM=1，未调用视觉模型）") -> str:
    """把一张图和一段提示词交给视觉模型，返回模型的文字回答。"""
    if llm.use_fake_llm():
        return fake_answer
    msg = HumanMessage(content=[
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": image_to_data_url(path)}},
    ])
    return llm.vlm(alt=alt).invoke([msg]).text


def interpret_image(path: Path, prompt: str, *, alt: bool = False, meta: str = "") -> str:
    """调用视觉模型判读一张图。meta 是写在结果开头的图片信息（时间、产品等）。"""
    head = f"【图片信息】\n文件：{path.name}\n{meta}".rstrip()
    return f"{head}\n\n【解读内容】\n{ask_image(path, prompt, alt=alt)}"
