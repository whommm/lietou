"""HTML渲染器模块。"""

from typing import Dict, Optional
import tkinter as tk

import customtkinter as ctk
import markdown
from tkinterweb import HtmlFrame

from ..utils.html_sanitizer import HtmlSanitizer
from .themes import DARK_CSS, LIGHT_CSS

LOADING_ANIMATION_HTML = """
<div class="loading-container">
    <div class="pulse-ring"></div>
    <div class="pulse-ring pulse-ring-delay"></div>
    <div class="brain-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" fill="currentColor"/>
        </svg>
    </div>
    <div class="loading-text">
        <span class="thinking-dot">AI</span>
        <span class="thinking-dot" style="animation-delay:0.1s">正在</span>
        <span class="thinking-dot" style="animation-delay:0.2s">深度</span>
        <span class="thinking-dot" style="animation-delay:0.3s">分析</span>
    </div>
    <div class="loading-steps">
        <div class="step-item" id="step-1">
            <div class="step-dot"></div>
            <span class="step-label">解析岗位信息</span>
        </div>
        <div class="step-item" id="step-2">
            <div class="step-dot"></div>
            <span class="step-label">行业背景匹配</span>
        </div>
        <div class="step-item" id="step-3">
            <div class="step-dot"></div>
            <span class="step-label">提取核心门槛</span>
        </div>
        <div class="step-item" id="step-4">
            <div class="step-dot"></div>
            <span class="step-label">生成搜索策略</span>
        </div>
    </div>
    <div class="loading-shimmer-bar">
        <div class="shimmer-fill"></div>
    </div>
</div>
<style>
    .loading-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 400px;
        padding: 40px 20px;
        position: relative;
    }
    .pulse-ring {
        position: absolute;
        width: 120px;
        height: 120px;
        border-radius: 50%;
        border: 3px solid var(--pulse-color, #667eea);
        animation: pulse-expand 2s ease-out infinite;
        opacity: 0;
        pointer-events: none;
    }
    .pulse-ring-delay {
        animation-delay: 1s;
    }
    @keyframes pulse-expand {
        0% { transform: scale(0.5); opacity: 0.6; }
        100% { transform: scale(2); opacity: 0; }
    }
    .brain-icon {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        animation: float-bounce 2s ease-in-out infinite;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
        position: relative;
        z-index: 1;
    }
    @keyframes float-bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
    .brain-icon svg {
        animation: rotate-slow 8s linear infinite;
    }
    @keyframes rotate-slow {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    .loading-text {
        margin-top: 28px;
        font-size: 20px;
        font-weight: 600;
        letter-spacing: 2px;
    }
    .thinking-dot {
        display: inline-block;
        animation: fade-slide 1.8s ease-in-out infinite;
        opacity: 0.4;
    }
    @keyframes fade-slide {
        0%, 100% { opacity: 0.4; transform: translateY(0); }
        50% { opacity: 1; transform: translateY(-2px); }
    }
    .loading-steps {
        margin-top: 36px;
        display: flex;
        flex-direction: column;
        gap: 12px;
        width: 100%;
        max-width: 260px;
    }
    .step-item {
        display: flex;
        align-items: center;
        gap: 12px;
        animation: step-fade-in 0.5s ease forwards;
        opacity: 0;
    }
    .step-item:nth-child(1) { animation-delay: 2s; }
    .step-item:nth-child(2) { animation-delay: 8s; }
    .step-item:nth-child(3) { animation-delay: 16s; }
    .step-item:nth-child(4) { animation-delay: 24s; }
    @keyframes step-fade-in {
        to { opacity: 1; }
    }
    .step-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #667eea;
        flex-shrink: 0;
        animation: dot-pulse 1.5s ease-in-out infinite;
    }
    .step-item:nth-child(2) .step-dot { animation-delay: 0.2s; }
    .step-item:nth-child(3) .step-dot { animation-delay: 0.4s; }
    .step-item:nth-child(4) .step-dot { animation-delay: 0.6s; }
    @keyframes dot-pulse {
        0%, 100% { opacity: 0.4; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.3); }
    }
    .step-label {
        font-size: 13px;
        color: #888;
        font-weight: 500;
    }
    .loading-shimmer-bar {
        margin-top: 40px;
        width: 100%;
        max-width: 320px;
        height: 4px;
        background: rgba(102, 126, 234, 0.1);
        border-radius: 4px;
        overflow: hidden;
    }
    .shimmer-fill {
        height: 100%;
        width: 40%;
        background: linear-gradient(90deg, transparent, #667eea, transparent);
        border-radius: 4px;
        animation: shimmer-slide 2s ease-in-out infinite;
    }
    @keyframes shimmer-slide {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(350%); }
    }
</style>
"""


