"""LLM 服务：DeepSeek + LangChain 封装。

职责：
1. 统一管理 ChatOpenAI 客户端（指向 DeepSeek 的 OpenAI 兼容接口）
2. 加载并渲染 `app/prompts/` 下的 Prompt 模板
3. 提供「纯文本补全」与「结构化 JSON 补全」两类调用，并做失败重试与 JSON 容错解析

设计说明：
- `deepseek-flash` 是推理模型，思考过程同样消耗 token，因此默认预留较大的
  `max_tokens`，避免正文被思考过程挤掉导致返回空内容。
- JSON 任务统一使用 DeepSeek 的 `response_format={"type": "json_object"}`，
  再叠加本地容错解析，最大程度保证结构化输出可用。
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from string import Template
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import PROMPTS_DIR, settings
from app.utils.response import CODE_CONFIG_ERROR, CODE_LLM_ERROR, BusinessError

logger = logging.getLogger(__name__)


# ======================================================================
# Prompt 模板加载与渲染
# ======================================================================


@lru_cache(maxsize=32)
def load_prompt(name: str) -> str:
    """读取 Prompt 模板文件内容（带缓存）。

    :param name: 模板文件名（不含 .txt 后缀），如 "task_decompose"
    """
    path: Path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise BusinessError(f"Prompt 模板不存在：{name}", CODE_CONFIG_ERROR)
    return path.read_text(encoding="utf-8")


def render_prompt(name: str, **kwargs: Any) -> str:
    """渲染 Prompt 模板。

    使用 `string.Template` 的 `$var` 语法，好处是模板里可以直接写 JSON 示例，
    不会与 `str.format` 的花括号冲突。
    """
    template = Template(load_prompt(name))
    try:
        return template.substitute(**kwargs)
    except KeyError as exc:  # 模板占位符与传入参数不匹配
        raise BusinessError(
            f"Prompt 模板 {name} 缺少参数：{exc}", CODE_CONFIG_ERROR
        ) from exc


# ======================================================================
# JSON 容错解析
# ======================================================================

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


# JSON 字符串字面量内不允许出现裸控制字符，需要转义回 \n / \r / \t
# 注意：字典的键是「真实控制字符」，值才是「反斜杠 + 字母」的转义写法
_CONTROL_CHAR_ESCAPES = {"\n": "\\n", "\r": "\\r", "\t": "\\t"}


def _escape_control_chars(text: str) -> str:
    """转义 JSON 字符串字面量内部的裸换行/制表符（模型偶尔会输出多行字符串）。

    只在字符串内部转义，字符串外的换行属于 JSON 的结构性空白，必须原样保留。
    已存在的转义序列（如 \\" 或 \\n）通过 `escaped` 标记原样跳过，不会被二次转义。
    """
    out: list[str] = []
    in_string = False
    escaped = False
    for char in text:
        if escaped:
            out.append(char)
            escaped = False
            continue
        if char == "\\":
            out.append(char)
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            out.append(char)
            continue
        if in_string and char in _CONTROL_CHAR_ESCAPES:
            out.append(_CONTROL_CHAR_ESCAPES[char])
            continue
        out.append(char)
    return "".join(out)


def extract_json(text: str) -> Any:
    """从模型输出中稳健地提取 JSON 对象/数组。

    依次尝试：直接解析 → 剥离 Markdown 代码块 → 截取最外层括号 → 修复尾逗号 →
    转义字符串内裸控制字符。全部失败则抛出业务异常。
    """
    if not text or not text.strip():
        raise BusinessError("模型返回内容为空，请重试", CODE_LLM_ERROR)

    candidates: list[str] = [text.strip()]

    fenced = _CODE_FENCE_RE.search(text)
    if fenced:
        candidates.append(fenced.group(1).strip())

    # 截取最外层的一对 {} 或 []
    start_obj, end_obj = text.find("{"), text.rfind("}")
    if start_obj != -1 and end_obj > start_obj:
        candidates.append(text[start_obj : end_obj + 1])
    start_arr, end_arr = text.find("["), text.rfind("]")
    if start_arr != -1 and end_arr > start_arr:
        candidates.append(text[start_arr : end_arr + 1])

    for candidate in candidates:
        for payload in (candidate, _TRAILING_COMMA_RE.sub(r"\1", candidate)):
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                pass
            try:
                return json.loads(_escape_control_chars(payload), strict=False)
            except json.JSONDecodeError:
                continue

    logger.error("JSON 解析失败，原始输出前 500 字符：%s", text[:500])
    raise BusinessError("模型返回格式异常，请重试", CODE_LLM_ERROR)


# ======================================================================
# LLM 客户端
# ======================================================================


class LLMService:
    """DeepSeek 调用封装（同步客户端 + 异步调用接口）。"""

    def __init__(self) -> None:
        self._client: ChatOpenAI | None = None

    @property
    def client(self) -> ChatOpenAI:
        """惰性构建 LangChain ChatOpenAI 客户端。"""
        if self._client is None:
            if not settings.DEEPSEEK_API_KEY:
                raise BusinessError(
                    "未配置 DEEPSEEK_API_KEY，请在 backend/.env 中填写后重启服务",
                    CODE_CONFIG_ERROR,
                )
            self._client = ChatOpenAI(
                model=settings.DEEPSEEK_MODEL,
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                timeout=settings.LLM_TIMEOUT,
                max_retries=2,
            )
        return self._client

    async def acomplete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str:
        """异步调用 DeepSeek，返回纯文本结果。

        :param json_mode: 为 True 时启用 DeepSeek 的 JSON 输出模式
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        overrides: dict[str, Any] = {}
        if temperature is not None:
            overrides["temperature"] = temperature
        if max_tokens is not None:
            overrides["max_tokens"] = max_tokens
        if json_mode:
            overrides["response_format"] = {"type": "json_object"}

        try:
            response = await self.client.ainvoke(messages, **overrides)
        except BusinessError:
            raise
        except Exception as exc:  # 网络/鉴权/限流等统一转换为友好提示
            logger.exception("DeepSeek 调用失败")
            raise BusinessError(
                f"AI 服务调用失败：{exc}。请检查网络与 API Key 配置后重试",
                CODE_LLM_ERROR,
            ) from exc

        content = response.content
        if isinstance(content, list):  # 兼容多模态分段返回
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part) for part in content
            )
        return (content or "").strip()

    async def acomplete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int | None = None,
        retries: int = 1,
    ) -> Any:
        """异步调用 DeepSeek 并解析为 JSON，失败自动重试。"""
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                raw = await self.acomplete(
                    system_prompt,
                    user_prompt,
                    max_tokens=max_tokens,
                    json_mode=True,
                )
                return extract_json(raw)
            except BusinessError as exc:
                last_error = exc
                logger.warning("JSON 补全第 %s 次失败：%s", attempt + 1, exc.message)
        raise last_error or BusinessError("AI 返回内容解析失败", CODE_LLM_ERROR)


@lru_cache
def get_llm_service() -> LLMService:
    """获取 LLM 服务单例，复用底层 HTTP 连接。"""
    return LLMService()
