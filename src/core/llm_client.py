"""LLM API 客户端模块"""

import time
from openai import OpenAI, APIError, AuthenticationError, APITimeoutError, APIConnectionError
from typing import Generator, Optional
from .prompt import SYSTEM_PROMPT


class LLMClientError(Exception):
    """LLM 客户端异常基类"""
    pass


class AuthError(LLMClientError):
    """认证错误"""
    pass


class NetworkError(LLMClientError):
    """网络错误"""
    pass


class TimeoutError(LLMClientError):
    """超时错误"""
    pass


class LLMClient:
    """大语言模型客户端"""

    MAX_RETRIES = 2
    RETRY_DELAY_BASE = 1.0

    def __init__(self, api_base_url: str, api_key: str, model_name: str = "deepseek-chat", timeout: int = 120):
        self.api_base_url = api_base_url.rstrip('/')
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        self._client: Optional[OpenAI] = None

    def _get_client(self) -> OpenAI:
        """获取或创建 OpenAI 客户端"""
        if self._client is None:
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_base_url,
                timeout=self.timeout
            )
        return self._client

    def _execute_with_retry(self, func, *args, **kwargs):
        """带重试的执行器"""
        last_error = None
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                return func(*args, **kwargs)
            except AuthError:
                raise
            except (NetworkError, TimeoutError) as e:
                last_error = e
                if attempt < self.MAX_RETRIES:
                    delay = self.RETRY_DELAY_BASE * (2 ** attempt)
                    time.sleep(delay)
            except APIError as e:
                last_error = e
                if "insufficient_quota" in str(e).lower():
                    raise AuthError("账户余额不足，请充值后重试。") from e
                if attempt < self.MAX_RETRIES:
                    delay = self.RETRY_DELAY_BASE * (2 ** attempt)
                    time.sleep(delay)
            except Exception as e:
                last_error = e
                if attempt < self.MAX_RETRIES:
                    delay = self.RETRY_DELAY_BASE * (2 ** attempt)
                    time.sleep(delay)
        raise last_error or LLMClientError("请求失败")

    def _do_analyze_jd(self, jd_text: str, company_context: str = "") -> str:
        """实际执行分析请求（非流式）"""
        client = self._get_client()

        user_message = jd_text
        if company_context:
            user_message = f"\u3010\u516c\u53f8\u80cc\u666f\u4fe1\u606f\u3011\n{company_context}\n\n\u3010\u5c97\u4f4d\u63cf\u8ff0\u3011\n{jd_text}"

        response = client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=4096
        )
        return response.choices[0].message.content or ""

    def analyze_jd(self, jd_text: str, company_context: str = "") -> str:
        """
        分析岗位描述（非流式）

        Args:
            jd_text: 原始岗位描述文本
            company_context: 公司调研上下文（可选）

        Returns:
            分析结果文本

        Raises:
            AuthError: API Key 无效或余额不足
            NetworkError: 网络连接失败
            TimeoutError: 请求超时
            LLMClientError: 其他错误
        """
        return self._execute_with_retry(self._do_analyze_jd, jd_text, company_context)

    def _do_analyze_jd_stream(self, jd_text: str, company_context: str = "") -> Generator[str, None, None]:
        """实际执行分析请求（流式）"""
        client = self._get_client()

        user_message = jd_text
        if company_context:
            user_message = f"\u3010\u516c\u53f8\u80cc\u666f\u4fe1\u606f\u3011\n{company_context}\n\n\u3010\u5c97\u4f4d\u63cf\u8ff0\u3011\n{jd_text}"

        stream = client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=4096,
            stream=True
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def analyze_jd_stream(self, jd_text: str, company_context: str = "") -> Generator[str, None, None]:
        """
        分析岗位描述（流式输出）

        Args:
            jd_text: 原始岗位描述文本
            company_context: 公司调研上下文（可选）

        Yields:
            分析结果文本片段

        Raises:
            AuthError: API Key 无效或余额不足
            NetworkError: 网络连接失败
            TimeoutError: 请求超时
            LLMClientError: 其他错误
        """
        return self._execute_with_retry(self._do_analyze_jd_stream, jd_text, company_context)

    def _do_chat_stream(self, user_message: str, system_message: str = "") -> Generator[str, None, None]:
        """实际执行聊天请求（流式）"""
        client = self._get_client()
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": user_message})

        stream = client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.7,
            max_tokens=4096,
            stream=True
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def chat_stream(self, user_message: str, system_message: str = "") -> Generator[str, None, None]:
        """通用聊天接口（流式输出）"""
        return self._execute_with_retry(self._do_chat_stream, user_message, system_message)
