"""主窗口 UI 模块"""

import customtkinter as ctk
from tkinter import messagebox
import threading
from typing import Optional

from ..core.config import ConfigManager
from ..core.history import HistoryManager
from ..core.llm_client import LLMClient, LLMClientError, AuthError, NetworkError, TimeoutError
from ..utils.helpers import copy_to_clipboard, validate_url, validate_api_key
from .card_widget import CardContainer
from .history_widget import HistoryPanel
from .result_parser import ResultParser


class MainWindow(ctk.CTk):
    """主窗口类"""

    def __init__(self):
        super().__init__()

        # 配置管理器
        self.config_manager = ConfigManager()

        # 历史记录管理器
        self.history_manager = HistoryManager()

        # 窗口基本设置
        self.title("智能岗位分析与寻访助手")
        self.geometry("1300x900")
        self.minsize(1000, 700)

        # 设置主题
        ctk.set_appearance_mode(self.config_manager.config.theme)
        ctk.set_default_color_theme("blue")

        # 分析线程
        self._analysis_thread: Optional[threading.Thread] = None
        self._stop_flag = False

        # 原始结果文本
        self._raw_result = ""

        # 当前分析的JD文本（用于保存历史记录）
        self._current_jd = ""

        # 是否已完成分析（用于控制卡片视图可用性）
        self._analysis_done = False

        # 构建界面
        self._build_ui()

        # 加载配置到界面
        self._load_config_to_ui()

    def _build_ui(self):
        """构建用户界面"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_config_frame()
        self._build_main_content()
        self._build_status_bar()

    def _build_config_frame(self):
        """构建顶部配置区"""
        config_frame = ctk.CTkFrame(self)
        config_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        config_frame.grid_columnconfigure(1, weight=1)
        config_frame.grid_columnconfigure(3, weight=1)

        # API Base URL
        ctk.CTkLabel(config_frame, text="API 地址:").grid(row=0, column=0, padx=(10, 5), pady=10, sticky="w")
        self.url_entry = ctk.CTkEntry(config_frame, placeholder_text="https://api.deepseek.com/v1")
        self.url_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        # API Key
        ctk.CTkLabel(config_frame, text="API Key:").grid(row=0, column=2, padx=(20, 5), pady=10, sticky="w")
        self.key_entry = ctk.CTkEntry(config_frame, placeholder_text="sk-xxx...", show="*")
        self.key_entry.grid(row=0, column=3, padx=5, pady=10, sticky="ew")

        # 模型名称
        ctk.CTkLabel(config_frame, text="模型:").grid(row=0, column=4, padx=(20, 5), pady=10, sticky="w")
        self.model_entry = ctk.CTkEntry(config_frame, placeholder_text="deepseek-chat", width=220)
        self.model_entry.grid(row=0, column=5, padx=5, pady=10)

        # 保存配置按钮
        self.save_btn = ctk.CTkButton(config_frame, text="保存配置", width=100, command=self._on_save_config)
        self.save_btn.grid(row=0, column=6, padx=(20, 10), pady=10)

        # 主题切换
        self.theme_switch = ctk.CTkSwitch(config_frame, text="深色模式", command=self._on_theme_toggle)
        self.theme_switch.grid(row=0, column=7, padx=(10, 5), pady=10)
        if self.config_manager.config.theme == "dark":
            self.theme_switch.select()

        # 流式输出开关
        self.stream_switch = ctk.CTkSwitch(config_frame, text="流式输出", command=self._on_stream_toggle)
        self.stream_switch.grid(row=0, column=8, padx=(5, 5), pady=10)
        if self.config_manager.config.stream_mode:
            self.stream_switch.select()

        # 历史记录按钮
        self.history_btn = ctk.CTkButton(
            config_frame,
            text="📋 历史",
            width=80,
            height=28,
            command=self._on_history_click
        )
        self.history_btn.grid(row=0, column=9, padx=(5, 10), pady=10)

    def _build_main_content(self):
        """构建主内容区"""
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=2)  # 输入区占 2
        main_frame.grid_columnconfigure(1, weight=3)  # 输出区占 3
        main_frame.grid_rowconfigure(0, weight=1)

        self._build_input_panel(main_frame)
        self._build_output_panel(main_frame)

    def _build_input_panel(self, parent):
        """构建左侧输入面板"""
        input_frame = ctk.CTkFrame(parent)
        input_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        input_frame.grid_columnconfigure(0, weight=1)
        input_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(input_frame, text="原始岗位描述 (JD)", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="w"
        )

        self.jd_textbox = ctk.CTkTextbox(input_frame, wrap="word")
        self.jd_textbox.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)

        self.clear_btn = ctk.CTkButton(btn_frame, text="清空", width=80, fg_color="gray", command=self._on_clear_input)
        self.clear_btn.grid(row=0, column=0, padx=5, sticky="w")

        self.analyze_btn = ctk.CTkButton(btn_frame, text="开始分析", width=150, command=self._on_analyze)
        self.analyze_btn.grid(row=0, column=1, padx=5, sticky="e")

    def _build_output_panel(self, parent):
        """构建右侧输出面板"""
        output_frame = ctk.CTkFrame(parent)
        output_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        output_frame.grid_columnconfigure(0, weight=1)
        output_frame.grid_rowconfigure(1, weight=1)

        # 标题栏
        header_frame = ctk.CTkFrame(output_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header_frame, text="分析结果", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")

        # 复制全部按钮
        self.copy_all_btn = ctk.CTkButton(
            header_frame,
            text="复制全部",
            width=80,
            height=28,
            command=self._on_copy_all
        )
        self.copy_all_btn.pack(side="right", padx=5)

        # 清空按钮
        self.clear_result_btn = ctk.CTkButton(
            header_frame,
            text="清空",
            width=60,
            height=28,
            fg_color="gray",
            command=self._on_clear_result
        )
        self.clear_result_btn.pack(side="right", padx=5)

        # 显示模式切换（默认原文模式）
        self.view_mode = ctk.StringVar(value="raw")
        mode_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        mode_frame.pack(side="right", padx=10)

        self.raw_radio = ctk.CTkRadioButton(
            mode_frame,
            text="原文",
            variable=self.view_mode,
            value="raw",
            command=self._on_view_mode_change
        )
        self.raw_radio.pack(side="left", padx=5)

        self.card_radio = ctk.CTkRadioButton(
            mode_frame,
            text="卡片",
            variable=self.view_mode,
            value="card",
            command=self._on_view_mode_change
        )
        self.card_radio.pack(side="left", padx=5)

        self.history_radio = ctk.CTkRadioButton(
            mode_frame,
            text="历史",
            variable=self.view_mode,
            value="history",
            command=self._on_view_mode_change
        )
        self.history_radio.pack(side="left", padx=5)

        # 原文文本框（默认显示）
        self.raw_textbox = ctk.CTkTextbox(output_frame, wrap="word", state="disabled")
        self.raw_textbox.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")

        # 卡片容器（延迟创建，切换时才构建）
        self.card_container = None
        self._card_frame_placeholder = output_frame  # 保存父容器引用

        # 历史面板（延迟创建）
        self.history_panel = None

    def _on_view_mode_change(self):
        """切换显示模式"""
        mode = self.view_mode.get()

        # 隐藏所有视图
        self.raw_textbox.grid_forget()
        if self.card_container:
            self.card_container.grid_forget()
        if self.history_panel:
            self.history_panel.grid_forget()

        if mode == "raw":
            # 切换到原文模式
            self.raw_textbox.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
        elif mode == "card":
            # 切换到卡片模式
            if not self._analysis_done:
                messagebox.showinfo("提示", "请等待分析完成后再切换到卡片视图")
                self.view_mode.set("raw")
                self._on_view_mode_change()
                return

            # 首次切换时创建卡片容器并渲染
            if self.card_container is None:
                self.card_container = CardContainer(self._card_frame_placeholder)
                self._render_cards()

            self.card_container.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
        elif mode == "history":
            # 切换到历史模式
            if self.history_panel is None:
                self.history_panel = HistoryPanel(
                    self._card_frame_placeholder,
                    history_manager=self.history_manager,
                    on_load_record=self._on_load_history
                )
            else:
                self.history_panel.refresh()
            self.history_panel.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")

    def _render_cards(self):
        """渲染卡片内容（仅在分析完成后调用一次）"""
        if not self._raw_result:
            return

        # 解析原始文本
        parsed = ResultParser.parse(self._raw_result)

        # 更新各模块卡片
        if parsed.module1:
            self.card_container.update_module(1, parsed.module1)
        if parsed.module2:
            self.card_container.update_module(2, parsed.module2)
        if parsed.module3:
            self.card_container.update_module(3, parsed.module3)
        if parsed.module4:
            self.card_container.update_module(4, parsed.module4)

    def _build_status_bar(self):
        """构建底部状态栏"""
        status_frame = ctk.CTkFrame(self, height=30)
        status_frame.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(status_frame, text="就绪", anchor="w")
        self.status_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

    def _load_config_to_ui(self):
        """加载配置到界面"""
        config = self.config_manager.config
        if config.api_base_url:
            self.url_entry.insert(0, config.api_base_url)
        if config.api_key:
            self.key_entry.insert(0, config.api_key)
        if config.model_name:
            self.model_entry.insert(0, config.model_name)

    def _on_save_config(self):
        """保存配置按钮点击事件"""
        url = self.url_entry.get().strip()
        key = self.key_entry.get().strip()
        model = self.model_entry.get().strip() or "deepseek-chat"

        if url and not validate_url(url):
            messagebox.showwarning("提示", "API 地址格式不正确，请输入以 http:// 或 https:// 开头的地址")
            return

        self.config_manager.update(api_base_url=url, api_key=key, model_name=model)
        if self.config_manager.save_config():
            self._set_status("配置已保存")
            messagebox.showinfo("成功", "配置已保存")
        else:
            messagebox.showerror("错误", "配置保存失败")

    def _on_theme_toggle(self):
        """主题切换事件"""
        if self.theme_switch.get():
            ctk.set_appearance_mode("dark")
            self.config_manager.update(theme="dark")
        else:
            ctk.set_appearance_mode("light")
            self.config_manager.update(theme="light")
        self.config_manager.save_config()

    def _on_stream_toggle(self):
        """流式输出开关事件"""
        stream_mode = bool(self.stream_switch.get())
        self.config_manager.update(stream_mode=stream_mode)
        self.config_manager.save_config()

    def _on_clear_input(self):
        """清空输入"""
        self.jd_textbox.delete("1.0", "end")

    def _on_clear_result(self):
        """清空结果"""
        # 清空原文
        self.raw_textbox.configure(state="normal")
        self.raw_textbox.delete("1.0", "end")
        self.raw_textbox.configure(state="disabled")

        # 重置状态
        self._raw_result = ""
        self._analysis_done = False

        # 销毁卡片容器（下次切换时重新创建）
        if self.card_container:
            self.card_container.destroy()
            self.card_container = None

        # 切回原文模式
        self.view_mode.set("raw")
        self._on_view_mode_change()

    def _on_copy_all(self):
        """复制全部结果"""
        if not self._raw_result:
            messagebox.showwarning("提示", "没有可复制的内容")
            return
        if copy_to_clipboard(self._raw_result):
            self._set_status("已复制到剪贴板")
        else:
            messagebox.showerror("错误", "复制失败")

    def _on_analyze(self):
        """开始分析按钮点击事件"""
        url = self.url_entry.get().strip()
        key = self.key_entry.get().strip()
        model = self.model_entry.get().strip() or "deepseek-chat"
        jd_text = self.jd_textbox.get("1.0", "end").strip()

        # 校验
        if not url:
            messagebox.showwarning("提示", "请先填写 API 地址")
            return
        if not validate_url(url):
            messagebox.showwarning("提示", "API 地址格式不正确")
            return
        if not key:
            messagebox.showwarning("提示", "请先填写 API Key")
            return
        if not validate_api_key(key):
            messagebox.showwarning("提示", "API Key 格式不正确")
            return
        if not jd_text:
            messagebox.showwarning("提示", "请先输入岗位描述")
            return

        # 保存当前JD文本
        self._current_jd = jd_text

        # 清空结果区
        self._on_clear_result()

        # 锁定 UI
        self._set_ui_analyzing(True)
        self._stop_flag = False

        # 启动后台线程
        self._analysis_thread = threading.Thread(
            target=self._do_analysis,
            args=(url, key, model, jd_text),
            daemon=True
        )
        self._analysis_thread.start()

    def _do_analysis(self, url: str, key: str, model: str, jd_text: str):
        """后台分析任务（在子线程中运行）"""
        try:
            client = LLMClient(
                api_base_url=url,
                api_key=key,
                model_name=model,
                timeout=self.config_manager.config.timeout
            )

            # 根据配置选择流式或非流式输出
            if self.config_manager.config.stream_mode:
                # 流式输出
                for chunk in client.analyze_jd_stream(jd_text):
                    if self._stop_flag:
                        break
                    self._raw_result += chunk
                    self.after(0, self._append_raw_text, chunk)
            else:
                # 非流式输出
                result = client.analyze_jd(jd_text)
                if not self._stop_flag:
                    self._raw_result = result
                    self.after(0, self._append_raw_text, result)

            if not self._stop_flag:
                self.after(0, self._on_analysis_complete, None)

        except (AuthError, NetworkError, TimeoutError, LLMClientError) as e:
            self.after(0, self._on_analysis_complete, str(e))
        except Exception as e:
            self.after(0, self._on_analysis_complete, f"未知错误: {str(e)}")

    def _append_raw_text(self, text: str):
        """追加原文文本"""
        self.raw_textbox.configure(state="normal")
        self.raw_textbox.insert("end", text)
        self.raw_textbox.see("end")
        self.raw_textbox.configure(state="disabled")

    def _on_analysis_complete(self, error: Optional[str]):
        """分析完成回调"""
        self._set_ui_analyzing(False)
        if error:
            messagebox.showerror("分析失败", error)
            self._set_status("分析失败")
        else:
            self._analysis_done = True
            # 保存历史记录
            if self._current_jd and self._raw_result:
                self.history_manager.save_record(self._current_jd, self._raw_result)
            self._set_status("分析完成 - 已自动保存到历史记录")

    def _set_ui_analyzing(self, analyzing: bool):
        """设置 UI 分析状态"""
        if analyzing:
            self.analyze_btn.configure(state="disabled", text="AI 正在思考中...")
            self.clear_btn.configure(state="disabled")
            self._set_status("正在分析...")
        else:
            self.analyze_btn.configure(state="normal", text="开始分析")
            self.clear_btn.configure(state="normal")

    def _set_status(self, text: str):
        """设置状态栏文本"""
        self.status_label.configure(text=text)

    def on_closing(self):
        """窗口关闭事件"""
        self._stop_flag = True
        self.destroy()

    def _on_history_click(self):
        """历史记录按钮点击事件"""
        self.view_mode.set("history")
        self._on_view_mode_change()

    def _on_load_history(self, record):
        """加载历史记录到主界面"""
        # 切回原文模式
        self.view_mode.set("raw")
        self._on_view_mode_change()

        # 清空当前内容
        self.jd_textbox.delete("1.0", "end")
        self.raw_textbox.configure(state="normal")
        self.raw_textbox.delete("1.0", "end")
        self.raw_textbox.configure(state="disabled")

        # 加载历史JD
        self.jd_textbox.insert("1.0", record.jd_text)

        # 加载历史结果
        self._raw_result = record.result
        self._current_jd = record.jd_text
        self._analysis_done = True

        # 显示结果
        self.raw_textbox.configure(state="normal")
        self.raw_textbox.insert("1.0", record.result)
        self.raw_textbox.configure(state="disabled")

        # 销毁旧的卡片容器（如果有）
        if self.card_container:
            self.card_container.destroy()
            self.card_container = None

        self._set_status(f"已加载历史记录：{record.title}")
