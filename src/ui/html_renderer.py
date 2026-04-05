"""HTML渲染器模块 - 将Markdown转换为精美HTML显示（鲁棒版）"""

import markdown
import tkinter as tk
from tkinterweb import HtmlFrame
from typing import Optional
from .themes import LIGHT_CSS, DARK_CSS
from ..utils.html_sanitizer import HtmlSanitizer


class HtmlRenderer:
    """HTML渲染器 - 支持Markdown转换和流式输出

    核心改进：
    - 节流渲染：300ms最小间隔，防止事件队列洪水
    - 异常兜底：渲染失败自动降级为纯文本框，不再闪退
    - HTML补全：自动修复未闭合标签
    - 缓冲区限制：100KB上限，防止内存泄漏
    """

    RENDER_INTERVAL_MS = 300
    MAX_BUFFER_SIZE = 100_000
    BUFFER_TRIM_SIZE = 50_000
    MAX_RENDER_RETRIES = 3

    def __init__(self, parent: tk.Widget, theme: str = "light"):
        self.parent = parent
        self.theme = theme

        self._md = markdown.Markdown(extensions=[
            'tables',
            'fenced_code',
            'nl2br',
            'sane_lists',
        ])

        self._sanitizer = HtmlSanitizer()

        # 状态变量
        self._buffer = ""
        self._last_rendered_len = 0
        self._is_streaming = False
        self._pending_update = False
        self._render_retry_count = 0
        self._fallback_mode = False

        # 创建HTML框架
        self._html_frame = HtmlFrame(
            parent,
            messages_enabled=False,
            vertical_scrollbar=True,
            on_link_click=self._handle_link_click,
        )

        # 备用文本框（降级模式使用）
        self._fallback_text: Optional[tk.Widget] = None

        self._load_empty()

    def _handle_link_click(self, url: str) -> bool:
        """处理HTML中的链接点击事件"""
        if url.startswith("copy://"):
            import urllib.parse
            import pyperclip
            try:
                text = urllib.parse.unquote(url[7:])
                text = urllib.parse.unquote(text)
                pyperclip.copy(text)
            except Exception:
                pass
            return False
        return True

    def _get_css(self) -> str:
        """获取当前主题的CSS"""
        return DARK_CSS if self.theme == "dark" else LIGHT_CSS

    def _wrap_html(self, body_content: str) -> str:
        """包装完整的HTML文档"""
        css = self._get_css()
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        {css}
        ::-webkit-scrollbar {{
            width: 8px;
        }}
        ::-webkit-scrollbar-track {{
            background: {'#2d2d2d' if self.theme == 'dark' else '#f1f1f1'};
        }}
        ::-webkit-scrollbar-thumb {{
            background: {'#555' if self.theme == 'dark' else '#c1c1c1'};
            border-radius: 4px;
        }}
    </style>
