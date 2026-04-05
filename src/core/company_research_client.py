"""公司深度调研客户端模块"""

import sys
import logging
import os
from typing import Generator, List, Dict
from .prompt import COMPANY_RESEARCH_PROMPT
from .llm_client import LLMClient

if getattr(sys, "frozen", False):
    try:
        import certifi

        os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
        os.environ["CURL_CA_BUNDLE"] = certifi.where()
    except ImportError:
        pass

logger = logging.getLogger(__name__)


class CompanyResearchError(Exception):
    """公司调研异常基类"""

    pass


class CompanyResearchClient:
    """公司深度调研客户端"""

    def __init__(self, tavily_api_key: str, llm_client: LLMClient):
        """初始化调研客户端"""
        try:
            from tavily import TavilyClient
        except ImportError:
            raise CompanyResearchError(
                "缺少 tavily-python 包，请运行 pip install tavily-python"
            )
        self.tavily = TavilyClient(api_key=tavily_api_key)
        self.llm = llm_client

    def research(self, company_name: str) -> str:
        """深度调研公司信息（非流式，返回完整结果）"""
        search_results = self._search_company(company_name)

        if not search_results:
            return "未找到相关搜索结果，请检查公司名称是否正确"

        detailed_contents = self._extract_contents(search_results)

        report = self._generate_report(company_name, search_results, detailed_contents)

        return report

    def _search_company(self, company_name: str) -> List[Dict]:
        """搜索公司信息"""
        try:
            queries = [
                "{} 公司简介 主营业务".format(company_name),
                "{} 最新动态 新闻".format(company_name),
            ]

            all_results = []
            for query in queries:
                response = self.tavily.search(
                    query=query,
                    search_depth="advanced",
                    max_results=5,
                    topic="general",
                    include_answer=True,
                )
                results = response.get("results", [])
                all_results.extend(results)

            # 去重（基于URL）
            seen_urls = set()
            unique_results = []
            for result in all_results:
                url = result.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(result)

            # 按评分排序，取前10个
            unique_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            return unique_results[:10]

        except Exception as e:
            raise CompanyResearchError("搜索失败: {}".format(str(e)))

    def _extract_single_url(self, url: str) -> dict:
        """提取单个URL的内容"""
        try:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                logger.warning("下载失败: {}".format(url))
                return None

            content = trafilatura.extract(
                downloaded,
                output_format="txt",
                include_tables=True,
                include_comments=False,
                favor_recall=True,
            )

            if content and len(content) > 50:
                logger.info("成功提取URL内容: {}".format(url))
                return {"url": url, "content": content[:4000]}
            else:
                logger.warning("内容为空或太短，跳过: {}".format(url))
                return None

        except Exception as e:
            logger.error("提取URL失败 {}: {}".format(url, str(e)))
            return None

    def _extract_contents(self, search_results: List[Dict]) -> List[Dict]:
        """并行提取网页详细内容"""
        try:
            import trafilatura
        except ImportError:
            logger.warning("缺少 trafilatura 包，跳过网页内容提取")
            return []

        urls_to_extract = [r["url"] for r in search_results[:5] if r.get("url")]
        logger.info("准备并行提取 {} 个URL的内容".format(len(urls_to_extract)))

        from concurrent.futures import ThreadPoolExecutor, as_completed

        contents = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self._extract_single_url, url): url
                for url in urls_to_extract
            }
            for future in as_completed(futures):
                result = future.result()
                if result:
                    contents.append(result)

        logger.info("最终成功提取 {} 个网页内容".format(len(contents)))
        return contents

    def _generate_report(
        self,
        company_name: str,
        search_results: List[Dict],
        detailed_contents: List[Dict],
    ) -> str:
        """生成调研报告"""
        sources_text = "\n".join(
            [
                "- [{}]({}): {}".format(
                    r.get("title", "无标题"),
                    r.get("url", ""),
                    r.get("content", "")[:200],
                )
                for r in search_results[:5]
            ]
        )

        detailed_text = "\n\n".join(
            [
                "### 来源: {}\n{}".format(c["url"], c["content"])
                for c in detailed_contents
            ]
        )

        if not detailed_text:
            detailed_text = "未获取到详细网页内容"

        prompt = COMPANY_RESEARCH_PROMPT.format(
            company_name=company_name,
            sources=sources_text,
            detailed_content=detailed_text,
        )

        return self.llm.chat(prompt)
