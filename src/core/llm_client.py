"""LLM API 客户端模块"""

import re
import time
from openai import (
    OpenAI,
    APIError,
    AuthenticationError,
    APITimeoutError,
    APIConnectionError,
)
from typing import Optional
from .prompt import SYSTEM_PROMPT, SEARCH_INTENT_PROMPT_APPENDIX


class LLMClientError(Exception):
    pass


class AuthError(LLMClientError):
    pass


class NetworkError(LLMClientError):
    pass


class TimeoutError(LLMClientError):
    pass


class LLMClient:
    MAX_RETRIES = 2
    RETRY_DELAY_BASE = 1.0

    def __init__(
        self,
        api_base_url: str,
        api_key: str,
        model_name: str = "deepseek-chat",
        timeout: int = 120,
    ):
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        self._client: Optional[OpenAI] = None

    def _get_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                api_key=self.api_key, base_url=self.api_base_url, timeout=self.timeout
            )
        return self._client

    def _execute_with_retry(self, func, *args, **kwargs):
        last_error = None
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                return func(*args, **kwargs)
            except AuthError:
                raise
            except (NetworkError, TimeoutError) as e:
                last_error = e
                if attempt < self.MAX_RETRIES:
                    delay = self.RETRY_DELAY_BASE * (2**attempt)
                    time.sleep(delay)
            except (APIError, Exception) as e:
                translated = self._translate_exception(e)
                if isinstance(translated, AuthError):
                    raise translated
                last_error = translated
                if attempt < self.MAX_RETRIES:
                    delay = self.RETRY_DELAY_BASE * (2**attempt)
                    time.sleep(delay)
        raise last_error or LLMClientError("请求失败")

    @property
    def _is_reasoning_model(self) -> bool:
        """检测当前是否为思考模型"""
        name = self.model_name.lower()
        return any(k in name for k in ("reasoner", "coding", "thinking", "k1.5", "k1"))

    def _get_max_tokens(self) -> int:
        """根据模型类型返回合适的 max_tokens"""
        return 8192 if self._is_reasoning_model else 4096

    @staticmethod
    def _clean_content(content: str) -> str:
        """清理模型返回内容，移除思考过程等"""
        if not content:
            return ""
        # 移除 <think>...</think> 标签及其内容
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
        # 移除多余的空行
        content = re.sub(r"\n{3,}", "\n\n", content)
        return content.strip()

    @staticmethod
    def _translate_exception(e: Exception) -> LLMClientError:
        if isinstance(e, AuthenticationError):
            return AuthError("API 密钥无效或账户余额不足，请检查后重试。")
        if isinstance(e, APITimeoutError):
            return TimeoutError("请求超时，请稍后重试。")
        if isinstance(e, APIConnectionError):
            return NetworkError("无法连接到大模型服务器，请检查网络或 API 地址。")
        if isinstance(e, APIError):
            if "insufficient_quota" in str(e).lower():
                return AuthError("账户余额不足，请充值后重试。")
            return LLMClientError("API 请求失败: {}".format(str(e)))
        return LLMClientError("未知错误: {}".format(str(e)))

    def _call_api(self, client, kwargs):
        """统一调用 API，思考模型使用流式获取完整内容。"""
        if self._is_reasoning_model:
            kwargs["stream"] = True
            response = client.chat.completions.create(**kwargs)
            chunks = []
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    chunks.append(chunk.choices[0].delta.content)
            return self._clean_content("".join(chunks))
        else:
            response = client.chat.completions.create(**kwargs)
            if not response.choices:
                raise LLMClientError("API 返回为空，未生成任何内容。")
            message = response.choices[0].message
            if message is None:
                raise LLMClientError("API 返回消息为空。")
            return self._clean_content(message.content or "")

    def _do_analyze_jd(self, jd_text: str, company_context: str = "") -> str:
        client = self._get_client()

        user_message = jd_text
        if company_context:
            user_message = f"\u3010\u516c\u53f8\u80cc\u666f\u4fe1\u606f\u3011\n{company_context}\n\n\u3010\u5c97\u4f4d\u63cf\u8ff0\u3011\n{jd_text}"

        kwargs = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT + SEARCH_INTENT_PROMPT_APPENDIX,
                },
                {"role": "user", "content": user_message},
            ],
            "max_tokens": self._get_max_tokens(),
        }
        if not self._is_reasoning_model:
            kwargs["temperature"] = 0.7
        return self._call_api(client, kwargs)

    def analyze_jd(self, jd_text: str, company_context: str = "") -> str:
        return self._execute_with_retry(self._do_analyze_jd, jd_text, company_context)

    def _do_chat(self, user_message: str, system_message: str = "") -> str:
        client = self._get_client()
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": user_message})

        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": self._get_max_tokens(),
        }
        if not self._is_reasoning_model:
            kwargs["temperature"] = 0.7
        return self._call_api(client, kwargs)

    def chat(self, user_message: str, system_message: str = "") -> str:
        return self._execute_with_retry(self._do_chat, user_message, system_message)