class HtmlRenderer:
    """HTML渲染器，默认按 HTML 片段渲染，兼容 Markdown 兜底。"""

    def __init__(self, parent: tk.Widget, theme: str = "light", **grid_kwargs):
        self.parent = parent
        self.theme = theme
        self._initial_grid_kwargs = grid_kwargs
        self._layout_manager: Optional[str] = None
        self._layout_kwargs: Dict[str, object] = {}

        self._md = markdown.Markdown(
            extensions=["tables", "fenced_code", "nl2br", "sane_lists"]
        )
        self._sanitizer = HtmlSanitizer()
        self._buffer = ""
        self._fallback_mode = False

        self._html_frame = HtmlFrame(
            parent,
            messages_enabled=False,
            vertical_scrollbar=True,
            on_link_click=self._handle_link_click,
        )
        self._fallback_text: Optional[ctk.CTkTextbox] = None

        self._load_empty()

    def _handle_link_click(self, url: str) -> bool:
        """处理HTML中的链接点击事件。"""
        if url.startswith("copy://"):
            import pyperclip
            import urllib.parse

            try:
                text = urllib.parse.unquote(url[7:])
                pyperclip.copy(text)
            except Exception:
                pass
            return False
        return True

    def _get_css(self) -> str:
        """获取当前主题的CSS。"""
        return DARK_CSS if self.theme == "dark" else LIGHT_CSS

    def _wrap_html(self, body_content: str) -> str:
        """包装完整HTML文档。"""
        css = self._get_css()
        scrollbar_track = "#2d2d2d" if self.theme == "dark" else "#f1f1f1"
        scrollbar_thumb = "#555" if self.theme == "dark" else "#c1c1c1"
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
            background: {scrollbar_track};
        }}
        ::-webkit-scrollbar-thumb {{
            background: {scrollbar_thumb};
            border-radius: 4px;
        }}
    </style>
