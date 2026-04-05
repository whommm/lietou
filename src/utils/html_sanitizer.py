"""HTML清洗器 - 自动补全未闭合标签，防止DOM解析错误"""

import re


class HtmlSanitizer:
    """HTML清洗器：使用标签栈补全未闭合的HTML标签"""

    VOID_ELEMENTS = frozenset({
        'br', 'hr', 'img', 'input', 'meta', 'link', 'area', 'base',
        'col', 'embed', 'source', 'track', 'wbr', 'param',
    })

    SAFE_TAGS = frozenset({
        'div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'thead', 'tbody', 'tfoot',
        'strong', 'em', 'b', 'i', 'u', 's', 'span', 'a',
        'code', 'pre', 'blockquote', 'cite',
        'section', 'article', 'header', 'footer', 'nav', 'main',
        'dl', 'dt', 'dd',
    })

    TAG_PATTERN = re.compile(r'<(/?)(\w+)(?:\s+[^>]*)?\s*/?>')

    def sanitize(self, html: str) -> str:
        """补全未闭合的HTML标签

        Args:
            html: 可能包含未闭合标签的HTML片段

        Returns:
            补全后的HTML字符串
        """
        if not html:
            return html

        stack = []
        result_parts = []
        last_end = 0

        for match in self.TAG_PATTERN.finditer(html):
            is_closing = match.group(1) == '/'
            tag_name = match.group(2).lower()
            is_self_closing = match.group(0).endswith('/>')

            result_parts.append(html[last_end:match.end()])
            last_end = match.end()

            if tag_name in self.VOID_ELEMENTS or is_self_closing:
                continue

            if tag_name not in self.SAFE_TAGS:
                continue

            if is_closing:
                # 弹出栈直到找到匹配的标签
                while stack and stack[-1] != tag_name:
                    unclosed = stack.pop()
                    result_parts.insert(-1 if result_parts else len(result_parts), f'</{unclosed}>')
                if stack:
                    stack.pop()
            else:
                stack.append(tag_name)

        result_parts.append(html[last_end:])

        # 补全剩余未闭合的标签
        closing_tags = ''.join(f'</{tag}>' for tag in reversed(stack))
        return ''.join(result_parts) + closing_tags
