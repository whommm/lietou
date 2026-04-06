"""主窗口 UI 模块。"""

import threading
from tkinter import TclError, messagebox
from typing import Optional

import customtkinter as ctk

from ..core.company_research_client import CompanyResearchClient
from ..core.config import ConfigManager
from ..core.history import HistoryManager
from ..core.llm_client import (
    AuthError,
    LLMClient,
    LLMClientError,
    NetworkError,
    TimeoutError,
)
from ..core.prompt import RESUME_MATCH_PROMPT
from ..utils.helpers import validate_api_key, validate_url
from .company_research_widget import CompanyResearchWidget
from .history_picker import HistoryPickerDialog
from .job_analysis_widget import JobAnalysisWidget
from .resume_match_widget import ResumeMatchWidget


class MainWindow(ctk.CTk):
    """主窗口类。"""

    FIXED_THEME = "light"

    MAX_COMPANY_OPTIONS = 3
    MAX_JOB_OPTIONS = 3

    SURFACE_COLORS = {
        "app": "#edf4ff",
        "panel": "#ffffff",
        "panel_alt": "#f7faff",
        "panel_soft": "#f3f7ff",
        "panel_edge": "#d9e5ff",
        "text": "#13233d",
        "muted": "#64748f",
        "accent": "#4f7cff",
        "accent_hover": "#3f68e6",
        "secondary": "#edf3ff",
        "secondary_hover": "#dde8ff",
    }

    def __init__(self):
        super().__init__()

        self.config_manager = ConfigManager()
        self.job_history_manager = HistoryManager(record_type="job_analysis")
        self.resume_history_manager = HistoryManager(record_type="resume_match")
        self.company_history_manager = HistoryManager(record_type="company_research")

        self.title("智能岗位分析与寻访助手")
        self.geometry("1300x900")
        self.minsize(1000, 700)

        self.config_manager.update(theme=self.FIXED_THEME)
        ctk.set_appearance_mode(self.FIXED_THEME)
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=self.SURFACE_COLORS["app"])

        self._analysis_thread: Optional[threading.Thread] = None
        self._resume_match_thread: Optional[threading.Thread] = None
        self._company_research_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._raw_result = ""
        self._current_jd = ""

        self._build_ui()
        self._load_config_to_ui()
        self._update_resume_job_list()
        self._update_company_list()

    def _build_ui(self):
        """构建用户界面。"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_config_frame()
        self._build_main_content()
        self._build_status_bar()

    def _build_config_frame(self):
        """构建顶部配置区。"""
        colors = self.SURFACE_COLORS
        config_frame = ctk.CTkFrame(
            self,
            corner_radius=24,
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["panel_edge"],
        )
        config_frame.grid(row=0, column=0, padx=14, pady=(14, 6), sticky="ew")
        config_frame.grid_columnconfigure(1, weight=1)
        config_frame.grid_columnconfigure(3, weight=1)
        config_frame.grid_columnconfigure(8, weight=1)

        title_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        title_frame.grid(
            row=0, column=0, columnspan=2, padx=(16, 10), pady=(14, 4), sticky="w"
        )
        ctk.CTkLabel(
            title_frame,
            text="智能岗位分析工作台",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=colors["text"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_frame,
            text="统一管理模型配置、公司调研、岗位分析与简历匹配。",
            font=ctk.CTkFont(size=12),
            text_color=colors["muted"],
        ).pack(anchor="w", pady=(2, 0))

        badge = ctk.CTkLabel(
            config_frame,
            text="Light Workspace",
            corner_radius=999,
            padx=14,
            pady=7,
            fg_color=colors["secondary"],
            text_color=colors["text"],
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        badge.grid(row=0, column=8, padx=(10, 16), pady=(16, 6), sticky="e")

        ctk.CTkLabel(config_frame, text="API 地址:").grid(
            row=1, column=0, padx=(16, 5), pady=10, sticky="w"
        )
        self.url_entry = ctk.CTkEntry(
            config_frame,
            placeholder_text="https://api.deepseek.com/v1",
            corner_radius=16,
            height=36,
            fg_color=colors["panel_alt"],
            border_color=colors["panel_edge"],
            text_color=colors["text"],
        )
        self.url_entry.grid(row=1, column=1, padx=5, pady=10, sticky="ew")

        ctk.CTkLabel(config_frame, text="API Key:").grid(
            row=1, column=2, padx=(20, 5), pady=10, sticky="w"
        )
        self.key_entry = ctk.CTkEntry(
            config_frame,
            placeholder_text="sk-xxx...",
            show="*",
            corner_radius=16,
            height=36,
            fg_color=colors["panel_alt"],
            border_color=colors["panel_edge"],
            text_color=colors["text"],
        )
        self.key_entry.grid(row=1, column=3, padx=5, pady=10, sticky="ew")

        ctk.CTkLabel(config_frame, text="模型:").grid(
            row=1, column=4, padx=(20, 5), pady=10, sticky="w"
        )
        self.model_entry = ctk.CTkEntry(
            config_frame,
            placeholder_text="deepseek-chat",
            width=220,
            corner_radius=16,
            height=36,
            fg_color=colors["panel_alt"],
            border_color=colors["panel_edge"],
            text_color=colors["text"],
        )
        self.model_entry.grid(row=1, column=5, padx=5, pady=10)

        self.save_btn = ctk.CTkButton(
            config_frame,
            text="保存配置",
            width=110,
            height=38,
            corner_radius=18,
            fg_color=colors["accent"],
            hover_color=colors["accent_hover"],
            text_color="#f8fbff",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_save_config,
        )
        self.save_btn.grid(row=1, column=6, padx=(20, 10), pady=10)

        ctk.CTkLabel(config_frame, text="Tavily Key:").grid(
            row=2, column=0, padx=(16, 5), pady=(0, 16), sticky="w"
        )
        self.tavily_key_entry = ctk.CTkEntry(
            config_frame,
            placeholder_text="tvly-xxx... (用于公司调研)",
            show="*",
            corner_radius=16,
            height=36,
            fg_color=colors["panel_alt"],
            border_color=colors["panel_edge"],
            text_color=colors["text"],
        )
        self.tavily_key_entry.grid(
            row=2, column=1, columnspan=7, padx=(5, 16), pady=(0, 16), sticky="ew"
        )

        for label in config_frame.winfo_children():
            if isinstance(label, ctk.CTkLabel) and label not in (badge,):
                label.configure(text_color=colors["text"])

    def _build_main_content(self):
        """构建主内容区。"""
        colors = self.SURFACE_COLORS
        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=24,
            fg_color=colors["panel"],
            segmented_button_fg_color=colors["secondary"],
            segmented_button_selected_color=colors["accent"],
            segmented_button_selected_hover_color=colors["accent_hover"],
            segmented_button_unselected_color=colors["secondary"],
            segmented_button_unselected_hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            border_width=1,
            border_color=colors["panel_edge"],
        )
        self.tabview.grid(row=1, column=0, padx=14, pady=6, sticky="nsew")

        self.tab_company = self.tabview.add("公司调研")
        self.tab_job = self.tabview.add("岗位分析")
        self.tab_resume = self.tabview.add("简历匹配")

        self._build_company_research_tab()
        self._build_job_analysis_tab()
        self._build_resume_match_tab()

    def _build_job_analysis_tab(self):
        """构建岗位分析标签页。"""
        self.tab_job.grid_columnconfigure(0, weight=2)
        self.tab_job.grid_columnconfigure(1, weight=3)
        self.tab_job.grid_rowconfigure(0, weight=1)

        self.job_analysis_widget = JobAnalysisWidget(
            self.tab_job,
            on_analyze=self._on_analyze,
            history_manager=self.job_history_manager,
            company_options=["不使用"],
            on_pick_company_history=self._open_company_history_picker,
            on_history_changed=self._update_company_list,
            theme=self.FIXED_THEME,
        )
        self.job_analysis_widget.grid(
            row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5
        )

    def _build_resume_match_tab(self):
        """构建简历匹配标签页。"""
        self.tab_resume.grid_columnconfigure(0, weight=2)
        self.tab_resume.grid_columnconfigure(1, weight=3)
        self.tab_resume.grid_rowconfigure(0, weight=1)

        self.resume_match_widget = ResumeMatchWidget(
            self.tab_resume,
            on_match=self._on_resume_match,
            job_list=["请先分析岗位"],
            on_pick_history=self._open_job_history_picker,
            theme=self.FIXED_THEME,
        )
        self.resume_match_widget.grid(
            row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5
        )

    def _build_company_research_tab(self):
        """构建公司调研标签页。"""
        self.tab_company.grid_columnconfigure(0, weight=2)
        self.tab_company.grid_columnconfigure(1, weight=3)
        self.tab_company.grid_rowconfigure(0, weight=1)

        self.company_research_widget = CompanyResearchWidget(
            self.tab_company,
            on_research=self._on_company_research,
            history_manager=self.company_history_manager,
            on_history_changed=self._update_company_list,
            theme=self.FIXED_THEME,
        )
        self.company_research_widget.grid(
            row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5
        )

    def _build_status_bar(self):
        """构建底部状态栏。"""
        colors = self.SURFACE_COLORS
        status_frame = ctk.CTkFrame(
            self,
            height=42,
            corner_radius=18,
            fg_color=colors["panel_soft"],
            border_width=1,
            border_color=colors["panel_edge"],
        )
        status_frame.grid(row=2, column=0, padx=14, pady=(6, 14), sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            status_frame,
            text="就绪",
            anchor="w",
            text_color=colors["text"],
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.status_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.status_hint_label = ctk.CTkLabel(
            status_frame,
            text="Single Light Theme Workspace",
            text_color=colors["muted"],
            font=ctk.CTkFont(size=11),
        )
        self.status_hint_label.grid(row=0, column=1, padx=10, pady=5, sticky="e")

    def _load_config_to_ui(self):
        """加载配置到界面。"""
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
        """保存配置按钮点击事件。"""
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
            api_base_url=url,
            api_key=key,
            model_name=model,
            tavily_api_key=tavily_key,
        )
        if self.config_manager.save_config():
            self._set_status("配置已保存")
            messagebox.showinfo("成功", "配置已保存")
        else:
            messagebox.showerror("错误", "配置保存失败")

    def _safe_after(self, callback, *args):
        """窗口仍存在时再派发 UI 回调，避免关闭后触发 Tcl 错误。"""
        try:
            if self.winfo_exists():
                self.after(0, callback, *args)
        except TclError:
            return

    def _create_llm_client(self, url: str, key: str, model: str, timeout: int):
        """创建统一的 LLM 客户端。"""
        return LLMClient(
            api_base_url=url,
            api_key=key,
            model_name=model,
            timeout=timeout,
        )

    def _get_llm_config(self):
        """获取当前 LLM 配置。"""
        return (
            self.url_entry.get().strip(),
            self.key_entry.get().strip(),
            self.model_entry.get().strip() or "deepseek-chat",
        )

    def _validate_llm_config(self):
        """校验通用 LLM 配置。"""
        url, key, model = self._get_llm_config()

        if not url:
            messagebox.showwarning("提示", "请先填写 API 地址")
            return None
        if not validate_url(url):
            messagebox.showwarning("提示", "API 地址格式不正确")
            return None
        if not key:
            messagebox.showwarning("提示", "请先填写 API Key")
            return None
        if not validate_api_key(key):
            messagebox.showwarning("提示", "API Key 格式不正确")
            return None

        return url, key, model

    def _validate_company_research_config(self):
        """校验公司调研所需配置。"""
        config = self._validate_llm_config()
        if not config:
            return None

        tavily_key = self.tavily_key_entry.get().strip()
        if not tavily_key:
            messagebox.showwarning("提示", "请先配置 Tavily API Key")
            return None

        return config + (tavily_key,)

    def _build_resume_history_payload(self, job_desc: str, resume: str):
        """构建简历匹配历史记录原文。"""
        job_summary = job_desc.strip().replace("\n", " ")[:120]
        resume_summary = resume.strip().replace("\n", " ")[:120]
        return "[简历匹配]\n岗位: {}\n简历摘要: {}".format(job_summary, resume_summary)

    def _run_threaded_task(self, thread_attr: str, target, args: tuple):
        """启动后台线程任务。"""
        thread = threading.Thread(target=target, args=args, daemon=True)
        setattr(self, thread_attr, thread)
        thread.start()

    def _find_company_context(self, company_title: str) -> str:
        """根据选项名查找公司调研上下文。"""
        if not company_title or company_title == "不使用":
            return ""

        for record in self.company_history_manager.get_all():
            if record.title == company_title:
                return record.result
        return ""

    def _start_job_analysis(self):
        """进入岗位分析执行态。"""
        self.job_analysis_widget.clear_result()
        self.job_analysis_widget.set_analyzing(True)
        self.job_analysis_widget.show_loading()
        self._stop_event.clear()
        self._set_status("正在进行岗位分析...")

    def _finish_job_analysis(self, error: Optional[str]):
        """收口岗位分析执行态。"""
        self.job_analysis_widget.set_analyzing(False)

        if error:
            self.job_analysis_widget.clear_result()
            messagebox.showerror("分析失败", error)
            self._set_status("岗位分析失败")
            return

        self.job_analysis_widget.set_result(self._raw_result)
        if self._current_jd and self._raw_result:
            self.job_history_manager.save_record(self._current_jd, self._raw_result)
            self._update_resume_job_list()
        self._set_status("岗位分析完成，结果已保存到历史记录")

    def _start_resume_match(self):
        """进入简历匹配执行态。"""
        self.resume_match_widget.show_loading()
        self._set_status("正在进行简历匹配...")

    def _finish_resume_match(
        self, result_text: str, job_desc: str, resume: str, error: Optional[str]
    ):
        """收口简历匹配执行态。"""
        self.resume_match_widget.set_matching(False)

        if error:
            self.resume_match_widget.clear_result()
            messagebox.showerror("匹配失败", error)
            self._set_status("简历匹配失败")
            return

        self.resume_match_widget.set_result(result_text)
        if result_text:
            self.resume_history_manager.save_record(
                jd_text=self._build_resume_history_payload(job_desc, resume),
                result=result_text,
            )
        self._set_status("简历匹配完成，结果已保存到历史记录")

    def _start_company_research(self):
        """进入公司调研执行态。"""
        self.company_research_widget.show_loading()
        self._set_status("正在进行公司调研...")

    def _finish_company_research(
        self, company_name: str, error: Optional[str], result: str = ""
    ):
        """收口公司调研执行态。"""
        self.company_research_widget.set_researching(False)

        if error:
            self.company_research_widget.clear_result()
            messagebox.showerror("调研失败", error)
            self._set_status("公司调研失败")
            return

        self.company_research_widget.set_result(result)
        if result:
            self.company_history_manager.save_record(
                jd_text="[公司调研] {}".format(company_name),
                result=result,
            )
            self.company_research_widget.refresh_history()
            self._update_company_list()
        self._set_status("公司调研完成 - {}".format(company_name))

    def _on_analyze(self, jd_text: str, company_title: str):
        """开始分析按钮点击事件。"""
        config = self._validate_llm_config()
        if not config:
            return
        url, key, model = config

        self._current_jd = jd_text
        company_context = self._find_company_context(company_title)

        self._start_job_analysis()
        self._run_threaded_task(
            "_analysis_thread",
            self._do_analysis,
            (url, key, model, jd_text, company_context),
        )

    def _do_analysis(
        self, url: str, key: str, model: str, jd_text: str, company_context: str = ""
    ):
        """后台分析任务。"""
        try:
            client = self._create_llm_client(
                url, key, model, self.config_manager.config.timeout
            )
            result = client.analyze_jd(jd_text, company_context)
            if not self._stop_event.is_set():
                self._raw_result = result
                self._safe_after(self._on_analysis_complete, None)
        except (AuthError, NetworkError, TimeoutError, LLMClientError) as e:
            self._safe_after(self._on_analysis_complete, str(e))
        except Exception as e:
            import traceback

            error_detail = f"未知错误: {str(e)}\n{traceback.format_exc()}"
            self._safe_after(self._on_analysis_complete, error_detail)

    def _on_analysis_complete(self, error: Optional[str]):
        """岗位分析完成回调。"""
        self._finish_job_analysis(error)

    def _on_resume_match(self, job_desc: str, resume: str):
        """简历匹配处理。"""
        config = self._validate_llm_config()
        if not config:
            self.resume_match_widget.set_matching(False)
            self.resume_match_widget.clear_result()
            return
        url, key, model = config

        if self._resume_match_thread and self._resume_match_thread.is_alive():
            messagebox.showwarning("提示", "上一次匹配仍在进行中，请稍候")
            self.resume_match_widget.set_matching(False)
            self.resume_match_widget.clear_result()
            return

        self._start_resume_match()
        self._run_threaded_task(
            "_resume_match_thread",
            self._do_resume_match,
            (url, key, model, job_desc, resume),
        )

    def _do_resume_match(
        self, url: str, key: str, model: str, job_desc: str, resume: str
    ):
        """后台简历匹配任务。"""
        try:
            client = self._create_llm_client(url, key, model, 60)
            prompt = RESUME_MATCH_PROMPT.format(job_description=job_desc, resume=resume)
            result_text = client.chat(prompt)
            self._safe_after(
                self._on_resume_match_complete, result_text, job_desc, resume, None
            )
        except Exception as e:
            self._safe_after(
                self._on_resume_match_complete, "", job_desc, resume, str(e)
            )

    def _on_resume_match_complete(
        self, result_text: str, job_desc: str, resume: str, error: Optional[str]
    ):
        """简历匹配完成回调。"""
        self._finish_resume_match(result_text, job_desc, resume, error)

    def _on_company_research(self, company_name: str):
        """公司调研处理。"""
        config = self._validate_company_research_config()
        if not config:
            self.company_research_widget.set_researching(False)
            self.company_research_widget.clear_result()
            return
        url, key, model, tavily_key = config

        if self._company_research_thread and self._company_research_thread.is_alive():
            messagebox.showwarning("提示", "上一次调研仍在进行中，请稍候")
            self.company_research_widget.set_researching(False)
            self.company_research_widget.clear_result()
            return

        self._start_company_research()
        self._run_threaded_task(
            "_company_research_thread",
            self._do_company_research,
            (url, key, model, tavily_key, company_name),
        )

    def _do_company_research(
        self, url: str, key: str, model: str, tavily_key: str, company_name: str
    ):
        """后台公司调研任务。"""
        try:
            llm_client = self._create_llm_client(url, key, model, 120)
            research_client = CompanyResearchClient(
                tavily_api_key=tavily_key, llm_client=llm_client
            )
            result = research_client.research(company_name)
            self._safe_after(
                self._on_company_research_complete, company_name, None, result
            )
        except Exception as e:
            self._safe_after(
                self._on_company_research_complete, company_name, str(e), ""
            )

    def _on_company_research_complete(
        self, company_name: str, error: Optional[str], result: str = ""
    ):
        """公司调研完成回调。"""
        self._finish_company_research(company_name, error, result)

    def _update_company_list(self):
        """更新岗位分析的公司调研列表。"""
        records = self.company_history_manager.get_all()
        company_titles = []
        seen_titles = set()

        for record in records:
            title = record.title.strip()
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)
            company_titles.append(title)
            if len(company_titles) >= self.MAX_COMPANY_OPTIONS:
                break

        company_list = ["不使用"] + company_titles
        self.job_analysis_widget.update_company_options(company_list)

    def _make_job_option_label(self, record, index: int) -> str:
        """为岗位下拉框生成稳定且不易冲突的展示文案。"""
        base_title = (
            record.title[:30] + "..." if len(record.title) > 30 else record.title
        )
        time_suffix = record.created_at[5:16] if record.created_at else str(index + 1)
        return "{}  [{}]".format(base_title, time_suffix)

    def _update_resume_job_list(self):
        """更新简历匹配的岗位列表。"""
        records = self.job_history_manager.get_all()
        if not records:
            self.resume_match_widget.update_job_list(["请先分析岗位"], {})
            return

        recent_records = records[: self.MAX_JOB_OPTIONS]
        job_list = []
        job_data_map = {}
        for index, record in enumerate(recent_records):
            label = self._make_job_option_label(record, index)
            job_list.append(label)
            job_data_map[label] = record.jd_text

        self.resume_match_widget.update_job_list(job_list, job_data_map)

    def _open_job_history_picker(self):
        """打开岗位分析历史选择器。"""
        dialog = HistoryPickerDialog(
            self,
            title="选择岗位分析历史",
            records=self.job_history_manager.get_all(),
            on_select=self._on_job_history_selected,
            empty_text="暂无岗位分析历史，可先去岗位分析页生成记录。",
            theme=self.FIXED_THEME,
        )
        dialog.focus()

    def _open_company_history_picker(self):
        """打开公司调研历史选择器。"""
        dialog = HistoryPickerDialog(
            self,
            title="选择公司调研历史",
            records=self.company_history_manager.get_all(),
            on_select=self._on_company_history_selected,
            empty_text="暂无公司调研历史，可先去公司调研页生成记录。",
            theme=self.FIXED_THEME,
        )
        dialog.focus()

    def _on_company_history_selected(self, record):
        """从历史选择公司调研后，更新岗位分析快捷选择。"""
        current_values = [
            item
            for item in self.job_analysis_widget.company_combo.cget("values")
            if item != "不使用"
        ]
        values = [record.title] + [
            item for item in current_values if item != record.title
        ]
        values = ["不使用"] + values[: self.MAX_COMPANY_OPTIONS]
        self.job_analysis_widget.update_company_options(values)
        self.job_analysis_widget.set_selected_company(record.title)

    def _on_job_history_selected(self, record):
        """从历史选择岗位后，更新简历匹配快捷选择。"""
        label = self._make_job_option_label(record, 0)
        current_values = [
            item for item in self.resume_match_widget.job_list if item != "请先分析岗位"
        ]
        current_map = dict(self.resume_match_widget.job_data_map)

        if label not in current_map:
            current_values = [label] + [
                item for item in current_values if item != label
            ]
        current_map[label] = record.jd_text

        values = current_values[: self.MAX_JOB_OPTIONS] or ["请先分析岗位"]
        filtered_map = {
            item: current_map[item] for item in values if item in current_map
        }
        self.resume_match_widget.update_job_list(values, filtered_map)
        self.resume_match_widget.job_combo.set(label)

    def _set_status(self, text: str):
        """设置状态栏文本。"""
        self.status_label.configure(text=text)

    def on_closing(self):
        """安全关闭。"""
        self._stop_event.set()

        if self._analysis_thread and self._analysis_thread.is_alive():
            self._analysis_thread.join(timeout=3.0)
        if self._resume_match_thread and self._resume_match_thread.is_alive():
            self._resume_match_thread.join(timeout=3.0)
        if self._company_research_thread and self._company_research_thread.is_alive():
            self._company_research_thread.join(timeout=3.0)

        if hasattr(self, "job_analysis_widget"):
            self.job_analysis_widget.clear_result()
        if hasattr(self, "resume_match_widget"):
            self.resume_match_widget.clear_result()
        if hasattr(self, "company_research_widget"):
            self.company_research_widget.clear_result()

        self.destroy()
