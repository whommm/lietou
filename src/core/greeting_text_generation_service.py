"""Greeting text generation service using LLM."""

import logging
import re
from typing import List, Optional

from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class GreetingTextGenerationError(Exception):
    """Raised when greeting text generation fails."""


class GreetingTextGenerationService:
    """Generate professional greeting messages for猎头 to candidates."""

    DEFAULT_TEMPLATE = (
        "您好，我是猎头顾问，目前有个base{city}的{job_title}机会，"
        "{job_summary}，"
        "薪资可谈，"
        "方便的话能发一份您的简历看看吗？"
    )

    SYSTEM_PROMPT = """你是一个资深猎头顾问，擅长撰写简洁专业的候选人打招呼消息。

要求：
1. 开头固定格式："您好，我是猎头顾问，目前有个base{city}的{job_title}机会，"
2. 中间用1-2句话简洁介绍岗位核心亮点（不要罗列职责，要突出吸引力）
3. 薪资统一写"薪资可谈"，绝对不要出现具体数字或范围
4. 结尾固定："方便的话能发一份您的简历看看吗？"
5. 总字数控制在60-100字（不含标点）
6. 语气专业、友好、有吸引力，像真人猎头写的
7. 不要出现公司名称（除非特别说明）
8. 不要出现"根据您的简历"等个性化表述（因为是首次联系）

只输出打招呼文本，不要解释，不要加引号。"""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def generate(
        self,
        job_title: str,
        city: str,
        job_description: str,
        salary_range: str = "",
        style: str = "general",
    ) -> str:
        """Generate a greeting message.

        Args:
            job_title: Job title (e.g., "高级产品经理")
            city: City name, should be at prefecture-level (e.g., "深圳")
            job_description: Full job description/JD text
            salary_range: Original salary range (will be replaced with "薪资可谈")
            style: Style variant - "general", "highlight", "career", "company", "balance"

        Returns:
            Formatted greeting text
        """
        # Clean city name to prefecture-level
        city = self._extract_prefecture_city(city)

        # Build user prompt
        user_prompt = self._build_prompt(
            job_title=job_title,
            city=city,
            job_description=job_description,
            salary_range=salary_range,
            style=style,
        )

        try:
            # Call LLM API
            raw_text = self.llm_client.chat(
                user_message=user_prompt,
                system_message=self.SYSTEM_PROMPT,
            )

            # Post-process to ensure format compliance
            return self._post_process(raw_text, job_title, city)

        except Exception as exc:
            logger.error("Failed to generate greeting text: %s", exc)
            # Fallback to template-based generation
            return self._fallback_generate(job_title, city, job_description)

    def generate_batch(
        self,
        job_title: str,
        city: str,
        job_description: str,
        salary_range: str = "",
        count: int = 5,
    ) -> List[str]:
        """Generate multiple greeting variants.

        Args:
            job_title: Job title
            city: City name
            job_description: Job description
            salary_range: Salary range
            count: Number of variants to generate (default 5)

        Returns:
            List of greeting texts
        """
        styles = ["general", "highlight", "career", "company", "balance"]
        results = []

        for i in range(min(count, len(styles))):
            try:
                text = self.generate(
                    job_title=job_title,
                    city=city,
                    job_description=job_description,
                    salary_range=salary_range,
                    style=styles[i],
                )
                if text and text not in results:
                    results.append(text)
            except Exception as exc:
                logger.warning("Failed to generate variant %d: %s", i, exc)
                continue

        # If we got fewer results than requested, fill with fallback
        while len(results) < count:
            fallback = self._fallback_generate(job_title, city, job_description)
            if fallback not in results:
                results.append(fallback)
            else:
                break

        return results[:count]

    def _build_prompt(
        self,
        job_title: str,
        city: str,
        job_description: str,
        salary_range: str,
        style: str,
    ) -> str:
        """Build the prompt for LLM."""
        style_hints = {
            "general": "写一个通用版本，平衡各方面信息",
            "highlight": "重点突出岗位的核心亮点和吸引力",
            "career": "强调职业发展空间和成长机会",
            "company": "突出公司优势和团队氛围",
            "balance": "强调工作生活平衡和福利待遇",
        }

        style_hint = style_hints.get(style, style_hints["general"])

        prompt = f"""请根据以下岗位信息，生成一段猎头打招呼文本：

岗位名称：{job_title}
工作城市：{city}
岗位描述：{job_description[:500]}
"""
        if salary_range:
            prompt += f'薪资范围：{salary_range}（注意：输出时请替换为"薪资可谈"）\n'

        prompt += f"\n生成要求：{style_hint}\n\n请生成："

        return prompt

    def _post_process(self, text: str, job_title: str, city: str) -> str:
        """Post-process LLM output to ensure format compliance."""
        if not text:
            return self._fallback_generate(job_title, city, "")

        text = text.strip()

        # Remove quotes if present
        text = text.strip('"\'"')

        # Ensure it starts with correct opening
        if not text.startswith("您好，我是猎头顾问"):
            # Try to fix or regenerate
            logger.warning("Greeting text doesn't start with expected format: %s", text[:50])
            text = f"您好，我是猎头顾问，目前有个base{city}的{job_title}机会，{text}"

        # Ensure salary is masked
        text = self._mask_salary(text)

        # Ensure it ends with resume request
        if "简历" not in text[-20:]:
            text = text.rstrip("，。！？") + "，方便的话能发一份您的简历看看吗？"

        # Limit length
        if len(text) > 200:
            text = text[:197] + "..."

        return text

    def _mask_salary(self, text: str) -> str:
        """Replace salary numbers with '薪资可谈'."""
        # Match patterns like "20-30k", "15k-25k", "年薪30-50万", etc.
        patterns = [
            r"\d+\s*-\s*\d+\s*[kK万wW]",
            r"\d+\s*[kK万wW]\s*-\s*\d+\s*[kK万wW]",
            r"年薪\s*\d+\s*-\s*\d+\s*万",
            r"月薪\s*\d+\s*-\s*\d+\s*[kK]",
            r"\d+\s*-\s*\d+\s*万/年",
            r"\d+\s*-\s*\d+\s*K/月",
        ]

        for pattern in patterns:
            text = re.sub(pattern, "薪资可谈", text)

        # Also replace explicit salary mentions
        text = re.sub(r"薪资[：:]\s*[^，。]+", "薪资可谈", text)
        text = re.sub(r"薪水[：:]\s*[^，。]+", "薪资可谈", text)
        text = re.sub(r"待遇[：:]\s*[^，。]+", "待遇可谈", text)

        return text

    def _fallback_generate(self, job_title: str, city: str, job_description: str) -> str:
        """Fallback greeting generation without LLM."""
        # Extract a brief summary from job description
        summary = self._extract_brief_summary(job_description)

        if summary:
            return self.DEFAULT_TEMPLATE.format(
                city=city,
                job_title=job_title,
                job_summary=summary,
            )
        else:
            return (
                f"您好，我是猎头顾问，目前有个base{city}的{job_title}机会，"
                "团队发展快、项目有挑战性，"
                "薪资可谈，"
                "方便的话能发一份您的简历看看吗？"
            )

    def _extract_brief_summary(self, job_description: str) -> str:
        """Extract a 1-2 sentence summary from job description."""
        if not job_description:
            return ""

        # Split by common delimiters and take first meaningful sentence
        sentences = re.split(r"[。；\n]", job_description)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10 and len(sentence) < 80:
                # Clean up the sentence
                sentence = re.sub(r"负责|工作|职责|要求|任职", "", sentence)
                sentence = sentence.strip("，。 ")
                if sentence:
                    return sentence

        return ""

    @staticmethod
    def _extract_prefecture_city(city_text: str) -> str:
        """Extract prefecture-level city name.

        Examples:
            "深圳市南山区" -> "深圳"
            "北京朝阳区" -> "北京"
            "上海市浦东新区" -> "上海"
            "杭州" -> "杭州"
        """
        if not city_text:
            return "该城市"

        # List of major Chinese cities (prefecture-level and above)
        major_cities = [
            "北京", "上海", "天津", "重庆",
            "深圳", "广州", "杭州", "南京", "苏州", "成都", "武汉",
            "西安", "长沙", "郑州", "青岛", "大连", "厦门", "宁波",
            "无锡", "佛山", "东莞", "福州", "济南", "合肥", "昆明",
            "哈尔滨", "长春", "沈阳", "石家庄", "太原", "呼和浩特",
            "乌鲁木齐", "拉萨", "银川", "西宁", "兰州", "贵阳",
            "海口", "南宁", "南昌", "温州", "常州", "南通", "烟台",
            "泉州", "唐山", "邯郸", "保定", "潍坊", "徐州", "绍兴",
            "嘉兴", "金华", "珠海", "惠州", "中山", "江门", "海口",
            "三亚", "廊坊", "咸阳", "绵阳", "德阳", "宜宾", "南充",
            "乐山", "泸州", "达州", "曲靖", "玉溪", "丽江", "大理",
        ]

        # Direct match for major cities
        for city in major_cities:
            if city in city_text:
                return city

        # Pattern matching for city names
        # Match patterns like "深圳市", "杭州", "XX市", etc.
        patterns = [
            r"(北京|上海|天津|重庆)",  # Municipalities
            r"(.*?)(?:市|区|县|镇|街道)",  # Generic pattern
        ]

        for pattern in patterns:
            match = re.search(pattern, city_text)
            if match:
                result = match.group(1)
                if result and len(result) >= 2:
                    return result

        # If no match found, return original text up to 4 chars
        clean_text = re.sub(r"[市区县镇街道省]", "", city_text)
        return clean_text[:4] or city_text[:4]


# Convenience function for external use
def generate_greeting_text(
    llm_client: LLMClient,
    job_title: str,
    city: str,
    job_description: str,
    salary_range: str = "",
) -> str:
    """Convenience function to generate greeting text."""
    service = GreetingTextGenerationService(llm_client)
    return service.generate(
        job_title=job_title,
        city=city,
        job_description=job_description,
        salary_range=salary_range,
    )
