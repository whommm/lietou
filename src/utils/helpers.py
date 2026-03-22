"""工具函数模块"""

import pyperclip


def copy_to_clipboard(text: str) -> bool:
    """
    复制文本到系统剪贴板

    Args:
        text: 要复制的文本

    Returns:
        是否成功
    """
    try:
        pyperclip.copy(text)
        return True
    except Exception:
        return False


def validate_url(url: str) -> bool:
    """
    简单验证 URL 格式

    Args:
        url: URL 字符串

    Returns:
        是否有效
    """
    if not url:
        return False
    return url.startswith(("http://", "https://"))


def validate_api_key(key: str) -> bool:
    """
    简单验证 API Key 格式

    Args:
        key: API Key 字符串

    Returns:
        是否有效
    """
    if not key:
        return False
    return len(key) >= 10
