"""主窗口 UI 模块。"""

import json
import re
import threading
import os
from tkinter import TclError, messagebox
from typing import Optional
from tkinter import filedialog

import customtkinter as ctk

from ..core.batch_match_service import BatchMatchService
from ..core.candidate_excel_service import CandidateExcelService
from ..core.company_research_client import CompanyResearchClient
from ..core.config import ConfigManager
from ..core.database import DatabaseManager
from ..core.history import HistoryManager
from ..core.liepin_browser import LiepinBrowserManager
from ..core.match_criteria_service import MatchCriteriaService
from ..core.liepin_resume_extractor import LiepinResumeExtractor
from ..core.liepin_search_service import LiepinSearchService
from ..core.liepin_search_task_service import LiepinSearchTaskService
from ..core.llm_client import (
    AuthError,
    LLMClient,
    LLMClientError,
    NetworkError,
    TimeoutError,
)
from ..core.prompt import RESUME_MATCH_PROMPT
from ..core.search_strategy_service import SearchStrategyService
from ..core.search_task_repository import SearchTaskRepository
from ..core.task_queue import TaskCategory, TaskQueue
from ..models import MatchCriteria
from .batch_match_widget import BatchMatchWidget
from .task_panel import TaskPanel
from ..utils.helpers import validate_api_key, validate_url
from .candidate_library_widget import CandidateLibraryWidget
from .company_research_widget import CompanyResearchWidget
from .history_picker import HistoryPickerDialog
from .selector_dialog import SelectorDialog
from .job_analysis_widget import JobAnalysisWidget
from .match_criteria_widget import MatchCriteriaWidget
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
        self.database_manager = DatabaseManager()
        self.search_task_repository = SearchTaskRepository(self.database_manager)
        self.candidate_excel_service = CandidateExcelService()
        self.search_strategy_service = SearchStrategyService()
        self.liepin_browser_manager = LiepinBrowserManager(self.config_manager)
        self.liepin_search_service = LiepinSearchService(self.liepin_browser_manager)
        self.liepin_resume_extractor = LiepinResumeExtractor()
        self.liepin_search_task_service = LiepinSearchTaskService(
            task_repository=self.search_task_repository,
            candidate_excel_service=self.candidate_excel_service,
            search_service=self.liepin_search_service,
            resume_extractor=self.liepin_resume_extractor,
        )

        self.title("智能岗位分析与寻访助手")
        self.geometry("1300x900")
        self.minsize(1000, 700)

        self.config_manager.update(theme=self.FIXED_THEME)
        ctk.set_appearance_mode(self.FIXED_THEME)
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=self.SURFACE_COLORS["app"])

        self._analysis_thread: Optional[threading.Thread] = None
        self._auto_pipeline_thread: Optional[threading.Thread] = None
        self._resume_match_thread: Optional[threading.Thread] = None
        self._company_research_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.task_queue = TaskQueue(self)

        self._raw_result = ""
        self._current_jd = ""
        self._candidate_job_map = {}
        self._current_candidate_excel_path = ""
        self._last_analysis_llm_config = None

        self._build_ui()
        self._load_config_to_ui()
        self._update_resume_job_list()
        self._update_company_list()
        self._update_match_criteria_job_list()
        self._update_candidate_job_list()
        self._update_batch_job_list()

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
        config_frame.grid_columnconfigure(1, weight=2)
        config_frame.grid_columnconfigure(3, weight=3)

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
        badge.grid(row=0, column=4, padx=(10, 16), pady=(16, 6), sticky="e")

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
            row=2, column=0, padx=(16, 5), pady=(0, 16), sticky="w"
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
        self.model_entry.grid(row=2, column=1, padx=5, pady=(0, 16), sticky="w")

        ctk.CTkLabel(config_frame, text="Tavily Key:").grid(
            row=2, column=2, padx=(20, 5), pady=(0, 16), sticky="w"
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
            row=2, column=3, padx=5, pady=(0, 16), sticky="ew"
        )

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
        self.save_btn.grid(row=2, column=4, padx=(20, 10), pady=(0, 16))

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
        self.tab_criteria = self.tabview.add("匹配条件")
        self.tab_resume = self.tabview.add("简历匹配")
        self.tab_candidates = self.tabview.add("候选人抓取")
        self.tab_batch = self.tabview.add("批量匹配")

        self._build_company_research_tab()
        self._build_job_analysis_tab()
        self._build_match_criteria_tab()
        self._build_resume_match_tab()
        self._build_candidate_library_tab()
        self._build_batch_match_tab()

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
            on_send_to_candidates=self._send_analysis_to_candidates,
            on_auto_search_candidates=self._start_auto_capture_from_analysis,
            on_pick_company_history=self._open_company_history_picker,
            on_history_changed=self._update_company_list,
            on_save_match_criteria=self._on_save_match_criteria,
            theme=self.FIXED_THEME,
        )
        self.job_analysis_widget.grid(
            row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5
        )

    def _build_match_criteria_tab(self):
        """构建独立匹配条件确认标签页。"""
        self.tab_criteria.grid_columnconfigure(0, weight=1)
        self.tab_criteria.grid_rowconfigure(0, weight=1)
        self.match_criteria_widget = MatchCriteriaWidget(
            self.tab_criteria,
            on_pick_job_history=self._open_job_history_picker,
            on_save=self._on_save_match_criteria_from_tab,
            theme=self.FIXED_THEME,
        )
        self.match_criteria_widget.grid(row=0, column=0, sticky="nsew")

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

    def _build_candidate_library_tab(self):
        """构建候选人抓取标签页。"""
        self.tab_candidates.grid_columnconfigure(0, weight=2)
        self.tab_candidates.grid_columnconfigure(1, weight=3)
        self.tab_candidates.grid_rowconfigure(0, weight=1)

        self.candidate_library_widget = CandidateLibraryWidget(
            self.tab_candidates,
            on_launch_browser=self._on_launch_liepin_browser,
            on_check_login=self._on_check_liepin_login,
            on_run_task=self._on_run_candidate_task,
            on_import_excel=self._on_import_candidate_excel,
            on_open_excel=self._on_open_candidate_excel,
            on_open_excel_dir=self._on_open_candidate_excel_dir,
            on_export_debug=self._on_export_liepin_debug,
            on_close_browser=self._on_close_liepin_browser,
            on_pick_job_history=self._open_job_history_picker,
            theme=self.FIXED_THEME,
        )
        self.candidate_library_widget.grid(
            row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5
        )

    def _build_batch_match_tab(self):
        """构建批量匹配标签页。"""
        self.tab_batch.grid_columnconfigure(0, weight=2)
        self.tab_batch.grid_columnconfigure(1, weight=3)
        self.tab_batch.grid_rowconfigure(0, weight=1)

        self.batch_match_widget = BatchMatchWidget(
            self.tab_batch,
            on_run_batch=self._on_run_batch_match,
            on_cancel_batch=self._on_cancel_batch_match,
            on_load_recent_batch=self._on_import_candidate_excel,
            on_open_excel=self._on_open_candidate_excel,
            on_open_excel_dir=self._on_open_candidate_excel_dir,
            on_pick_job_history=self._open_job_history_picker,
            theme=self.FIXED_THEME,
        )
        self.batch_match_widget.grid(
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

        self.task_panel_btn = ctk.CTkButton(
            status_frame,
            text="后台任务",
            width=90,
            height=30,
            corner_radius=12,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._open_task_panel,
        )
        self.task_panel_btn.grid(row=0, column=2, padx=10, pady=5, sticky="e")

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

    def _build_candidate_job_payload(self, record) -> dict:
        """为候选人抓取页构建岗位与搜索策略数据。"""
        strategy = self.search_strategy_service.build_from_analysis_result(
            "{}\n{}".format(record.result or "", record.jd_text or "")
        )
        strategy_payload = self.search_strategy_service.to_payload(strategy)
        return {
            "record_id": record.id,
            "title": record.title,
            "job_description": record.jd_text,
            "analysis_result": record.result,
            "strategy": strategy_payload,
            "strategy_round_count": len(strategy_payload.get("executable_rounds", [])),
            "match_criteria": record.match_criteria_json or "",
        }

    def _run_threaded_task(self, thread_attr: str, target, args: tuple):
        """启动后台线程任务。"""
        thread = threading.Thread(target=target, args=args, daemon=True)
        setattr(self, thread_attr, thread)
        thread.start()

    @staticmethod
    def _extract_match_criteria_json(html_text: str) -> str:
        """Extract trailing JSON from analysis result if present."""
        if not html_text:
            return ""
        for pattern in (
            r"```json\s*(\{.*\})\s*```\s*$",
            r"<(?:pre|code)[^>]*>(\{.*\})</(?:pre|code)>\s*$",
            r"(\{.*\})\s*$",
        ):
            m = re.search(pattern, html_text, re.DOTALL | re.IGNORECASE)
            if m:
                try:
                    data = json.loads(m.group(1))
                    if isinstance(data, dict) and "core_requirements" in data:
                        return m.group(1)
                except (ValueError, TypeError):
                    continue
        return ""

    def _on_save_match_criteria(self, criteria):
        """Save edited match criteria to the latest job history record."""
        if not self._raw_result or not self._current_jd:
            return
        target = None
        for record in self.job_history_manager.get_all():
            if record.jd_text == self._current_jd and record.result == self._raw_result:
                target = record
                break
        if target is None:
            target = self.job_history_manager.save_record(
                self._current_jd, self._raw_result
            )
        target.match_criteria_json = json.dumps(criteria.to_dict(), ensure_ascii=False)
        target.match_criteria_confirmed = True
        self.job_history_manager.repository.upsert(target)
        self._update_resume_job_list()
        self._update_match_criteria_job_list(selected_record=target)
        self._update_candidate_job_list()
        self._update_batch_job_list()

    def _on_save_match_criteria_from_tab(self, job_label: str, payload: dict, criteria):
        """Save edited match criteria from the standalone match criteria tab."""
        record = self.job_history_manager.get_by_id(payload.get("record_id", ""))
        if record is None:
            messagebox.showwarning("提示", "未找到对应岗位记录")
            return
        record.match_criteria_json = json.dumps(criteria.to_dict(), ensure_ascii=False)
        record.match_criteria_confirmed = True
        self.job_history_manager.repository.upsert(record)
        self._raw_result = record.result
        self._current_jd = record.jd_text
        self.job_analysis_widget.set_match_criteria(criteria)
        self._update_match_criteria_job_list(selected_record=record)
        self._update_candidate_job_list(selected_record=record)
        self._update_batch_job_list(selected_record=record)

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
            return None

        self.job_analysis_widget.set_result(self._raw_result)
        record = None
        if self._current_jd and self._raw_result:
            record = self.job_history_manager.save_record(
                self._current_jd, self._raw_result
            )
            match_criteria_json = self._extract_match_criteria_json(self._raw_result)
            if match_criteria_json:
                record.match_criteria_json = match_criteria_json
                self.job_history_manager.repository.upsert(record)
            self._update_resume_job_list()
            self._update_match_criteria_job_list(selected_record=record)
            self._update_candidate_job_list()
            self._update_batch_job_list()
        self._set_status("岗位分析完成，结果已保存到历史记录")
        return record

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
        self._last_analysis_llm_config = config

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
        record = self._finish_job_analysis(error)
        if record is not None and error is None:
            self._start_auto_pipeline_after_analysis(record)

    def _start_auto_pipeline_after_analysis(self, record):
        """Continue analysis -> criteria generation -> candidate capture automatically."""
        self.tabview.set("匹配条件")
        self._update_match_criteria_job_list(selected_record=record)
        self._set_status("岗位分析完成，正在单独生成匹配条件...")
        config = self._last_analysis_llm_config or self._get_valid_llm_config_silent()
        if not config:
            criteria = MatchCriteriaService.build_fallback(record.jd_text)
            self._on_auto_match_criteria_complete(record.id, criteria, None)
            return
        self._run_threaded_task(
            "_auto_pipeline_thread",
            self._do_auto_match_criteria,
            (record.id, config),
        )

    def _do_auto_match_criteria(self, record_id: str, config):
        """Generate match criteria in a dedicated background API call."""
        try:
            record = self.job_history_manager.get_by_id(record_id)
            if record is None:
                raise RuntimeError("未找到岗位记录")
            url, key, model = config
            client = self._create_llm_client(url, key, model, self.config_manager.config.timeout)
            service = MatchCriteriaService(client)
            criteria = service.generate(record.result, record.jd_text)
            self._safe_after(
                self._on_auto_match_criteria_complete, record_id, criteria, None
            )
        except Exception as exc:
            self._safe_after(
                self._on_auto_match_criteria_complete, record_id, None, str(exc)
            )

    def _on_auto_match_criteria_complete(
        self, record_id: str, criteria: Optional[MatchCriteria], error: Optional[str]
    ):
        """Persist generated criteria and move into candidate capture."""
        record = self.job_history_manager.get_by_id(record_id)
        if record is None:
            messagebox.showwarning("提示", "匹配条件生成后未找到岗位记录")
            return
        if criteria is None:
            criteria = MatchCriteriaService.build_fallback(record.jd_text)
            self._set_status("匹配条件 API 生成失败，已使用保底标准继续自动流程")
        else:
            self._set_status("匹配条件已生成，准备进入候选人抓取")
        if error:
            # Keep the chain moving, but leave a visible breadcrumb in the status bar.
            self._set_status("匹配条件 API 生成失败，已使用保底标准继续自动流程：{}".format(error))

        record.match_criteria_json = json.dumps(criteria.to_dict(), ensure_ascii=False)
        record.match_criteria_confirmed = True
        self.job_history_manager.repository.upsert(record)
        self.job_analysis_widget.set_match_criteria(criteria)
        self._update_match_criteria_job_list(selected_record=record)
        self._update_candidate_job_list(selected_record=record)
        self._update_batch_job_list(selected_record=record)
        self.after(500, lambda: self._continue_to_candidate_capture(record))

    def _continue_to_candidate_capture(self, record):
        """Switch to candidate capture and open the 15-second confirmation dialog."""
        self._update_candidate_job_list(selected_record=record)
        self.tabview.set("候选人抓取")
        self._set_status("已进入候选人抓取，等待 15 秒确认后自动开始")
        if hasattr(self, "candidate_library_widget"):
            self.candidate_library_widget.run_selected_task()

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

    def _on_launch_liepin_browser(self):
        """启动猎聘浏览器（在后台线程执行，避免 UI 卡死）。"""
        import threading

        def _run():
            try:
                self.liepin_browser_manager.launch()
                state = self.liepin_browser_manager.open_search_page()
                self.after(
                    0,
                    lambda: self.candidate_library_widget.set_browser_state(
                        "浏览器已启动并打开找简历页，用户目录：{}".format(state.profile_dir)
                    ),
                )
                self.after(
                    0, lambda: self._set_status("猎聘浏览器已启动并导航到找简历页")
                )
            except Exception as exc:
                self.after(
                    0, lambda exc=exc: messagebox.showerror("浏览器启动失败", str(exc))
                )
                self.after(0, lambda: self._set_status("猎聘浏览器启动失败"))

        threading.Thread(target=_run, daemon=True).start()

    def _on_check_liepin_login(self):
        """检查猎聘登录状态（在后台线程执行，避免 UI 卡死）。"""
        import threading

        def _run():
            try:
                self.liepin_browser_manager.launch()
                state = self.liepin_browser_manager.get_state()
                # 如果浏览器刚被重新打开，默认页面是 about:blank，此时导航到搜索页
                # 以免用户看到空白页面。
                if not state.current_url or state.current_url.lower() in ("about:blank", ""):
                    state = self.liepin_browser_manager.open_search_page()
                text = (
                    "猎聘已登录，可手动搜索后执行结果页入库。"
                    if state.logged_in
                    else "猎聘未登录，请先在浏览器中手动登录。"
                )
                self.after(0, lambda: self.candidate_library_widget.set_browser_state(text))
                self.after(0, lambda: self._set_status(text))
            except Exception as exc:
                self.after(
                    0, lambda exc=exc: messagebox.showerror("登录检查失败", str(exc))
                )
                self.after(0, lambda: self._set_status("猎聘登录检查失败"))

        threading.Thread(target=_run, daemon=True).start()

    def _on_export_liepin_debug(self):
        """导出当前猎聘页面结构（在后台线程执行，避免 UI 卡死）。"""
        import threading

        def _run():
            try:
                self.liepin_browser_manager.launch()
                debug_path = self.liepin_browser_manager.export_debug_snapshot(
                    "manual_debug"
                )
                self.after(
                    0,
                    lambda: self.candidate_library_widget.set_browser_state(
                        "已导出页面诊断文件：{}".format(debug_path)
                    ),
                )
                self.after(0, lambda: self._set_status("猎聘页面诊断文件已导出"))
                self.after(
                    0,
                    lambda: messagebox.showinfo(
                        "成功", "页面诊断文件已导出:\n{}".format(debug_path)
                    ),
                )
            except Exception as exc:
                self.after(0, lambda exc=exc: messagebox.showerror("导出失败", str(exc)))
                self.after(0, lambda: self._set_status("导出页面诊断失败"))

        threading.Thread(target=_run, daemon=True).start()

    def _on_close_liepin_browser(self):
        """安全关闭猎聘浏览器，保留 worker 线程以便下次重启。"""
        try:
            self.liepin_browser_manager.close_browser()
            self.candidate_library_widget.set_browser_state("浏览器已安全关闭")
            self._set_status("猎聘浏览器已关闭")
        except Exception as exc:
            messagebox.showerror("关闭失败", str(exc))
            self._set_status("猎聘浏览器关闭失败")

    def _send_analysis_to_candidates(self, jd_text: str, analysis_result: str):
        """将当前岗位分析结果同步到候选人抓取页。"""
        target_record = self._resolve_analysis_record(jd_text, analysis_result)
        if target_record is None:
            messagebox.showwarning("提示", "未找到对应岗位记录，请先保存分析结果后再试")
            return

        self._update_candidate_job_list(selected_record=target_record)
        self._update_match_criteria_job_list(selected_record=target_record)
        self.tabview.set("候选人抓取")
        self._set_status("已将岗位分析同步到候选人抓取页")

    def _start_auto_capture_from_analysis(self, jd_text: str, analysis_result: str):
        """从当前分析结果或历史岗位直接启动自动搜索与抓取。"""
        target_record = self._resolve_analysis_record(jd_text, analysis_result)
        if target_record is None:
            messagebox.showwarning("提示", "未找到对应岗位记录，请先保存或重新加载该岗位分析")
            return

        self._update_candidate_job_list(selected_record=target_record)
        self._update_match_criteria_job_list(selected_record=target_record)
        self._update_batch_job_list(selected_record=target_record)
        self._continue_to_candidate_capture(target_record)

    def _resolve_analysis_record(self, jd_text: str, analysis_result: str):
        """Find or persist the analysis record backing a UI action."""
        target_record = None
        for record in self.job_history_manager.get_all():
            if record.jd_text == jd_text and record.result == analysis_result:
                target_record = record
                break

        if (
            target_record is None
            and self._current_jd == jd_text
            and self._raw_result == analysis_result
        ):
            target_record = self.job_history_manager.save_record(
                jd_text, analysis_result
            )
            self._update_resume_job_list()
            self._update_match_criteria_job_list(selected_record=target_record)
        return target_record

    def _on_run_candidate_task(
        self,
        job_label: str,
        payload: dict,
        filters: dict,
        max_candidates: int,
        max_pages: int,
    ):
        """创建并提交当前结果页入库任务到后台队列。"""
        strategy = dict(payload["strategy"] or {})
        strategy["filters"] = dict(filters or {})
        strategy["per_round_limit"] = 30
        search_task = self.search_task_repository.create(
            job_history_id=payload["record_id"],
            task_name="{} - 猎聘结果页入库".format(payload["title"]),
            keywords=strategy,
            max_pages=max_pages,
            max_candidates=max_candidates,
        )
        auto_match_config = self._get_valid_llm_config_silent()
        auto_match_workers = (
            self.batch_match_widget.get_concurrency()
            if hasattr(self, "batch_match_widget")
            else BatchMatchService.DEFAULT_WORKERS
        )
        task_name = "结果页入库 - {}".format(payload["title"])
        task_id = self.task_queue.submit(
            name=task_name,
            category=TaskCategory.BROWSER,
            target=self._do_candidate_task,
            args=(search_task.id, payload, auto_match_config, auto_match_workers),
            on_complete=self._on_candidate_task_complete,
        )
        self.candidate_library_widget.set_running(True, task_id)
        self._set_status("已创建后台任务：{}".format(task_name))

    def _do_candidate_task(
        self,
        queue_task_id: str,
        cancel_event,
        task_info,
        search_task_id: str,
        payload: dict,
        auto_match_config,
        auto_match_workers: int,
    ):
        """后台执行当前结果页入库任务。"""
        try:
            task_info.auto_batch_task_ids = []

            def on_round_complete(excel_path, round_index, round_info, row_indexes, round_stats, search_task):
                batch_task_id = self._submit_round_batch_match(
                    payload=payload,
                    excel_path=excel_path,
                    round_index=round_index,
                    round_info=round_info,
                    row_indexes=row_indexes,
                    auto_match_config=auto_match_config,
                    max_workers=auto_match_workers,
                )
                if batch_task_id:
                    task_info.auto_batch_task_ids.append(batch_task_id)

            def on_all_complete(summary_obj, _search_task):
                task_info.all_complete_summary = summary_obj

            summary = self.liepin_search_task_service.run_task(
                search_task_id,
                cancel_event=cancel_event,
                on_round_complete=on_round_complete,
                on_all_complete=on_all_complete,
            )
            candidate_payload = self._build_candidate_excel_payloads(
                self.candidate_excel_service.load_candidates(summary.excel_path)
            )
            failed_preview = ""
            if summary.failed_candidates:
                failed_lines = []
                for item in summary.failed_candidates[:3]:
                    failed_lines.append(
                        "第{}页-第{}位 {}：{}".format(
                            item.get("page_number", "?"),
                            item.get("rank_index", "?"),
                            item.get("name")
                            or item.get("identifier")
                            or "未命名候选人",
                            item.get("reason", "处理失败"),
                        )
                    )
                failed_preview = "\n失败示例：{}".format("；".join(failed_lines))
            round_preview = ""
            if summary.query_level_stats:
                round_lines = []
                for item in summary.query_level_stats[:4]:
                    round_lines.append(
                        "{}：{}，页数 {}，原始 {}，收录 {}，去重 {}".format(
                            item.get("label") or "搜索轮次",
                            item.get("query") or "",
                            item.get("pages_processed", 0),
                            item.get("raw_candidates", 0),
                            item.get("accepted_candidates", 0),
                            item.get("deduplicated_candidates", 0),
                        )
                    )
                round_preview = "\n轮次统计：{}".format("；".join(round_lines))
            summary_text = (
                "结果页入库完成：已处理 {} 页，来源标签 {} 个，收录线索 {} 位，完整简历 {} 位，待补抓 {} 位，失败 {} 位。\nExcel 文件：{}".format(
                    summary.pages_processed,
                    len(summary.processed_keywords),
                    summary.sourced_candidate_count,
                    summary.enriched_candidate_count,
                    summary.partial_candidate_count,
                    summary.failed_candidate_count,
                    summary.excel_path,
                )
                + round_preview
                + failed_preview
            )
            task_info.summary = summary
            task_info.candidate_payload = candidate_payload
            task_info.payload = payload
            task_info.summary_text = summary_text
        except Exception as exc:
            task_info.error_message = str(exc)
            raise

    def _get_valid_llm_config_silent(self):
        """Return LLM config without showing UI warnings."""
        url, key, model = self._get_llm_config()
        if not url or not key:
            return None
        if not validate_url(url) or not validate_api_key(key):
            return None
        return url, key, model

    def _load_match_criteria_from_payload(self, payload: dict) -> Optional[MatchCriteria]:
        mc_json = payload.get("match_criteria", "") if payload else ""
        if mc_json:
            try:
                return MatchCriteria.from_dict(json.loads(mc_json))
            except (ValueError, TypeError):
                pass
        record = self.job_history_manager.get_by_id(payload.get("record_id", ""))
        if record and record.match_criteria_json:
            try:
                return MatchCriteria.from_dict(json.loads(record.match_criteria_json))
            except (ValueError, TypeError):
                return None
        return None

    def _submit_round_batch_match(
        self,
        payload: dict,
        excel_path: str,
        round_index: int,
        round_info: dict,
        row_indexes: list,
        auto_match_config,
        max_workers: int,
    ) -> str:
        """Submit one background batch match task for the rows captured in a round."""
        if not auto_match_config:
            return ""
        candidates = self.candidate_excel_service.load_matchable_candidates_by_rows(
            excel_path, row_indexes
        )
        if not candidates:
            return ""
        match_criteria = self._load_match_criteria_from_payload(payload)
        url, key, model = auto_match_config
        task_name = "自动批量匹配 - 第{}轮 - {}".format(
            round_index, round_info.get("query") or round_info.get("label") or payload.get("title", "")
        )
        return self.task_queue.submit(
            name=task_name,
            category=TaskCategory.COMPUTE,
            target=self._do_batch_match,
            args=(url, key, model, payload, excel_path, candidates, match_criteria, max_workers),
        )

    def _on_candidate_task_complete(self, task):
        """结果页入库任务完成回调。"""
        self.candidate_library_widget.set_running(False)
        if task.status.value == "cancelled":
            self._set_status("结果页入库已取消")
            self.candidate_library_widget.set_task_result("", "任务已取消")
            return
        if task.status.value == "failed":
            messagebox.showerror("结果页入库失败", task.error_message)
            self._set_status("结果页入库失败")
            self.candidate_library_widget.set_task_result("", "任务失败：{}".format(task.error_message))
            return

        summary = getattr(task, "summary", None)
        candidate_payload = getattr(task, "candidate_payload", [])
        summary_text = getattr(task, "summary_text", "")
        excel_path = summary.excel_path if summary else ""
        search_task_id = summary.task_id if summary else ""

        self._current_candidate_excel_path = excel_path
        self.candidate_library_widget.set_task_result(search_task_id, summary_text)
        self.candidate_library_widget.set_excel_file(excel_path)
        self.candidate_library_widget.set_candidate_records(candidate_payload)
        self.batch_match_widget.set_excel_file(
            excel_path,
            self.candidate_excel_service.count_matchable_candidates(excel_path),
        )
        self._set_status("结果页入库完成")

    def _on_run_batch_match(self, job_label: str, payload: dict):
        """发起批量匹配任务。"""
        excel_path = self.batch_match_widget.get_excel_file()
        if self._has_running_batch_match_for_excel(excel_path):
            messagebox.showwarning("提示", "当前 Excel 已有批量匹配任务在后台执行，请等待完成")
            return

        config = self._validate_llm_config()
        if not config:
            return
        url, key, model = config

        if not excel_path:
            messagebox.showwarning("提示", "请先导入候选人 Excel 文件")
            return

        candidates = self.candidate_excel_service.load_matchable_candidates(excel_path)
        if not candidates:
            messagebox.showwarning("提示", "当前 Excel 中没有可匹配候选人")
            return

        match_criteria = None
        mc_json = payload.get("match_criteria", "")
        if mc_json:
            try:
                match_criteria = MatchCriteria.from_dict(json.loads(mc_json))
            except (ValueError, TypeError):
                match_criteria = None
        if match_criteria is None:
            record = self.job_history_manager.get_by_id(payload.get("record_id", ""))
            if record and record.match_criteria_json:
                try:
                    match_criteria = MatchCriteria.from_dict(
                        json.loads(record.match_criteria_json)
                    )
                except (ValueError, TypeError):
                    match_criteria = None

        max_workers = self.batch_match_widget.get_concurrency()
        task_name = "批量匹配 - {}".format(job_label)
        task_id = self.task_queue.submit(
            name=task_name,
            category=TaskCategory.COMPUTE,
            target=self._do_batch_match,
            args=(url, key, model, payload, excel_path, candidates, match_criteria, max_workers),
            on_update=self._on_batch_match_task_update,
            on_complete=self._on_batch_match_task_complete,
        )
        self.batch_match_widget.set_running(True, task_id)
        self._set_status("已创建后台任务：{}".format(task_name))

    def _do_batch_match(
        self,
        task_id: str,
        cancel_event,
        task_info,
        url: str,
        key: str,
        model: str,
        payload: dict,
        excel_path: str,
        candidates: list,
        match_criteria: Optional[MatchCriteria],
        max_workers: int,
    ):
        """后台执行批量匹配任务。"""
        try:
            task_info.excel_path = excel_path
            if cancel_event.is_set():
                raise RuntimeError("用户已取消批量匹配")

            client_factory = lambda: self._create_llm_client(url, key, model, 180)
            service = BatchMatchService(
                None,
                llm_client=None,
                llm_client_factory=client_factory,
                max_workers=max_workers,
            )

            def progress_callback(current, total, candidate):
                if cancel_event.is_set():
                    return
                candidate_name = getattr(candidate, "name", "") or "未命名候选人"
                self.task_queue.update_progress(
                    task_id, current, total, candidate_name
                )

            results = service.match_excel_candidates(
                payload["job_description"],
                candidates,
                match_criteria=match_criteria,
                progress_callback=progress_callback,
            )
            if cancel_event.is_set():
                raise RuntimeError("用户已取消批量匹配")

            result_payload = []
            for result in results:
                self.candidate_excel_service.write_match_result(
                    excel_path,
                    result.row_index,
                    result.tier,
                    result.detail,
                )
                result_payload.append(
                    {
                        "result_id": str(result.row_index),
                        "candidate_id": str(result.row_index),
                        "candidate_name": result.candidate_name,
                        "tier": result.tier or "待解析",
                        "core_met_count": result.core_met_count,
                        "core_total": result.core_total,
                        "dealbreaker_hit": result.dealbreaker_hit,
                        "recommendation": result.recommendation or "待解析",
                        "summary": result.summary or "",
                        "risks": result.risks or "",
                        "match_detail": result.detail,
                        "inferred_abilities": result.inferred_abilities or "",
                    }
                )
            task_info.result_payload = result_payload
            task_info.summary_text = "批量匹配完成：共处理 {} 位候选人，结果已回写 Excel。\nExcel 文件：{}".format(
                len(result_payload), excel_path
            )
        except Exception as exc:
            task_info.error_message = str(exc)
            raise

    def _on_batch_match_task_update(self, task):
        """Update UI when batch match task reports progress."""
        self.batch_match_widget.set_progress(
            task.progress_current, task.progress_total, task.progress_message
        )
        self._set_status(
            "批量匹配进行中：{}/{}，当前处理 {}".format(
                task.progress_current,
                task.progress_total,
                task.progress_message or "未命名候选人",
            )
        )

    def _on_cancel_batch_match(self):
        """Request soft cancellation for the current batch match."""
        task_id = self.batch_match_widget.get_current_task_id()
        if task_id:
            self.task_queue.cancel_task(task_id)
            self.batch_match_widget.info_label.configure(
                text="已请求取消，等待当前候选人处理结束..."
            )
            self._set_status("正在取消批量匹配...")

    def _on_batch_match_task_complete(self, task):
        """批量匹配任务完成回调。"""
        self.batch_match_widget.set_running(False)
        if task.status.value == "cancelled":
            self._set_status("批量匹配已取消")
            self.batch_match_widget.set_results("任务已取消")
            return
        if task.status.value == "failed":
            messagebox.showerror("批量匹配失败", task.error_message)
            self._set_status("批量匹配失败")
            self.batch_match_widget.set_results("任务失败：{}".format(task.error_message))
            return

        excel_path = getattr(task, "excel_path", "")
        result_payload = getattr(task, "result_payload", [])
        summary_text = getattr(task, "summary_text", "")

        self._current_candidate_excel_path = excel_path
        self.batch_match_widget.set_excel_file(
            excel_path,
            self.candidate_excel_service.count_matchable_candidates(excel_path),
        )
        if result_payload:
            self.batch_match_widget.set_match_results(result_payload)
        else:
            self.batch_match_widget.set_results(summary_text)
        self._set_status("批量匹配完成")

    def _on_import_candidate_excel(self):
        file_path = filedialog.askopenfilename(
            title="选择候选人 Excel",
            filetypes=[("Excel 文件", "*.xlsx")],
            initialdir=os.path.join(os.getcwd(), "exports", "candidates"),
        )
        if not file_path:
            return

        records = self.candidate_excel_service.load_candidates(file_path)
        candidate_payload = self._build_candidate_excel_payloads(records)
        summary = "已导入 Excel：{}\n共 {} 位候选人。".format(
            file_path, len(candidate_payload)
        )
        self._current_candidate_excel_path = file_path
        self.candidate_library_widget.set_library_candidates(summary)
        self.candidate_library_widget.set_excel_file(file_path)
        self.candidate_library_widget.set_candidate_records(candidate_payload)
        self.batch_match_widget.set_excel_file(
            file_path,
            self.candidate_excel_service.count_matchable_candidates(file_path),
        )
        self.batch_match_widget.set_results(summary)
        self._set_status("已导入候选人 Excel")

    def _on_open_candidate_excel(self):
        file_path = (
            self.candidate_library_widget.get_excel_file()
            or self.batch_match_widget.get_excel_file()
        )
        if not file_path:
            messagebox.showwarning("提示", "当前没有可打开的 Excel 文件")
            return
        if not os.path.exists(file_path):
            messagebox.showwarning("提示", "Excel 文件不存在：{}".format(file_path))
            return
        os.startfile(file_path)

    def _on_open_candidate_excel_dir(self):
        file_path = (
            self.candidate_library_widget.get_excel_file()
            or self.batch_match_widget.get_excel_file()
        )
        if not file_path:
            messagebox.showwarning("提示", "当前没有可打开目录的 Excel 文件")
            return
        directory = os.path.dirname(file_path)
        if not directory or not os.path.exists(directory):
            messagebox.showwarning("提示", "Excel 文件目录不存在：{}".format(directory))
            return
        os.startfile(directory)

    def _build_candidate_excel_payloads(self, records: list) -> list:
        payloads = []
        for record in records:
            payloads.append(
                {
                    "candidate_id": str(record.row_index),
                    "name": record.name,
                    "profile_url": record.profile_url,
                    "source_keyword": record.source_keyword,
                    "resume_text": record.resume_text,
                    "resume_summary": record.resume_text[:120],
                    "capture_status": record.capture_status,
                    "capture_status_label": record.capture_status,
                    "last_source_at": record.captured_at,
                    "last_enriched_at": record.captured_at,
                }
            )
        return payloads

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

    def _update_candidate_job_list(self, selected_record=None):
        """更新候选人抓取页的岗位来源列表。"""
        records = self.job_history_manager.get_all()
        if not records:
            self._candidate_job_map = {"请先分析岗位": {}}
            if hasattr(self, "candidate_library_widget"):
                self.candidate_library_widget.update_job_options(
                    ["请先分析岗位"], self._candidate_job_map
                )
            return

        job_options = []
        job_data_map = {}
        for index, record in enumerate(records[: self.MAX_JOB_OPTIONS]):
            label = self._make_job_option_label(record, index)
            job_options.append(label)
            job_data_map[label] = self._build_candidate_job_payload(record)

        self._candidate_job_map = job_data_map
        if hasattr(self, "candidate_library_widget"):
            self.candidate_library_widget.update_job_options(job_options, job_data_map)
            if selected_record is not None:
                selected_label = None
                for label, payload in job_data_map.items():
                    if payload.get("record_id") == selected_record.id:
                        selected_label = label
                        break
                if selected_label:
                    self.candidate_library_widget.set_selected_job(selected_label)

    def _update_match_criteria_job_list(self, selected_record=None):
        """更新独立匹配条件页的岗位来源列表。"""
        records = self.job_history_manager.get_all()
        if not records:
            if hasattr(self, "match_criteria_widget"):
                self.match_criteria_widget.update_job_options(["请先分析岗位"], {})
            return

        job_options = []
        job_data_map = {}
        for index, record in enumerate(records[: self.MAX_JOB_OPTIONS]):
            label = self._make_job_option_label(record, index)
            job_options.append(label)
            job_data_map[label] = self._build_candidate_job_payload(record)

        if hasattr(self, "match_criteria_widget"):
            self.match_criteria_widget.update_job_options(job_options, job_data_map)
            if selected_record is not None:
                for label, payload in job_data_map.items():
                    if payload.get("record_id") == selected_record.id:
                        self.match_criteria_widget.set_selected_job(label)
                        break

    def _update_batch_job_list(self, selected_record=None):
        """更新批量匹配页的岗位列表。"""
        records = self.job_history_manager.get_all()
        if not records:
            if hasattr(self, "batch_match_widget"):
                self.batch_match_widget.update_job_options(["请先分析岗位"], {})
            return

        job_options = []
        job_data_map = {}
        for index, record in enumerate(records[: self.MAX_JOB_OPTIONS]):
            label = self._make_job_option_label(record, index)
            job_options.append(label)
            job_data_map[label] = self._build_candidate_job_payload(record)

        if hasattr(self, "batch_match_widget"):
            self.batch_match_widget.update_job_options(job_options, job_data_map)
            if selected_record is not None:
                for label, payload in job_data_map.items():
                    if payload.get("record_id") == selected_record.id:
                        self.batch_match_widget.set_selected_job(label)
                        break

    def _open_job_history_picker(self):
        """打开岗位分析历史选择器。"""
        dialog = SelectorDialog(
            self,
            title="选择岗位分析历史",
            records=self.job_history_manager.get_all(),
            on_select=self._on_job_history_selected,
            empty_text="暂无岗位分析历史，可先去岗位分析页生成记录。",
            get_display_text=lambda r: f"{r.title}  [{r.created_at}]",
        )
        dialog.focus()

    def _open_company_history_picker(self):
        """打开公司调研历史选择器。"""
        dialog = SelectorDialog(
            self,
            title="选择公司调研历史",
            records=self.company_history_manager.get_all(),
            on_select=self._on_company_history_selected,
            empty_text="暂无公司调研历史，可先去公司调研页生成记录。",
            get_display_text=lambda r: f"{r.title}  [{r.created_at}]",
        )
        dialog.focus()

    def _on_company_history_selected(self, record):
        """从历史选择公司调研后，更新岗位分析快捷选择。"""
        current_values = [
            item
            for item in getattr(self.job_analysis_widget, "_company_options", [])
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
        self.resume_match_widget.set_selected_job(label)

        current_candidate_values = [
            item
            for item in self._candidate_job_map.keys()
            if item != "请先分析岗位" and item != label
        ]
        candidate_payload = self._build_candidate_job_payload(record)
        candidate_map = {label: candidate_payload}
        for item in current_candidate_values[: self.MAX_JOB_OPTIONS - 1]:
            if item in self._candidate_job_map:
                candidate_map[item] = self._candidate_job_map[item]
        self._candidate_job_map = candidate_map
        if hasattr(self, "candidate_library_widget"):
            self.candidate_library_widget.update_job_options(
                list(candidate_map.keys()), candidate_map
            )
            self.candidate_library_widget.set_selected_job(label)

        if hasattr(self, "match_criteria_widget"):
            self.match_criteria_widget.update_job_options(
                list(candidate_map.keys()), candidate_map
            )
            self.match_criteria_widget.set_selected_job(label)

        if hasattr(self, "batch_match_widget"):
            self.batch_match_widget.update_job_options(
                list(candidate_map.keys()), candidate_map
            )
            self.batch_match_widget.set_selected_job(label)

        # Also sync to job analysis widget if it has match criteria persisted
        self._raw_result = record.result
        self._current_jd = record.jd_text
        self.job_analysis_widget.set_jd_text(record.jd_text)
        self.job_analysis_widget.set_result(record.result)
        if record.match_criteria_json:
            try:
                mc = MatchCriteria.from_dict(json.loads(record.match_criteria_json))
                self.job_analysis_widget.set_match_criteria(mc)
            except (ValueError, TypeError):
                pass

    def _set_status(self, text: str):
        """设置状态栏文本。"""
        self.status_label.configure(text=text)

    def on_closing(self):
        """安全关闭。"""
        self._stop_event.set()
        self.task_queue.shutdown(wait_seconds=5.0)

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

        try:
            self.liepin_browser_manager.close()
        except Exception:
            pass

        self.destroy()

    def _open_task_panel(self):
        """打开全局后台任务面板。"""
        panel = TaskPanel(self, self.task_queue, on_cancel=self._on_task_cancel)
        panel.focus()

    def _on_task_cancel(self, task_id: str):
        """从全局面板请求取消任务。"""
        self.task_queue.cancel_task(task_id)

    def _has_running_batch_match_for_excel(self, excel_path: str) -> bool:
        """检查是否有针对同一 Excel 的批量匹配任务正在运行。"""
        if not excel_path:
            return False
        for task in self.task_queue.list_tasks():
            if task.category != TaskCategory.COMPUTE:
                continue
            if task.status.value not in ("pending", "running"):
                continue
            task_excel = getattr(task, "excel_path", "")
            if task_excel == excel_path:
                return True
        return False
