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
        self._last_rendered_len = 0
        self._is_streaming = False
        self._initialized = False
        self._user_scrolled = False  # 用户是否手动滚动过

        # 创建HTML框架
        self._html_frame = HtmlFrame(
            parent,
            messages_enabled=False,
            vertical_scrollbar=True,
            on_link_click=self._handle_link_click,
        )

        # 绑定鼠标滚轮事件检测用户滚动
        self._html_frame.bind('<MouseWheel>', self._on_user_scroll)

        # 加载初始空白内容
        self._load_empty()

    def _handle_link_click(self, url: str) -> bool:
        """处理HTML中的链接点击事件"""
        if url.startswith("copy://"):
            import urllib.parse
            import pyperclip
            from tkinter import messagebox
            try:
                # 解析URL编码的文本
                text = urllib.parse.unquote(url[7:])
                pyperclip.copy(text)
                # 可选：如果你想给用户更明显的反馈，可以取消下面这行的注释
                # messagebox.showinfo("成功", f"已复制: {text}")
            except Exception:
                pass
            return False  # 返回False阻止默认跳转
        return True  # 其他链接允许默认处理

    def _on_user_scroll(self, event=None):
        """用户滚动时的回调"""
        # 检测是否滚回底部
        try:
            pos = self._html_frame.yview()
            if pos and len(pos) == 2 and pos[1] >= 0.98:
                # 用户滚回底部，恢复自动跟随
                self._user_scrolled = False
            else:
                self._user_scrolled = True
        except Exception:
            self._user_scrolled = True

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
        /* overflow-anchor 自动保持滚动位置 */
        html {{
            overflow-anchor: none;
        }}
        body {{
            overflow-anchor: none;
        }}
        #content-anchor {{
            overflow-anchor: auto;
            width: 100%;
        }}
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
<div id="content-anchor"></div>
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
        self._last_rendered_len = 0
        self._is_streaming = True
        self._initialized = False
        self._user_scrolled = False
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
        if not self._is_streaming:
            self.start_stream()

        self._buffer += chunk

        # 增加更新间隔到1500字符，减少重新加载频率
        if len(self._buffer) - self._last_rendered_len > 1500:
            self._update_stream_display()

    def _update_stream_display(self):
        """更新流式显示内容 - 使用DOM innerHTML"""
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
            # 首次加载完整页面，包含内容容器
            full_html = self._wrap_html('<div id="stream-content"></div>')
            self._html_frame.load_html(full_html)
            self._initialized = True

        # 使用DOM API更新内容容器
        try:
            content_elem = self._html_frame.document.getElementById('stream-content')
            if content_elem:
                content_elem.innerHTML = html_body
        except Exception:
            # DOM更新失败，回退到重新加载
            full_html = self._wrap_html(html_body)
            self._html_frame.load_html(full_html)

        # 智能滚动：用户没手动滚动过则跟随底部
        if not self._user_scrolled:
            self.parent.after(50, lambda: self._html_frame.yview_moveto(1.0))

    def finish_stream(self):
        """完成流式输出，进行最终渲染"""
        self._is_streaming = False
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
