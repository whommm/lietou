"""HTML渲染器模块 - 将Markdown转换为精美HTML显示"""

import markdown
import tkinter as tk
from tkinterweb import HtmlFrame
from typing import Optional
from .themes import LIGHT_CSS, DARK_CSS


class HtmlRenderer:
    """HTML渲染器 - 支持Markdown转换和流式输出"""

    def __init__(self, parent: tk.Widget, theme: str = "light"):
        """
        初始化HTML渲染器

        Args:
            parent: 父容器
            theme: 主题名称 ("light" 或 "dark")
        """
        self.parent = parent
        self.theme = theme

        # Markdown转换器
        self._md = markdown.Markdown(extensions=[
            'tables',        # 表格支持
            'fenced_code',   # 代码块支持
            'nl2br',         # 换行转换
            'sane_lists',    # 更好的列表支持
        ])

        # 流式输出缓冲区
        self._buffer = ""

        # 创建HTML框架
        self._html_frame = HtmlFrame(
            parent,
            messages_enabled=False,  # 禁用控制台消息
            vertical_scrollbar=True,
        )

        # 加载初始空白内容
        self._load_empty()

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
        /* 滚动条样式 */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        ::-webkit-scrollbar-track {{
            background: {'#2d2d2d' if self.theme == 'dark' else '#f1f1f1'};
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb {{
            background: {'#555' if self.theme == 'dark' else '#c1c1c1'};
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: {'#777' if self.theme == 'dark' else '#a1a1a1'};
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
        """
        设置Markdown内容并渲染为HTML

        Args:
            markdown_text: Markdown格式的文本
        """
        if not markdown_text or not markdown_text.strip():
            self._load_empty()
            return

        # 转换Markdown为HTML
        self._md.reset()
        html_body = self._md.convert(markdown_text)

        # 加载完整的HTML
        full_html = self._wrap_html(html_body)
        self._html_frame.load_html(full_html)

    def start_stream(self):
        """开始流式输出"""
        self._buffer = ""
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
        """
        追加流式文本块

        Args:
            chunk: 新的文本片段
        """
        self._buffer += chunk

        # 更频繁地更新显示
        if len(self._buffer) % 200 == 0 or len(chunk) > 30:
            self._update_stream_display()

    def _update_stream_display(self):
        """更新流式显示内容"""
        if not self._buffer:
            return

        # 转换当前缓冲区内容
        try:
            self._md.reset()
            html_body = self._md.convert(self._buffer)
            full_html = self._wrap_html(html_body)
            self._html_frame.load_html(full_html)
        except Exception:
            # 转换失败时显示纯文本
            escaped = self._buffer.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
            plain_html = self._wrap_html(escaped)
            self._html_frame.load_html(plain_html)

    def finish_stream(self):
        """完成流式输出，进行最终渲染"""
        self._update_stream_display()
        self._md.reset()

    def clear(self):
        """清空内容"""
        self._buffer = ""
        self._md.reset()
        self._load_empty()

    def get_content(self) -> str:
        """获取当前内容（Markdown格式）"""
        return self._buffer

    def set_theme(self, theme: str):
        """
        切换主题

        Args:
            theme: 主题名称 ("light" 或 "dark")
        """
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
    """
    HTML结果显示组件 - 带工具栏
    用于替换原有的CTkTextbox，提供更丰富的内容显示
    """

    def __init__(self, parent: tk.Widget, theme: str = "light",
                 on_copy=None, on_clear=None, on_export=None):
        """
        初始化HTML结果组件

        Args:
            parent: 父容器
            theme: 主题名称
            on_copy: 复制回调
            on_clear: 清空回调
            on_export: 导出回调
        """
        # 先初始化基类
        super().__init__(parent, theme)

        self._on_copy = on_copy
        self._on_clear = on_clear
        self._on_export = on_export
