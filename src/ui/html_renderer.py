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
        self._auto_scroll = True  # 是否自动滚动到底部
        self._scroll_check_id = None

        # 创建主容器
        self._container = tk.Frame(parent)
        self._container.grid_columnconfigure(0, weight=1)
        self._container.grid_rowconfigure(0, weight=1)

        # 创建HTML框架
        self._html_frame = HtmlFrame(
            self._container,
            messages_enabled=False,
            vertical_scrollbar=True,
            on_link_click=self._handle_link_click,
        )
        self._html_frame.grid(row=0, column=0, sticky="nsew")

        # 创建浮动按钮（放在容器右下角）
        self._scroll_down_btn = tk.Button(
            self._container,
            text="⬇",
            font=("Arial", 16),
            bg="#4CAF50" if theme == "light" else "#667eea",
            fg="white",
            relief="flat",
            cursor="hand2",
            command=self._on_scroll_down_click,
            width=3,
            height=1
        )
        # 初始隐藏
        self._btn_visible = False

        # 绑定滚动事件到HtmlFrame及其子组件
        self._bind_scroll_events()

        # 加载初始内容
        self._load_empty()

    def _bind_scroll_events(self):
        """绑定滚动事件"""
        # 只绑定到HtmlFrame本身
        self._html_frame.bind('<MouseWheel>', self._on_scroll)
        self._html_frame.bind('<Button-4>', self._on_scroll_up)
        self._html_frame.bind('<Button-5>', self._on_scroll_down)

    def _on_scroll(self, event=None):
        """Windows滚轮事件"""
        if event and event.delta < 0:
            # 向下滚动
            self._on_user_scroll_down()
        elif event and event.delta > 0:
            # 向上滚动
            self._on_user_scroll_up()

    def _on_scroll_up(self, event=None):
        """Linux向上滚轮"""
        self._on_user_scroll_up()

    def _on_scroll_down(self, event=None):
        """Linux向下滚轮"""
        self._on_user_scroll_down()

    def _on_user_scroll_up(self):
        """用户向上滚动"""
        self._auto_scroll = False
        self._show_scroll_button()

    def _on_user_scroll_down(self):
        """用户向下滚动"""
        # 延迟检查是否已到底部
        self._container.after(100, self._check_if_at_bottom)

    def _check_if_at_bottom(self):
        """检查是否已滚动到底部"""
        try:
            pos = self._html_frame.yview()
            if pos and len(pos) == 2 and pos[1] >= 0.98:
                # 已到底部，恢复自动滚动
                self._auto_scroll = True
                self._hide_scroll_button()
            else:
                # 未到底部
                self._auto_scroll = False
                self._show_scroll_button()
        except Exception:
            pass

    def _on_scroll_down_click(self):
        """点击滚动到底部按钮"""
        self._scroll_to_bottom()
        self._auto_scroll = True
        self._hide_scroll_button()

    def _show_scroll_button(self):
        """显示滚动按钮"""
        if not self._btn_visible:
            self._scroll_down_btn.place(relx=1.0, rely=1.0, x=-20, y=-20, anchor="se")
            self._btn_visible = True

    def _hide_scroll_button(self):
        """隐藏滚动按钮"""
        if self._btn_visible:
            self._scroll_down_btn.place_forget()
            self._btn_visible = False

    def _scroll_to_bottom(self):
        """滚动到底部"""
        try:
            self._html_frame.yview_moveto(1.0)
        except Exception:
            pass

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
        html, body {{
            overflow-anchor: auto;
        }}
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
        self._container.grid(**kwargs)

    def grid_forget(self):
        """取消网格布局"""
        self._container.grid_forget()

    def pack(self, **kwargs):
        """打包布局"""
        self._container.pack(**kwargs)

    def pack_forget(self):
        """取消打包布局"""
        self._container.pack_forget()

    def place(self, **kwargs):
        """位置布局"""
        self._container.place(**kwargs)

    def place_forget(self):
        """取消位置布局"""
        self._container.place_forget()

    def destroy(self):
        """销毁组件"""
        if self._scroll_check_id:
            self._container.after_cancel(self._scroll_check_id)
        self._container.destroy()

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
        self._auto_scroll = True
        self._md.reset()

        # 隐藏按钮
        self._hide_scroll_button()

        # 显示加载状态
        loading_html = self._wrap_html(
            '<div style="text-align: center; padding: 20px; color: #667eea;">'
            '<span style="font-size: 24px;">&#x1F916;</span><br>'
            '<span style="font-size: 18px; font-weight: 600;">AI 正在思考中...</span>'
            '</div>'
        )
        self._html_frame.load_html(loading_html)

        # 启动滚动检查
        self._start_scroll_check()

    def _start_scroll_check(self):
        """启动定期滚动检查"""
        if self._scroll_check_id:
            self._container.after_cancel(self._scroll_check_id)
        self._scroll_check_id = self._container.after(300, self._periodic_scroll_check)

    def _periodic_scroll_check(self):
        """定期检查滚动位置"""
        if self._is_streaming:
            # 检查当前滚动位置
            try:
                pos = self._html_frame.yview()
                if pos and len(pos) == 2:
                    # 如果不在底部且自动滚动开启，说明用户向上滚动了
                    if pos[1] < 0.95 and self._auto_scroll:
                        self._auto_scroll = False
                        self._show_scroll_button()
                    # 如果在底部，恢复自动滚动
                    elif pos[1] >= 0.98:
                        self._auto_scroll = True
                        self._hide_scroll_button()
            except Exception:
                pass

            # 继续检查
            self._scroll_check_id = self._container.after(300, self._periodic_scroll_check)

    def append_chunk(self, chunk: str):
        """追加流式文本块"""
        if not self._is_streaming:
            self.start_stream()

        self._buffer += chunk

        # 增加更新间隔，减少重新加载频率
        if len(self._buffer) - self._last_rendered_len > 1500:
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
        if self._auto_scroll:
            self._container.after(50, self._scroll_to_bottom)

    def finish_stream(self):
        """完成流式输出"""
        self._is_streaming = False

        # 停止滚动检查
        if self._scroll_check_id:
            self._container.after_cancel(self._scroll_check_id)
            self._scroll_check_id = None

        self._update_stream_display()
        self._md.reset()

        # 最终滚动到底部
        if self._auto_scroll:
            self._scroll_to_bottom()

    def clear(self):
        """清空内容"""
        self._buffer = ""
        self._md.reset()
        self._is_streaming = False
        self._auto_scroll = True

        # 停止滚动检查
        if self._scroll_check_id:
            self._container.after_cancel(self._scroll_check_id)
            self._scroll_check_id = None

        self._hide_scroll_button()
        self._load_empty()

    def get_content(self) -> str:
        """获取当前内容（Markdown格式）"""
        return self._buffer

    def set_theme(self, theme: str):
        """切换主题"""
        if theme not in ("light", "dark"):
            return

        self.theme = theme

        # 更新按钮颜色
        self._scroll_down_btn.configure(
            bg="#4CAF50" if theme == "light" else "#667eea"
        )

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
