"""Auto-greeting service for high-tier candidates on Liepin."""

import logging
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, List, Optional

from .candidate_excel_service import CandidateExcelService
from .liepin_browser import LiepinBrowserManager

logger = logging.getLogger(__name__)


class GreetingStatus(Enum):
    """Status of a single greeting attempt."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ALREADY_GREETED = "already_greeted"


@dataclass
class GreetingResult:
    """Result of greeting one candidate."""
    row_index: int
    candidate_name: str
    profile_url: str
    status: GreetingStatus
    message: str = ""
    timestamp: str = ""
    error_detail: str = ""


class AutoGreetingService:
    """Automate the greeting workflow for high-tier candidates."""

    GREETING_BUTTON_SELECTORS = [
        'button:has-text("立即沟通")',
        'button:has-text("打招呼")',
        'button:has-text("在线沟通")',
    ]

    ALREADY_GREETED_MARKERS = ["已沟通", "已打招呼", "继续沟通", "继续聊聊"]

    def __init__(
        self,
        browser_manager: LiepinBrowserManager,
        excel_service: Optional[CandidateExcelService] = None,
    ):
        self.browser_manager = browser_manager
        self.excel_service = excel_service or CandidateExcelService()
        self._greeting_count_today = 0
        self._last_greeting_date = ""

    def greet_candidates_from_excel(
        self,
        excel_path: str,
        message_template: str = "",
        tiers: Optional[set] = None,
        require_gold_collar: bool = True,
        require_no_contact: bool = True,
        delay_min: float = 3.0,
        delay_max: float = 8.0,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> List[GreetingResult]:
        """Greet tier-A/B candidates from Excel file."""
        tiers = {str(t).strip().upper() for t in (tiers or {"A", "B"})}
        
        candidates = self.excel_service.load_candidates(excel_path)
        logger.warning("[打招呼] Excel 共加载 %d 位候选人", len(candidates))
        
        # Debug: log each candidate's status
        for c in candidates:
            tier = self._get_tier(c)
            logger.warning(
                "[打招呼] 候选人 %s | 抓取状态=%s | 档位=%s | 有链接=%s",
                c.name, c.capture_status, tier, bool(c.profile_url)
            )
        
        target_candidates = self.excel_service.load_greetable_candidates(
            excel_path,
            tiers=tiers,
            require_gold_collar=require_gold_collar,
            require_no_contact=require_no_contact,
        )
        
        logger.warning(
            "[打招呼] 筛选条件: 抓取状态∈{抓取成功,部分成功} AND 档位∈%s AND 有简历链接 AND 金领=%s AND 无联系方式=%s",
            tiers,
            require_gold_collar,
            require_no_contact,
        )
        logger.warning("[打招呼] 筛选后剩余 %d 位候选人", len(target_candidates))
        
        if not target_candidates:
            logger.warning("No tier-%s candidates found", tiers)
            return []

        # Note: Login check should be done by the caller (main_window) before calling this method
        # This avoids duplicate checks and allows for user interaction (login prompts)
        
        results = []
        total = len(target_candidates)
        
        logger.warning("[打招呼] 开始批量打招呼，共 %d 位候选人", total)

        def _greet_worker(page):
            for index, candidate in enumerate(target_candidates, start=1):
                logger.warning("[打招呼] ===== 处理第 %d/%d 位候选人: %s =====", index, total, candidate.name)
                
                if progress_callback:
                    progress_callback(index, total, candidate.name or "未命名")

                # Human-like delay
                if index > 1:
                    delay = random.uniform(delay_min, delay_max)
                    logger.warning("[打招呼] 等待 %.1f 秒后继续...", delay)
                    time.sleep(delay)

                try:
                    result = self._greet_single(
                        page, candidate, message_template
                    )
                    results.append(result)
                    self._write_result_to_excel(excel_path, result)
                    logger.warning("[打招呼] 第 %d/%d 位处理完成，状态: %s", index, total, result.status.value)
                except Exception as exc:
                    logger.exception("[打招呼] 处理候选人异常: %s", candidate.name)
                    # Create error result
                    from datetime import datetime
                    error_result = GreetingResult(
                        row_index=candidate.row_index,
                        candidate_name=candidate.name or "未命名",
                        profile_url=candidate.profile_url,
                        status=GreetingStatus.FAILED,
                        message="",
                        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        error_detail=f"处理异常: {str(exc)}",
                    )
                    results.append(error_result)
                    self._write_result_to_excel(excel_path, error_result)
                    # Try to recover by closing any dialogs
                    try:
                        self._close_any_dialog(page)
                    except Exception:
                        pass
                
                logger.warning("[打招呼] ===== 第 %d/%d 位处理结束 =====", index, total)
            
            logger.warning("[打招呼] 所有候选人处理完成，共 %d 人", len(results))

        self.browser_manager.run_with_page(_greet_worker)
        logger.warning("[打招呼] 批量打招呼服务返回，共处理 %d 人", len(results))
        return results

    def _greet_single(self, page, candidate, message_template: str) -> GreetingResult:
        """Greet a single candidate."""
        from datetime import datetime
        
        result = GreetingResult(
            row_index=candidate.row_index,
            candidate_name=candidate.name or "未命名",
            profile_url=candidate.profile_url,
            status=GreetingStatus.PENDING,
        )

        try:
            logger.warning("[打招呼] 开始处理候选人: %s", candidate.name)
            
            # Clean up any leftover dialogs from previous candidate
            self._close_any_dialog(page)
            
            # Navigate to profile with multiple fallbacks
            if not self._navigate_to_profile(page, candidate.profile_url):
                logger.error("[打招呼] %s - 页面导航失败，跳过", candidate.name)
                result.status = GreetingStatus.FAILED
                result.error_detail = "页面导航失败"
                return result
            
            logger.warning("[打招呼] %s - 页面加载完成，URL: %s", candidate.name, page.url)

            # Check if already greeted via body text
            try:
                body_text = page.locator("body").inner_text(timeout=5000) or ""
            except Exception:
                body_text = page.evaluate("() => document.body.innerText") or ""
            
            if any(m in body_text for m in self.ALREADY_GREETED_MARKERS):
                logger.warning("[打招呼] %s - 检测到已打招呼标记，跳过", candidate.name)
                result.status = GreetingStatus.ALREADY_GREETED
                result.message = "已打过招呼"
                return result

            # Click greeting button
            if not self._click_greeting_button(page):
                # Fallback: check if button shows "继续沟通" (already greeted)
                if self._has_continue_chat_button(page):
                    logger.warning("[打招呼] %s - 检测到继续沟通按钮，已打招呼", candidate.name)
                    result.status = GreetingStatus.ALREADY_GREETED
                    result.message = "已打过招呼"
                    return result
                logger.warning("[打招呼] %s - 未找到沟通按钮", candidate.name)
                result.status = GreetingStatus.FAILED
                result.error_detail = "未找到沟通按钮"
                return result

            # Handle dialog
            logger.warning("[打招呼] %s - 点击沟通按钮成功，处理弹窗...", candidate.name)
            dialog_result = self._handle_dialog(page, message_template)
            
            if dialog_result.get("success"):
                result.status = GreetingStatus.SUCCESS
                result.message = dialog_result.get("message", "")
                self._greeting_count_today += 1
                logger.warning("[打招呼] %s - 发送成功", candidate.name)
            else:
                result.status = GreetingStatus.FAILED
                result.error_detail = dialog_result.get("error", "未知错误")
                logger.warning("[打招呼] %s - 发送失败: %s", candidate.name, result.error_detail)

        except Exception as exc:
            logger.exception("[打招呼] %s - 处理异常: %s", candidate.name, exc)
            result.status = GreetingStatus.FAILED
            result.error_detail = str(exc)
        finally:
            # Clean up: close any open dialogs/modals to avoid blocking next candidate
            self._close_any_dialog(page)
            result.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.warning("[打招呼] %s - 处理结束，状态: %s", candidate.name, result.status.value)
            
        return result

    def _click_greeting_button(self, page) -> bool:
        """Find and click greeting button."""
        for selector in self.GREETING_BUTTON_SELECTORS:
            try:
                locator = page.locator(selector)
                if locator.count() > 0 and locator.first.is_visible(timeout=2000):
                    locator.first.click()
                    return True
            except Exception:
                continue
        return False

    def _write_result_to_excel(self, excel_path: str, result: GreetingResult) -> None:
        """Best-effort persistence of one greeting attempt."""
        status_labels = {
            GreetingStatus.SUCCESS: "发送成功",
            GreetingStatus.FAILED: "发送失败",
            GreetingStatus.SKIPPED: "已跳过",
            GreetingStatus.ALREADY_GREETED: "已打过招呼",
            GreetingStatus.PENDING: "待处理",
        }
        message = result.message or result.error_detail or ""
        try:
            self.excel_service.write_greeting_result(
                excel_path,
                result.row_index,
                status_labels.get(result.status, result.status.value),
                message,
                result.timestamp,
            )
        except Exception as exc:
            logger.warning("[打招呼] 回写 Excel 失败: %s", exc)

    def _close_any_dialog(self, page) -> None:
        """Close any open dialogs, modals, or chat windows to avoid blocking next candidate."""
        try:
            # Method 1: Use JavaScript to forcibly remove all dialog/modal elements from DOM
            page.evaluate(
                """
                () => {
                    // Remove all dialog elements
                    const selectors = [
                        'dialog', '[role="dialog"]', '.ant-modal', '.modal', 
                        '[class*="modal"]', '[class*="dialog"]', '.chat-dialog',
                        '.im-dialog', '.message-dialog'
                    ];
                    selectors.forEach(sel => {
                        document.querySelectorAll(sel).forEach(el => {
                            el.style.display = 'none';
                            el.remove();
                        });
                    });
                    // Dispatch Escape key
                    document.dispatchEvent(new KeyboardEvent('keydown', {
                        key: 'Escape', keyCode: 27, bubbles: true
                    }));
                }
                """
            )
            time.sleep(0.5)
            
            # Method 2: Press Escape key via Playwright
            for _ in range(2):
                page.keyboard.press("Escape")
                time.sleep(0.2)
            
            # Method 3: Click common close buttons
            close_selectors = [
                'button[class*="close"]',
                'button[aria-label="Close"]',
                '.ant-modal-close',
                '.dialog-close',
                '[class*="close-btn"]',
                '[class*="close-button"]',
                'button:has-text("关闭")',
                'button:has-text("取消")',
            ]
            for selector in close_selectors:
                try:
                    locator = page.locator(selector)
                    if locator.count() > 0:
                        for i in range(min(locator.count(), 2)):
                            elem = locator.nth(i)
                            if elem.is_visible(timeout=200):
                                elem.click()
                                time.sleep(0.2)
                                break
                except Exception:
                    continue
                    
        except Exception:
            pass

    def _navigate_to_profile(self, page, url: str) -> bool:
        """Navigate to candidate profile with multiple fallbacks to avoid hanging."""
        # Method 1: Standard goto with short timeout
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=8000)
            time.sleep(2)
            if url in page.url or "showresumedetail" in page.url:
                return True
        except Exception:
            pass
        
        # Method 2: JavaScript navigation
        try:
            logger.warning("[打招呼] 尝试JS导航到: %s", url)
            page.evaluate(f"window.location.href = '{url}'")
            time.sleep(3)
            if url in page.url or "showresumedetail" in page.url:
                return True
        except Exception:
            pass
        
        # Method 3: Reload then navigate
        try:
            logger.warning("[打招呼] 尝试刷新后导航到: %s", url)
            page.reload(wait_until="domcontentloaded", timeout=5000)
            time.sleep(1)
            page.goto(url, wait_until="commit", timeout=5000)
            time.sleep(2)
            if url in page.url or "showresumedetail" in page.url:
                return True
        except Exception:
            pass
            
        return False

    def _has_continue_chat_button(self, page) -> bool:
        """Check if page shows '继续沟通' button (already greeted)."""
        continue_selectors = [
            'button:has-text("继续沟通")',
            'button:has-text("继续聊聊")',
            'a:has-text("继续沟通")',
            '[role="button"]:has-text("继续沟通")',
        ]
        for selector in continue_selectors:
            try:
                locator = page.locator(selector)
                if locator.count() > 0 and locator.first.is_visible(timeout=2000):
                    return True
            except Exception:
                continue
        return False

    def _handle_dialog(self, page, message_template: str) -> dict:
        """Handle greeting dialog and send custom message in chat window."""
        result = {"success": False, "message": "", "error": ""}
        time.sleep(2)

        # Step 1: Click "不选择职位开聊" if available
        try:
            no_job_btn = page.locator('button:has-text("不选择职位开聊")')
            if no_job_btn.count() > 0 and no_job_btn.first.is_visible(timeout=2000):
                no_job_btn.first.click()
                time.sleep(2)  # Wait for chat window to open
        except Exception:
            pass

        # Step 2: If no "不选择职位开聊", try to select a job
        if not result["success"]:
            self._select_job_if_needed(page)

        # Step 3: Enter custom message in chat input and send
        if message_template:
            if self._send_chat_message(page, message_template):
                result["success"] = True
                result["message"] = message_template
            else:
                result["error"] = "聊天消息发送失败"
        else:
            # No custom message, just confirm the greeting was sent
            result["success"] = True
            result["message"] = "已发送打招呼"

        return result

    def _send_chat_message(self, page, message: str) -> bool:
        """Send a message in the chat window.
        
        Finds the chat input box, enters the message, and clicks send.
        """
        try:
            # Wait for chat dialog to appear
            time.sleep(1.5)
            
            # Find the text input - try multiple selectors based on observed structure
            input_selectors = [
                # By placeholder text
                'textarea[placeholder*="请输入文字"]',
                'input[placeholder*="请输入文字"]',
                '[contenteditable="true"]',
                # By role
                '[role="textbox"]',
                # Generic inputs in chat area
                'dialog textarea',
                'dialog input[type="text"]',
            ]
            
            chat_input = None
            for selector in input_selectors:
                try:
                    locator = page.locator(selector)
                    if locator.count() > 0:
                        # Check if it's visible and in the chat dialog
                        for i in range(min(locator.count(), 3)):
                            elem = locator.nth(i)
                            if elem.is_visible(timeout=1000):
                                chat_input = elem
                                break
                    if chat_input:
                        break
                except Exception:
                    continue
            
            if not chat_input:
                logger.warning("Chat input not found")
                return False
            
            # Clear any existing text and enter new message
            chat_input.fill(message)
            time.sleep(0.5)
            
            # Find and click send button
            send_selectors = [
                'button:has-text("发送")',
                'button[type="submit"]',
                '[role="button"]:has-text("发送")',
            ]
            
            for selector in send_selectors:
                try:
                    send_btn = page.locator(selector)
                    if send_btn.count() > 0:
                        # Check if button is enabled
                        btn = send_btn.first
                        if btn.is_visible(timeout=1000) and btn.is_enabled():
                            btn.click()
                            time.sleep(1)
                            return True
                except Exception:
                    continue
            
            # Fallback: try pressing Enter
            try:
                chat_input.press("Enter")
                time.sleep(1)
                return True
            except Exception:
                pass
                
        except Exception as exc:
            logger.warning("Failed to send chat message: %s", exc)
        
        return False

    def _select_job_if_needed(self, page) -> bool:
        """Select first job if dialog requires it."""
        try:
            dropdown = page.locator('.ant-select:has-text("选择职位")')
            if dropdown.count() > 0:
                dropdown.first.click()
                time.sleep(1)
                options = page.locator('.ant-select-item')
                if options.count() > 0:
                    options.first.click()
                    return True
        except Exception:
            pass
        return False

    @staticmethod
    def _get_tier(record) -> Optional[str]:
        """Extract tier from record with multiple fallback strategies."""
        # 1. Check explicit tier field
        if hasattr(record, "tier") and record.tier:
            tier = str(record.tier).strip().upper()
            if tier in ["A", "B", "C", "D"]:
                return tier
        if hasattr(record, "match_tier") and record.match_tier:
            tier = str(record.match_tier).strip().upper()
            if tier in ["A", "B", "C", "D"]:
                return tier
        
        # 2. Try match_score as letter
        if hasattr(record, "match_score") and record.match_score is not None:
            score_str = str(record.match_score).strip().upper()
            if score_str in ["A", "B", "C", "D"]:
                return score_str
            # If match_score is a number, infer tier from score ranges
            try:
                score_num = float(record.match_score)
                if score_num >= 80:
                    return "A"
                elif score_num >= 60:
                    return "B"
                elif score_num >= 40:
                    return "C"
                else:
                    return "D"
            except (TypeError, ValueError):
                pass
        
        # 3. Try match_detail text patterns
        detail = getattr(record, "match_detail", "") or ""
        import re
        
        # Pattern: "档位判定: A", "档位: A" or "档位：A"
        match = re.search(r"(?:档位判定|档位)\s*[:：]\s*([ABCD])", detail, re.I)
        if match:
            return match.group(1).upper()
        
        # Pattern: "匹配档位 A" or "档位A"
        match = re.search(r"(?:匹配)?\s*档\s*位\s*([ABCD])", detail, re.I)
        if match:
            return match.group(1).upper()
            
        # Pattern: "Tier A" or "等级 A"
        match = re.search(r"(?:Tier|等级|级别)\s*[:：]?\s*([ABCD])", detail, re.I)
        if match:
            return match.group(1).upper()
        
        return None

    @classmethod
    def _is_greetable_candidate(
        cls,
        record,
        tiers: set,
        require_gold_collar: bool = True,
        require_no_contact: bool = True,
    ) -> bool:
        """Only explicit A/B-style tiers are allowed into auto greeting."""
        tier = cls._get_tier(record)
        if not tier or tier not in tiers:
            return False
        if getattr(record, "capture_status", "") not in ("抓取成功", "部分成功"):
            return False
        if not getattr(record, "profile_url", ""):
            return False
        if getattr(record, "greeting_status", "") in ("发送成功", "已打过招呼"):
            return False
        if require_gold_collar and not CandidateExcelService.is_gold_collar_candidate(record):
            return False
        if require_no_contact and CandidateExcelService.has_contact_info(record):
            return False
        return True

    @staticmethod
    def generate_summary(results: List[GreetingResult]) -> str:
        """Generate summary text."""
        if not results:
            return "没有需要打招呼的候选人"
        
        total = len(results)
        success = sum(1 for r in results if r.status == GreetingStatus.SUCCESS)
        already = sum(1 for r in results if r.status == GreetingStatus.ALREADY_GREETED)
        failed = sum(1 for r in results if r.status == GreetingStatus.FAILED)
        
        lines = [
            f"自动打招呼完成：共处理 {total} 位候选人",
            f"  - 成功：{success} 人",
            f"  - 已打过：{already} 人",
            f"  - 失败：{failed} 人",
        ]
        
        if failed > 0:
            lines.append("\n失败详情：")
            for r in results:
                if r.status == GreetingStatus.FAILED:
                    lines.append(f"  - {r.candidate_name}: {r.error_detail}")
        
        return "\n".join(lines)