</head>
<body>
{body_content}
</body>
</html>"""

    def _load_empty(self):
        """加载空白内容"""
        empty_html = self._wrap_html("<p style='color: #999;'>等待分析结果...</p>")
        self._html_frame.load_html(empty_html)

    # ------------------------------------------------------------------ #
    # 公共接口
    # ------------------------------------------------------------------ #

    def grid(self, **kwargs):
        """网格布局"""
        self._html_frame.grid(**kwargs)

    def grid_forget(self):
        """取消网格布局"""
        self._html_frame.grid_forget()

    def pack(self, **kwargs):
        """打包布局"""
        self._html_frame.pack(**kwargs)

    def pack_forget(self):
        """取消打包布局"""
        self._html_frame.pack_forget()

    def place(self, **kwargs):
        """位置布局"""
        self._html_frame.place(**kwargs)

    def place_forget(self):
        """取消位置布局"""
        self._html_frame.place_forget()

    def destroy(self):
        """销毁组件"""
        self._html_frame.destroy()

    def set_content(self, markdown_text: str):
        """设置Markdown内容并渲染为HTML"""
        if not markdown_text or not markdown_text.strip():
            self._load_empty()
            return

        self._exit_fallback_mode()

        try:
            self._md.reset()
            html_body = self._md.convert(markdown_text)
            html_body = self._sanitizer.sanitize(html_body)
            full_html = self._wrap_html(html_body)
            self._html_frame.load_html(full_html)
            self._buffer = markdown_text
        except Exception:
            self._buffer = markdown_text
            self._enter_fallback_mode("渲染异常，显示原始内容")

    def start_stream(self):
        """开始流式输出"""
        self._exit_fallback_mode()
        self._buffer = ""
        self._last_rendered_len = 0
        self._is_streaming = True
        self._pending_update = False
        self._render_retry_count = 0
        self._md.reset()

        loading_html = self._wrap_html(
            '<div style="text-align: center; padding: 20px; color: #667eea;">'
            '<span style="font-size: 24px;">&#x1F916;</span><br>'
            '<span style="font-size: 18px; font-weight: 600;">AI 正在思考中...</span>'
            '</div>'
        )
        self._html_frame.load_html(loading_html)

    def append_chunk(self, chunk: str):
        """追加流式文本块（公共接口）"""
        if not self._is_streaming:
            self.start_stream()

        if len(self._buffer) + len(chunk) > self.MAX_BUFFER_SIZE:
            self._buffer = self._buffer[-self.BUFFER_TRIM_SIZE:]

        self._buffer += chunk
        self._schedule_update()

    def finish_stream(self):
        """完成流式输出"""
        self._is_streaming = False
        if self._buffer and not self._fallback_mode:
            self._schedule_update()
        self._md.reset()

        try:
            self._html_frame.yview_moveto(1.0)
        except Exception:
            pass

    def clear(self):
        """清空内容"""
        self._buffer = ""
        self._md.reset()
        self._is_streaming = False
        self._pending_update = False
        self._render_retry_count = 0
        self._exit_fallback_mode()
        self._load_empty()

    def get_content(self) -> str:
        """获取当前内容（Markdown格式）"""
        return self._buffer

    def set_theme(self, theme: str):
        """切换主题"""
        if theme not in ("light", "dark"):
            return

        self.theme = theme

        if self._fallback_mode and self._fallback_text is not None:
            return

        if self._buffer:
            self._schedule_update()
        else:
            self._load_empty()

    def copy_to_clipboard(self) -> bool:
        """复制内容到剪贴板"""
        try:
            import pyperclip
            pyperclip.copy(self._buffer)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    # 内部渲染逻辑
    # ------------------------------------------------------------------ #

    def _schedule_update(self):
        """节流调度：确保同一时间只有一个渲染任务在队列中"""
        if self._pending_update or self._fallback_mode:
            return
        self._pending_update = True
        self._html_frame.after(self.RENDER_INTERVAL_MS, self._do_render)

    def _do_render(self):
        """实际渲染执行（带完整异常处理）"""
        try:
            self._render_retry_count = 0
            self._render_once()
        except Exception as e:
            self._handle_render_error(e)
        finally:
            self._pending_update = False

    def _render_once(self):
        """单次渲染逻辑"""
        if not self._buffer:
            return

        html_body = self._convert_markdown_safe(self._buffer)
        html_body = self._sanitizer.sanitize(html_body)
        full_html = self._wrap_html(html_body)

        self._html_frame.load_html(full_html)
        self._last_rendered_len = len(self._buffer)

        try:
            self._html_frame.yview_moveto(1.0)
        except Exception:
            pass

    def _convert_markdown_safe(self, text: str) -> str:
        """安全的Markdown转换"""
        try:
            self._md.reset()
            return self._md.convert(text)
        except Exception:
            return (text
                    .replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('\n', '<br>'))

    def _handle_render_error(self, error: Exception):
        """渲染错误处理"""
        self._render_retry_count += 1

        if self._render_retry_count < self.MAX_RENDER_RETRIES:
            self._html_frame.after(500, self._do_render)
            return

        self._enter_fallback_mode(str(error))

    def _enter_fallback_mode(self, error_msg: str):
        """进入降级模式：显示纯文本"""
        self._fallback_mode = True

        try:
            self._html_frame.grid_forget()
        except Exception:
            pass

        if self._fallback_text is None:
            import customtkinter as ctk
            self._fallback_text = ctk.CTkTextbox(
                self.parent,
                wrap="word",
                state="normal",
            )

        self._fallback_text.grid_forget()
        self._fallback_text.delete("1.0", "end")
        self._fallback_text.insert("1.0",
            f"[HTML渲染异常，显示原始内容]\n\n{self._buffer}"
        )
        self._fallback_text.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")

    def _exit_fallback_mode(self):
        """退出降级模式"""
        self._fallback_mode = False
        if self._fallback_text is not None:
            try:
                self._fallback_text.grid_forget()
            except Exception:
                pass


class HtmlResultWidget(HtmlRenderer):
    """HTML结果显示组件 - 带工具栏"""

    def __init__(self, parent: tk.Widget, theme: str = "light",
                 on_copy=None, on_clear=None, on_export=None):
        super().__init__(parent, theme)
        self._on_copy = on_copy
        self._on_clear = on_clear
        self._on_export = on_export