</head>
<body>
{body_content}
</body>
</html>"""

    def _load_empty(self):
        """加载空白占位。"""
        empty_html = self._wrap_html("<p style='color: #999;'>等待结果输出...</p>")
        self._html_frame.load_html(empty_html)

    def _looks_like_html(self, text: str) -> bool:
        """判断内容是否更像HTML片段。"""
        lowered = text.lstrip().lower()
        html_markers = (
            "<div",
            "<p",
            "<h1",
            "<h2",
            "<h3",
            "<ul",
            "<ol",
            "<table",
            "<!doctype",
            "<html",
        )
        return lowered.startswith(html_markers) or "</" in lowered

    def _render_body(self, text: str) -> str:
        """将输入内容转换为最终HTML body。"""
        if self._looks_like_html(text):
            return self._sanitizer.sanitize(text)

        self._md.reset()
        return self._sanitizer.sanitize(self._md.convert(text))

    def _remember_layout(self, manager: str, kwargs: Dict[str, object]):
        """记录最近一次有效布局方式。"""
        self._layout_manager = manager
        self._layout_kwargs = dict(kwargs)

    def _apply_layout(self, widget):
        """将最近一次布局方式应用到指定组件。"""
        manager = self._layout_manager
        kwargs = self._layout_kwargs or self._initial_grid_kwargs

        if manager is None and not kwargs:
            return

        if manager == "pack":
            widget.pack(**kwargs)
        elif manager == "place":
            widget.place(**kwargs)
        else:
            widget.grid(**kwargs)

    def _forget_layout(self, widget):
        """根据当前布局管理器隐藏组件。"""
        manager = self._layout_manager
        if manager == "pack":
            widget.pack_forget()
        elif manager == "place":
            widget.place_forget()
        else:
            widget.grid_forget()

    def grid(self, **kwargs):
        """网格布局。"""
        self._remember_layout("grid", kwargs)
        self._html_frame.grid(**kwargs)

    def grid_forget(self):
        """取消网格布局。"""
        self._html_frame.grid_forget()
        if self._fallback_text is not None:
            self._fallback_text.grid_forget()

    def pack(self, **kwargs):
        """打包布局。"""
        self._remember_layout("pack", kwargs)
        self._html_frame.pack(**kwargs)

    def pack_forget(self):
        """取消打包布局。"""
        self._html_frame.pack_forget()
        if self._fallback_text is not None:
            self._fallback_text.pack_forget()

    def place(self, **kwargs):
        """位置布局。"""
        self._remember_layout("place", kwargs)
        self._html_frame.place(**kwargs)

    def place_forget(self):
        """取消位置布局。"""
        self._html_frame.place_forget()
        if self._fallback_text is not None:
            self._fallback_text.place_forget()

    def destroy(self):
        """销毁组件。"""
        if self._fallback_text is not None:
            self._fallback_text.destroy()
        self._html_frame.destroy()

    def set_content(self, text: str):
        """设置结果内容并渲染。"""
        if not text or not text.strip():
            self.clear()
            return

        self._buffer = text
        self._exit_fallback_mode()

        try:
            html_body = self._render_body(text)
            self._html_frame.load_html(self._wrap_html(html_body))
        except Exception:
            self._enter_fallback_mode()

    def show_loading(self):
        """显示等待动画。"""
        self._buffer = ""
        self._exit_fallback_mode()
        self._html_frame.load_html(self._wrap_html(LOADING_ANIMATION_HTML))

    def clear(self):
        """清空内容。"""
        self._buffer = ""
        self._exit_fallback_mode()
        self._load_empty()

    def get_content(self) -> str:
        """获取当前内容。"""
        return self._buffer

    def set_theme(self, theme: str):
        """切换主题。"""
        if theme not in ("light", "dark"):
            return

        self.theme = theme
        if self._fallback_mode:
            self._enter_fallback_mode()
        elif self._buffer:
            self.set_content(self._buffer)
        else:
            self._load_empty()

    def copy_to_clipboard(self) -> bool:
        """复制当前内容。"""
        try:
            import pyperclip

            pyperclip.copy(self._buffer)
            return True
        except Exception:
            return False

    def _enter_fallback_mode(self):
        """进入纯文本降级模式。"""
        self._fallback_mode = True
        self._forget_layout(self._html_frame)

        if self._fallback_text is None:
            self._fallback_text = ctk.CTkTextbox(self.parent, wrap="word")

        self._fallback_text.configure(state="normal")
        self._fallback_text.delete("1.0", "end")
        self._fallback_text.insert(
            "1.0", "[HTML 渲染异常，已切换为原始文本显示]\n\n{}".format(self._buffer)
        )
        self._fallback_text.configure(state="disabled")
        self._forget_layout(self._fallback_text)
        self._apply_layout(self._fallback_text)

    def _exit_fallback_mode(self):
        """退出纯文本降级模式。"""
        self._fallback_mode = False
        if self._fallback_text is not None:
            self._forget_layout(self._fallback_text)
        self._apply_layout(self._html_frame)
