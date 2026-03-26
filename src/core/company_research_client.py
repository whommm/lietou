"""公司深度调研客户端模块"""

import sys
if sys.version_info < (3, 9):
    from typing import Dict as dict

from tavily import TavilyClient
import trafilatura
from typing import Generator, List, Dict
from .prompt import COMPANY_RESEARCH_PROMPT
from .llm_client import LLMClient
import logging
import os

# 配置日志
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'company_research.log')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CompanyResearchError(Exception):
    """公司调研异常基类"""
    pass


class CompanyResearchClient:
    """公司深度调研客户端"""

    def __init__(self, tavily_api_key: str, llm_client: LLMClient):
        """初始化调研客户端"""
        self.tavily = TavilyClient(api_key=tavily_api_key)
        self.llm = llm_client

    def research(self, company_name: str) -> Generator[str, None, None]:
        """深度调研公司信息（流式输出）"""
        # 步骤1: 搜索公司信息
        yield "🔍 正在搜索公司相关信息...\n"
        search_results = self._search_company(company_name)

        if not search_results:
            yield "⚠️ 未找到相关搜索结果，请检查公司名称是否正确\n"
            return

        yield "✅ 已找到 {} 条相关信息\n\n".format(len(search_results))

        # 步骤2: 提取网页详细内容
        yield "📄 正在提取网页详细内容...\n"
        detailed_contents = self._extract_contents(search_results)

        yield "✅ 已成功提取 {} 个网页内容\n\n".format(len(detailed_contents))

        # 步骤3: LLM整合分析
        yield "🤖 正在生成调研报告...\n\n"
        yield "---\n\n"

        report_generator = self._generate_report(
            company_name,
            search_results,
            detailed_contents
        )

        for chunk in report_generator:
            yield chunk

    def _search_company(self, company_name: str) -> List[Dict]:
        """搜索公司信息"""
        try:
            queries = [
                "{} 公司简介 主营业务".format(company_name),
                "{} 最新动态 新闻".format(company_name)
            ]

            all_results = []
            for query in queries:
                response = self.tavily.search(
                    query=query,
                    search_depth="advanced",
                    max_results=5,
                    topic="general",
                    include_answer=True
                )
                results = response.get('results', [])
                all_results.extend(results)

            # 去重（基于URL）
            seen_urls = set()
            unique_results = []
            for result in all_results:
                url = result.get('url', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(result)

            # 按评分排序，取前10个
            unique_results.sort(key=lambda x: x.get('score', 0), reverse=True)
            return unique_results[:10]

        except Exception as e:
            raise CompanyResearchError("搜索失败: {}".format(str(e)))

    def _extract_contents(self, search_results: List[Dict]) -> List[Dict]:
        """提取网页详细内容"""
        contents = []
        urls_to_extract = [r['url'] for r in search_results[:5] if r.get('url')]
        logger.info("准备提取 {} 个URL的内容".format(len(urls_to_extract)))

        for idx, url in enumerate(urls_to_extract):
            logger.info("正在提取第 {}/{} 个URL: {}".format(idx+1, len(urls_to_extract), url))
            try:
                downloaded = trafilatura.fetch_url(url)
                if not downloaded:
                    logger.warning("下载失败: {}".format(url))
                    continue

                logger.debug("下载成功，内容长度: {} 字节".format(len(downloaded)))

                content = trafilatura.extract(
                    downloaded,
                    output_format="txt",
                    include_tables=True,
                    include_comments=False,
                    favor_recall=True
                )

                if content:
                    logger.info("提取到内容长度: {} 字符".format(len(content)))
                    if len(content) > 50:
                        contents.append({
                            'url': url,
                            'content': content[:4000]
                        })
                        logger.info("成功添加URL内容: {}".format(url))
                    else:
                        logger.warning("内容太短，跳过: {}".format(url))
                else:
                    logger.warning("提取内容为空: {}".format(url))

            except Exception as e:
                logger.error("提取URL失败 {}: {}".format(url, str(e)))
                continue

        logger.info("最终成功提取 {} 个网页内容".format(len(contents)))
        return contents

    def _generate_report(self, company_name: str, search_results: List[Dict],
                        detailed_contents: List[Dict]) -> Generator[str, None, None]:
        """生成调研报告"""
        # 构建搜索摘要
        sources_text = "\n".join([
            "- [{}]({}): {}".format(
                r.get('title', '无标题'),
                r.get('url', ''),
                r.get('content', '')[:200]
            )
            for r in search_results[:5]
        ])

        # 构建详细内容
        detailed_text = "\n\n".join([
            "### 来源: {}\n{}".format(c['url'], c['content'])
            for c in detailed_contents
        ])

        if not detailed_text:
            detailed_text = "未获取到详细网页内容"

        # 构建提示词
        prompt = COMPANY_RESEARCH_PROMPT.format(
            company_name=company_name,
            sources=sources_text,
            detailed_content=detailed_text
        )

        # 调用LLM生成报告（流式）
        return self.llm.chat_stream(prompt)

