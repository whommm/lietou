"""主窗口 UI 模块"""

import customtkinter as ctk
from tkinter import messagebox
import threading
from typing import Optional

from ..core.config import ConfigManager
from ..core.history import HistoryManager
from ..core.llm_client import (
    LLMClient,
    LLMClientError,
    AuthError,
    NetworkError,
    TimeoutError,
)
from ..utils.helpers import copy_to_clipboard, validate_url, validate_api_key
from .history_widget import HistoryPanel
from .html_renderer import HtmlRenderer
from .resume_match_widget import ResumeMatchWidget
from .company_research_widget import CompanyResearchWidget
from ..core.prompt import RESUME_MATCH_PROMPT
from ..core.company_research_client import CompanyResearchClient, CompanyResearchError


class MainWindow(ctk.CTk):
    """主窗口类"""

    def __init__(self):
        super().__init__()

        # 配置管理器
        self.config_manager = ConfigManager()

        # 历史记录管理器 - 三个独立的管理器
        self.job_history_manager = HistoryManager(record_type="job_analysis")
        self.resume_history_manager = HistoryManager(record_type="resume_match")
        self.company_history_manager = HistoryManager(record_type="company_research")

        # 窗口基本设置
        self.title("智能岗位分析与寻访助手")
        self.geometry("1300x900")
        self.minsize(1000, 700)

        # 设置主题
        ctk.set_appearance_mode(self.config_manager.config.theme)
        ctk.set_default_color_theme("blue")

        # 分析线程
        self._analysis_thread: Optional[threading.Thread] = None
        self._resume_match_thread: Optional[threading.Thread] = None
        self._company_research_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # 原始结果文本
        self._raw_result = ""

        # 当前分析的JD文本（用于保存历史记录）
        self._current_jd = ""

        # 是否已完成分析
        self._analysis_done = False

        # 构建界面
        self._build_ui()

        # 加载配置到界面
        self._load_config_to_ui()

        # 初始化简历匹配的岗位列表
        self._update_resume_job_list()

        # 初始化岗位分析的公司调研列表
        self._update_company_list()

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

        # 第一行：LLM配置
        ctk.CTkLabel(config_frame, text="API 地址:").grid(
            row=0, column=0, padx=(10, 5), pady=10, sticky="w"
        )
        self.url_entry = ctk.CTkEntry(
            config_frame, placeholder_text="https://api.deepseek.com/v1"
        )
        self.url_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        ctk.CTkLabel(config_frame, text="API Key:").grid(
            row=0, column=2, padx=(20, 5), pady=10, sticky="w"
        )
        self.key_entry = ctk.CTkEntry(
            config_frame, placeholder_text="sk-xxx...", show="*"
        )
        self.key_entry.grid(row=0, column=3, padx=5, pady=10, sticky="ew")

        ctk.CTkLabel(config_frame, text="模型:").grid(
            row=0, column=4, padx=(20, 5), pady=10, sticky="w"
        )
        self.model_entry = ctk.CTkEntry(
            config_frame, placeholder_text="deepseek-chat", width=220
        )
        self.model_entry.grid(row=0, column=5, padx=5, pady=10)

        self.save_btn = ctk.CTkButton(
            config_frame, text="保存配置", width=100, command=self._on_save_config
        )
        self.save_btn.grid(row=0, column=6, padx=(20, 10), pady=10)

        self.theme_switch = ctk.CTkSwitch(
            config_frame, text="深色模式", command=self._on_theme_toggle
        )
        self.theme_switch.grid(row=0, column=7, padx=(10, 5), pady=10)
        if self.config_manager.config.theme == "dark":
            self.theme_switch.select()

        # 第二行：Tavily API Key
        ctk.CTkLabel(config_frame, text="Tavily Key:").grid(
            row=1, column=0, padx=(10, 5), pady=(0, 10), sticky="w"
        )
        self.tavily_key_entry = ctk.CTkEntry(
            config_frame, placeholder_text="tvly-xxx... (用于公司调研)", show="*"
        )
        self.tavily_key_entry.grid(
            row=1, column=1, columnspan=5, padx=5, pady=(0, 10), sticky="ew"
        )

    def _build_main_content(self):
        """构建主内容区"""
        # 创建标签页视图
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        # 添加三个标签页（公司调研放在第一个）
        self.tab_company = self.tabview.add("公司调研")
        self.tab_job = self.tabview.add("岗位分析")
        self.tab_resume = self.tabview.add("简历匹配")

        # 构建公司调研标签页内容
        self._build_company_research_tab()

        # 构建岗位分析标签页内容
        self._build_job_analysis_tab()

        # 构建简历匹配标签页内容
        self._build_resume_match_tab()

    def _build_job_analysis_tab(self):
        """构建岗位分析标签页"""
        self.tab_job.grid_columnconfigure(0, weight=2)
        self.tab_job.grid_columnconfigure(1, weight=3)
        self.tab_job.grid_rowconfigure(0, weight=1)

        self._build_input_panel(self.tab_job)
        self._build_output_panel(self.tab_job)

    def _build_resume_match_tab(self):
        """构建简历匹配标签页"""
        self.tab_resume.grid_columnconfigure(0, weight=2)
        self.tab_resume.grid_columnconfigure(1, weight=3)
        self.tab_resume.grid_rowconfigure(0, weight=1)

        self.resume_match_widget = ResumeMatchWidget(
            self.tab_resume,
            on_match=self._on_resume_match,
            job_list=["请先分析岗位"],
            theme=self.config_manager.config.theme,
        )
        self.resume_match_widget.grid(
            row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5
        )

    def _build_company_research_tab(self):
        """构建公司调研标签页"""
        self.tab_company.grid_columnconfigure(0, weight=2)
        self.tab_company.grid_columnconfigure(1, weight=3)
        self.tab_company.grid_rowconfigure(0, weight=1)

        self.company_research_widget = CompanyResearchWidget(
            self.tab_company,
            on_research=self._on_company_research,
            history_manager=self.company_history_manager,
            theme=self.config_manager.config.theme,
        )
        self.company_research_widget.grid(
            row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5
        )

    def _build_input_panel(self, parent):
        """构建左侧输入面板"""
        input_frame = ctk.CTkFrame(parent)
        input_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        input_frame.grid_columnconfigure(0, weight=1)
        input_frame.grid_rowconfigure(3, weight=1)

        # 标题
        ctk.CTkLabel(
            input_frame,
            text="原始岗位描述 (JD)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        # 描述
        ctk.CTkLabel(
            input_frame,
            text="输入岗位描述，AI将自动分析并生成结构化报告",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray60"),
        ).grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")

        # 公司调研选择
        ctk.CTkLabel(input_frame, text="参考公司调研（可选）:").grid(
            row=2, column=0, padx=10, pady=(5, 5), sticky="w"
        )
        self.company_combo = ctk.CTkComboBox(input_frame, values=["不使用"])
        self.company_combo.grid(row=3, column=0, padx=10, pady=(0, 5), sticky="ew")

        # JD输入框
        self.jd_textbox = ctk.CTkTextbox(input_frame, wrap="word")
        self.jd_textbox.grid(row=4, column=0, padx=10, pady=5, sticky="nsew")
        input_frame.grid_rowconfigure(4, weight=1)

        # 按钮区
        btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_frame.grid(row=5, column=0, padx=10, pady=10, sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)

        self.clear_btn = ctk.CTkButton(
            btn_frame,
            text="清空",
            width=80,
            fg_color="gray",
            command=self._on_clear_input,
        )
        self.clear_btn.grid(row=0, column=0, padx=5, sticky="w")

        self.analyze_btn = ctk.CTkButton(
            btn_frame, text="开始分析", width=150, command=self._on_analyze
        )
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

        ctk.CTkLabel(
            header_frame, text="分析结果", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")

        # 按钮区
        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.pack(side="right")

        # 复制全部按钮
        self.copy_all_btn = ctk.CTkButton(
            btn_frame, text="复制全部", width=80, height=28, command=self._on_copy_all
        )
        self.copy_all_btn.pack(side="right", padx=5)

        # 清空按钮
        self.clear_result_btn = ctk.CTkButton(
            btn_frame,
            text="清空",
            width=60,
            height=28,
            fg_color="gray",
            command=self._on_clear_result,
        )
        self.clear_result_btn.pack(side="right", padx=5)

        # 历史按钮
        self.history_btn = ctk.CTkButton(
            btn_frame, text="历史", width=60, height=28, command=self._on_history_click
        )
        self.history_btn.pack(side="right", padx=5)

        # HTML渲染器
        self.html_renderer = HtmlRenderer(
            output_frame, theme=self.config_manager.config.theme
        )
        self.html_renderer.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")

        # 历史面板（延迟创建）
        self.history_panel = None
        self._showing_history = False

    def _on_history_click(self):
        """历史按钮点击事件"""
        if self._showing_history:
            # 切回结果视图
            self._hide_history()
        else:
            # 显示历史视图
            self._show_history()

    def _show_history(self):
        """显示历史面板"""
        # 隐藏HTML渲染器
        self.html_renderer.grid_forget()

        # 创建或刷新历史面板
        if self.history_panel is None:
            parent = self.html_renderer.parent
            self.history_panel = HistoryPanel(
                parent,
                history_manager=self.job_history_manager,
                on_load_record=self._on_load_history,
            )
        else:
            self.history_panel.refresh()

        self.history_panel.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
        self._showing_history = True
        self.history_btn.configure(text="返回")

    def _hide_history(self):
        """隐藏历史面板"""
        if self.history_panel:
            self.history_panel.grid_forget()

        self.html_renderer.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
        self._showing_history = False
        self.history_btn.configure(text="历史")

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
        if config.tavily_api_key:
            self.tavily_key_entry.insert(0, config.tavily_api_key)

    def _on_save_config(self):
        """保存配置按钮点击事件"""
        url = self.url_entry.get().strip()
        key = self.key_entry.get().strip()
        model = self.model_entry.get().strip() or "deepseek-chat"
        tavily_key = self.tavily_key_entry.get().strip()

        if url and not validate_url(url):
            messagebox.showwarning(
                "提示", "API 地址格式不正确，请输入以 http:// 或 https:// 开头的地址"
            )
            return

        self.config_manager.update(
            api_base_url=url, api_key=key, model_name=model, tavily_api_key=tavily_key
        )
        if self.config_manager.save_config():
            self._set_status("配置已保存")
            messagebox.showinfo("成功", "配置已保存")
        else:
            messagebox.showerror("错误", "配置保存失败")

    def _on_theme_toggle(self):
        """主题切换事件"""
        theme = "dark" if self.theme_switch.get() else "light"
        ctk.set_appearance_mode(theme)
        self.config_manager.update(theme=theme)
        self.config_manager.save_config()

        # 更新HTML渲染器主题
        self.html_renderer.set_theme(theme)
        self.company_research_widget.set_theme(theme)
        self.resume_match_widget.set_theme(theme)

    def _on_clear_input(self):
        """清空输入"""
        self.jd_textbox.delete("1.0", "end")

    def _on_clear_result(self):
        """清空结果"""
        # 清空HTML渲染器
        self.html_renderer.clear()

        # 重置状态
        self._raw_result = ""
        self._analysis_done = False

        # 如果正在显示历史，切回结果视图
        if self._showing_history:
            self._hide_history()

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

        # 获取公司调研上下文
        company_context = ""
        company_title = self.company_combo.get()
        if company_title and company_title != "不使用":
            records = self.company_history_manager.get_all()
            for record in records:
                if record.title == company_title:
                    company_context = record.result
                    break

        # 清空结果区
        self._on_clear_result()

        # 如果正在显示历史，切回结果视图
        if self._showing_history:
            self._hide_history()

        # 锁定 UI
        self._set_ui_analyzing(True)
        self._stop_event.clear()

        self.html_renderer.show_loading()

        self._analysis_thread = threading.Thread(
            target=self._do_analysis,
            args=(url, key, model, jd_text, company_context),
            daemon=True,
        )
        self._analysis_thread.start()

    def _do_analysis(
        self, url: str, key: str, model: str, jd_text: str, company_context: str = ""
    ):
        """后台分析任务（在子线程中运行）"""
        try:
            client = LLMClient(
                api_base_url=url,
                api_key=key,
                model_name=model,
                timeout=self.config_manager.config.timeout,
            )

            result = client.analyze_jd(jd_text, company_context)
            if not self._stop_event.is_set():
                self._raw_result = result
                self.after(0, self._on_analysis_complete, None)

        except (AuthError, NetworkError, TimeoutError, LLMClientError) as e:
            self.after(0, self._on_analysis_complete, str(e))
        except Exception as e:
            import traceback

            error_detail = f"未知错误: {str(e)}\n{traceback.format_exc()}"
            self.after(0, self._on_analysis_complete, error_detail)

    def _on_analysis_complete(self, error: Optional[str]):
        """分析完成回调"""
        self._set_ui_analyzing(False)

        if error:
            self.html_renderer.clear()
            messagebox.showerror("分析失败", error)
            self._set_status("分析失败")
        else:
            self._analysis_done = True
            self.html_renderer.set_content(self._raw_result)
            if self._current_jd and self._raw_result:
                self.job_history_manager.save_record(self._current_jd, self._raw_result)
                self._update_resume_job_list()
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
        """安全关闭"""
        self._stop_event.set()

        if self._analysis_thread and self._analysis_thread.is_alive():
            self._analysis_thread.join(timeout=3.0)

        if hasattr(self, "html_renderer"):
            self.html_renderer.clear()

        self.destroy()

    def _on_load_history(self, record):
        """加载历史记录到主界面"""
        # 切回结果视图
        if self._showing_history:
            self._hide_history()

        # 清空当前内容
        self.jd_textbox.delete("1.0", "end")

        # 加载历史JD
        self.jd_textbox.insert("1.0", record.jd_text)

        # 加载历史结果
        self._raw_result = record.result
        self._current_jd = record.jd_text
        self._analysis_done = True

        # 显示结果（使用HTML渲染）
        self.html_renderer.set_content(record.result)

        self._set_status(f"已加载历史记录：{record.title}")

    def _on_resume_match(self, job_desc: str, resume: str):
        """简历匹配处理"""
        url = self.url_entry.get().strip()
        key = self.key_entry.get().strip()
        model = self.model_entry.get().strip() or "deepseek-chat"

        if not url:
            messagebox.showwarning("提示", "请先填写 API 地址")
            self.resume_match_widget.set_matching(False)
            return
        if not key:
            messagebox.showwarning("提示", "请先填写 API Key")
            self.resume_match_widget.set_matching(False)
            return

        if self._resume_match_thread and self._resume_match_thread.is_alive():
            messagebox.showwarning("提示", "上一次匹配仍在进行中，请稍候")
            self.resume_match_widget.set_matching(False)
            return

        self._resume_match_thread = threading.Thread(
            target=self._do_resume_match,
            args=(url, key, model, job_desc, resume),
            daemon=True,
        )
        self._resume_match_thread.start()

    def _do_resume_match(
        self, url: str, key: str, model: str, job_desc: str, resume: str
    ):
        """后台简历匹配任务"""
        try:
            client = LLMClient(
                api_base_url=url, api_key=key, model_name=model, timeout=60
            )

            prompt = RESUME_MATCH_PROMPT.format(job_description=job_desc, resume=resume)
            result_text = client.chat(prompt)

            self.after(
                0, self._on_resume_match_complete, result_text, job_desc, resume, None
            )

        except Exception as e:
            self.after(0, self._on_resume_match_complete, "", job_desc, resume, str(e))

    def _on_resume_match_complete(
        self, result_text: str, job_desc: str, resume: str, error: Optional[str]
    ):
        """简历匹配完成回调"""
        self.resume_match_widget.set_matching(False)

        if error:
            self.resume_match_widget.html_renderer.clear()
            messagebox.showerror("匹配失败", error)
            self._set_status("简历匹配失败")
        else:
            self.resume_match_widget.set_result(result_text)
            if result_text:
                self.resume_history_manager.save_record(
                    jd_text="[简历匹配]\n岗位: {}...\n简历: {}...".format(
                        job_desc[:100], resume[:100]
                    ),
                    result=result_text,
                )
            self._set_status("简历匹配完成")

    def _update_company_list(self):
        """更新岗位分析的公司调研列表"""
        records = self.company_history_manager.get_all()
        if records:
            company_list = ["不使用"] + [r.title for r in records]
            self.company_combo.configure(values=company_list)
            self.company_combo.set("不使用")
        else:
            self.company_combo.configure(values=["不使用"])
            self.company_combo.set("不使用")

    def _update_resume_job_list(self):
        records = self.job_history_manager.get_all()
        if records:
            job_list = [
                f"{r.title[:30]}..." if len(r.title) > 30 else r.title for r in records
            ]
            job_data_map = {
                (f"{r.title[:30]}..." if len(r.title) > 30 else r.title): r.jd_text
                for r in records
            }
            self.resume_match_widget.update_job_list(job_list, job_data_map)

    def _on_company_research(self, company_name: str):
        """公司调研处理"""
        url = self.url_entry.get().strip()
        key = self.key_entry.get().strip()
        model = self.model_entry.get().strip() or "deepseek-chat"
        tavily_key = self.tavily_key_entry.get().strip()

        if not url or not key:
            messagebox.showwarning("提示", "请先配置API地址和Key")
            self.company_research_widget.set_researching(False)
            return

        if not tavily_key:
            messagebox.showwarning("提示", "请先配置Tavily API Key")
            self.company_research_widget.set_researching(False)
            return

        if self._company_research_thread and self._company_research_thread.is_alive():
            messagebox.showwarning("提示", "上一次调研仍在进行中，请稍候")
            self.company_research_widget.set_researching(False)
            return

        self._company_research_thread = threading.Thread(
            target=self._do_company_research,
            args=(url, key, model, tavily_key, company_name),
            daemon=True,
        )
        self._company_research_thread.start()

    def _do_company_research(
        self, url: str, key: str, model: str, tavily_key: str, company_name: str
    ):
        """后台公司调研任务"""
        try:
            llm_client = LLMClient(
                api_base_url=url, api_key=key, model_name=model, timeout=120
            )
            research_client = CompanyResearchClient(
                tavily_api_key=tavily_key, llm_client=llm_client
            )

            result = research_client.research(company_name)
            self.after(
                0, self._on_company_research_complete, company_name, None, result
            )

        except Exception as e:
            self.after(0, self._on_company_research_complete, company_name, str(e), "")

    def _on_company_research_complete(
        self, company_name: str, error: Optional[str], result: str = ""
    ):
        """公司调研完成回调"""
        self.company_research_widget.set_researching(False)

        if error:
            self.html_renderer.clear()
            messagebox.showerror("调研失败", error)
            self._set_status("公司调研失败")
        else:
            self.company_research_widget.set_result(result)
            if result:
                self.company_history_manager.save_record(
                    jd_text="[公司调研] {}".format(company_name), result=result
                )
                self.company_research_widget.refresh_history()
                self._update_company_list()
            self._set_status("公司调研完成 - {}".format(company_name))
