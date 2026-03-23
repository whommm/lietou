"""LLM API 客户端模块"""

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

    def analyze_jd(self, jd_text: str) -> str:
        """
        分析岗位描述（非流式）

        Args:
            jd_text: 原始岗位描述文本

        Returns:
            分析结果文本

        Raises:
            AuthError: API Key 无效或余额不足
            NetworkError: 网络连接失败
            TimeoutError: 请求超时
            LLMClientError: 其他错误
        """
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": jd_text}
                ],
                temperature=0.7,
                max_tokens=4096
            )
            return response.choices[0].message.content or ""
        except AuthenticationError as e:
            raise AuthError("API 密钥无效或账户余额不足，请检查配置。") from e
        except APITimeoutError as e:
            raise TimeoutError(f"请求超时（{self.timeout}秒），请稍后重试或检查网络。") from e
        except APIConnectionError as e:
            raise NetworkError("无法连接到大模型服务器，请检查网络或 API 地址是否正确。") from e
        except APIError as e:
            if "insufficient_quota" in str(e).lower():
                raise AuthError("账户余额不足，请充值后重试。") from e
            raise LLMClientError(f"API 调用失败: {str(e)}") from e
        except Exception as e:
            raise LLMClientError(f"未知错误: {str(e)}") from e

    def analyze_jd_stream(self, jd_text: str) -> Generator[str, None, None]:
        """
        分析岗位描述（流式输出）

        Args:
            jd_text: 原始岗位描述文本

        Yields:
            分析结果文本片段

        Raises:
            AuthError: API Key 无效或余额不足
            NetworkError: 网络连接失败
            TimeoutError: 请求超时
            LLMClientError: 其他错误
        """
        try:
            client = self._get_client()
            stream = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": jd_text}
                ],
                temperature=0.7,
                max_tokens=4096,
                stream=True
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except AuthenticationError as e:
            raise AuthError("API 密钥无效或账户余额不足，请检查配置。") from e
        except APITimeoutError as e:
            raise TimeoutError(f"请求超时（{self.timeout}秒），请稍后重试或检查网络。") from e
        except APIConnectionError as e:
            raise NetworkError("无法连接到大模型服务器，请检查网络或 API 地址是否正确。") from e
        except APIError as e:
            if "insufficient_quota" in str(e).lower():
                raise AuthError("账户余额不足，请充值后重试。") from e
            raise LLMClientError(f"API 调用失败: {str(e)}") from e
        except Exception as e:
            raise LLMClientError(f"未知错误: {str(e)}") from e
    def chat_stream(self, user_message: str, system_message: str = "") -> Generator[str, None, None]:
        """通用聊天接口（流式输出）"""
        try:
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
        except AuthenticationError as e:
            raise AuthError("API 密钥无效或账户余额不足，请检查配置。") from e
        except APITimeoutError as e:
            raise TimeoutError(f"请求超时（{self.timeout}秒），请稍后重试或检查网络。") from e
        except APIConnectionError as e:
            raise NetworkError("无法连接到大模型服务器，请检查网络或 API 地址是否正确。") from e
        except APIError as e:
            if "insufficient_quota" in str(e).lower():
                raise AuthError("账户余额不足，请充值后重试。") from e
            raise LLMClientError(f"API 调用失败: {str(e)}") from e
        except Exception as e:
            raise LLMClientError(f"未知错误: {str(e)}") from e
