"""模型配置：从 .env 读取主模型和视觉模型。

学员不需要改这个文件，只需要填 .env。

关于 DeepSeek 思考模式：deepseek-flash 默认开启思考模式。思考模式下调用工具，
要求把每轮的 reasoning_content 原样回传，否则接口返回 400。
LangChain 的 ChatOpenAI 不会回传这个字段，所以智能体默认关闭思考模式。
"""
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from common.paths import COURSE_ROOT

load_dotenv(COURSE_ROOT / ".env")


def use_fake_llm() -> bool:
    """COURSE_FAKE_LLM=1 时，示例使用预设回答，不调用模型。"""
    return os.getenv("COURSE_FAKE_LLM", "0").strip() == "1"


def _build(prefix: str, *, thinking: bool) -> ChatOpenAI:
    api_key = os.getenv(f"{prefix}_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            f".env 中没有填写 {prefix}_API_KEY。"
            "请按《课前准备》第 9 节配置，或设置 COURSE_FAKE_LLM=1 先体验流程。"
        )
    base_url = os.getenv(f"{prefix}_BASE_URL", "https://api.deepseek.com").strip()
    extra_body = None
    if "deepseek" in base_url:
        extra_body = {"thinking": {"type": "enabled" if thinking else "disabled"}}
    # 部分 OpenAI 兼容网关的 GPT 模型需要使用 Responses API。
    responses_api = os.getenv(f"{prefix}_USE_RESPONSES_API", "").strip().lower()
    if responses_api not in {"", "0", "1", "false", "true"}:
        raise ValueError(f"{prefix}_USE_RESPONSES_API 请填写 1 或 0")
    return ChatOpenAI(
        model=os.getenv(f"{prefix}_MODEL", "deepseek-flash").strip(),
        api_key=api_key,
        base_url=base_url,
        timeout=120,
        max_retries=2,
        extra_body=extra_body,
        use_responses_api=(responses_api in {"1", "true"}) if responses_api else None,
    )


def main_llm(*, thinking: bool = False) -> ChatOpenAI:
    """主模型：规划、调用工具、写稿。"""
    return _build("MAIN", thinking=thinking)


def agent_model(*fake_turns):
    """智能体用的模型。COURSE_FAKE_LLM=1 时返回按剧本回答的假模型。

    fake_turns 是假模型依次说的话（可以包含工具调用），见 common/fake.py。
    """
    if use_fake_llm():
        from common.fake import scripted
        return scripted(*fake_turns)
    return main_llm()


def ask(prompt: str, *, fake_answer: str = "（COURSE_FAKE_LLM=1，未调用模型）") -> str:
    """直接问主模型一个问题，返回文字。"""
    if use_fake_llm():
        return fake_answer
    # 用 .text 而不是 .content：开启 Responses API 时 content 是内容块列表，.text 只取文字部分
    return main_llm().invoke(prompt).text


def vlm(*, alt: bool = False) -> ChatOpenAI:
    """视觉模型：判读图片。alt=True 时使用 ALT_VLM_*（如 Agnes）做对比。"""
    return _build("ALT_VLM" if alt else "VLM", thinking=False)
