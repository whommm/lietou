"""HTML渲染器模块 - 将Markdown转换为精美HTML显示"""

import markdown
import tkinter as tk
from tkinterweb import HtmlFrame
from typing import Optional
from .themes import LIGHT_CSS, DARK_CSS


class HtmlRenderer:
    """HTML渲染器 - 支持Markdown转换和流式输出"""

    def __init__(self, parent: tk.Widget, theme: str = "light"):
        self.parent = parent
        self.theme = theme

        # Markdown转换器
        self._md = markdown.Markdown(extensions=[
            'tables',
            'fenced_code',
            'nl2br',
            'sane_lists',
        ])

        # 流式输出缓冲区
        self._buffer = ""
        self._last_rendered_len = 0
        self._is_streaming = False
        self._initialized = False

        # 创建HTML框架
        self._html_frame = HtmlFrame(
            parent,
            messages_enabled=False,
            vertical_scrollbar=True,
            on_link_click=self._handle_link_click,
        )

        # 加载初始内容
        self._load_empty()

    def _handle_link_click(self, url: str) -> bool:
        """处理HTML中的链接点击事件"""
        if url.startswith("copy://"):
            import urllib.parse
            import pyperclip
            try:
                text = urllib.parse.unquote(url[7:])
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

        self._md.reset()
        html_body = self._md.convert(markdown_text)
        full_html = self._wrap_html(html_body)
        self._html_frame.load_html(full_html)

    def start_stream(self):
        """开始流式输出"""
        self._buffer = ""
        self._last_rendered_len = 0
        self._is_streaming = True
        self._initialized = False
        self._md.reset()

        # 显示加载状态
        loading_html = self._wrap_html(
            '<div style="text-align: center; padding: 20px; color: #667eea;">'
            '<span style="font-size: 24px;">&#x1F916;</span><br>'
            '<span style="font-size: 18px; font-weight: 600;">AI 正在思考中...</span>'
            '</div>'
        )
        self._html_frame.load_html(loading_html)

    def append_chunk(self, chunk: str):
        """追加流式文本块"""
        if not self._is_streaming:
            self.start_stream()

        self._buffer += chunk
        self._update_stream_display()

    def _update_stream_display(self):
        """更新流式显示内容"""
        if not self._buffer:
            return

        # 转换当前缓冲区内容
        try:
            self._md.reset()
            html_body = self._md.convert(self._buffer)
        except Exception:
            escaped = self._buffer.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
            html_body = escaped

        self._last_rendered_len = len(self._buffer)

        if not self._initialized:
            full_html = self._wrap_html('<div id="stream-content"></div>')
            self._html_frame.load_html(full_html)
            self._initialized = True

        # 使用DOM API更新内容
        try:
            content_elem = self._html_frame.document.getElementById('stream-content')
            if content_elem:
                content_elem.innerHTML = html_body
        except Exception:
            full_html = self._wrap_html(html_body)
            self._html_frame.load_html(full_html)

        # 自动滚动到底部
        try:
            self._html_frame.yview_moveto(1.0)
        except Exception:
            pass

    def finish_stream(self):
        """完成流式输出"""
        self._is_streaming = False
        self._update_stream_display()
        self._md.reset()

        # 最终滚动到底部
        try:
            self._html_frame.yview_moveto(1.0)
        except Exception:
            pass

    def clear(self):
        """清空内容"""
        self._buffer = ""
        self._md.reset()
        self._is_streaming = False
        self._load_empty()

    def get_content(self) -> str:
        """获取当前内容（Markdown格式）"""
        return self._buffer

    def set_theme(self, theme: str):
        """切换主题"""
        if theme not in ("light", "dark"):
            return

        self.theme = theme

        # 重新渲染当前内容
        if self._buffer:
            self._update_stream_display()
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


class HtmlResultWidget(HtmlRenderer):
    """HTML结果显示组件 - 带工具栏"""

    def __init__(self, parent: tk.Widget, theme: str = "light",
                 on_copy=None, on_clear=None, on_export=None):
        super().__init__(parent, theme)
        self._on_copy = on_copy
        self._on_clear = on_clear
        self._on_export = on_export
