"""分析结果解析模块"""

import re
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class ParsedResult:
    """解析后的分析结果"""
    module1: str = ""  # 岗位定性与大白话翻译
    module2: str = ""  # 核心门槛提取
    module3: str = ""  # 搜索关键词扩展
    module4: str = ""  # 布尔搜索公式
    raw_text: str = ""  # 原始文本


class ResultParser:
    """分析结果解析器"""

    # 模块标题的匹配模式
    MODULE_PATTERNS = [
        (1, [r"模块一", r"岗位定性", r"大白话翻译", r"模块1"]),
        (2, [r"模块二", r"核心门槛", r"剥离水分", r"模块2"]),
        (3, [r"模块三", r"搜索关键词", r"黑话与变体", r"模块3"]),
        (4, [r"模块四", r"布尔搜索", r"Boolean", r"模块4"]),
    ]

    @classmethod
    def parse(cls, text: str) -> ParsedResult:
        """
        解析 AI 返回的文本，拆分成四个模块

        Args:
            text: AI 返回的原始文本

        Returns:
            ParsedResult 对象
        """
        result = ParsedResult(raw_text=text)

        if not text.strip():
            return result

        # 找到每个模块的起始位置
        module_positions = cls._find_module_positions(text)

        # 按位置排序
        sorted_modules = sorted(module_positions.items(), key=lambda x: x[1])

        # 提取每个模块的内容
        for i, (module_num, start_pos) in enumerate(sorted_modules):
            # 确定结束位置
            if i + 1 < len(sorted_modules):
                end_pos = sorted_modules[i + 1][1]
            else:
                end_pos = len(text)

            # 提取内容
            content = text[start_pos:end_pos].strip()

            # 移除模块标题行
            content = cls._remove_title_line(content)

            # 设置到结果对象
            if module_num == 1:
                result.module1 = content
            elif module_num == 2:
                result.module2 = content
            elif module_num == 3:
                result.module3 = content
            elif module_num == 4:
                result.module4 = content

        return result

    @classmethod
    def _find_module_positions(cls, text: str) -> Dict[int, int]:
        """找到每个模块在文本中的起始位置"""
        positions = {}

        for module_num, patterns in cls.MODULE_PATTERNS:
            min_pos = len(text)
            found = False

            for pattern in patterns:
                matches = list(re.finditer(pattern, text, re.IGNORECASE))
                for match in matches:
                    if match.start() < min_pos:
                        min_pos = match.start()
                        found = True

            if found:
                # 找到这一行的开头
                line_start = text.rfind("\n", 0, min_pos) + 1
                positions[module_num] = line_start

        return positions

    @classmethod
    def _remove_title_line(cls, content: str) -> str:
        """移除模块标题行"""
        lines = content.split("\n")
        if not lines:
            return content

        # 检查第一行是否是标题
        first_line = lines[0].strip()
        if any(re.search(pattern, first_line, re.IGNORECASE)
               for _, patterns in cls.MODULE_PATTERNS
               for pattern in patterns):
            lines = lines[1:]

        return "\n".join(lines).strip()

    @classmethod
    def extract_boolean_formulas(cls, module4_content: str) -> Dict[str, str]:
        """
        从模块四内容中提取布尔搜索公式

        Returns:
            {"precise": 精准版公式, "broad": 泛化版公式}
        """
        result = {"precise": "", "broad": ""}

        if not module4_content:
            return result

        lines = module4_content.split("\n")
        current_type = None
        current_formula = []

        for line in lines:
            line_lower = line.lower()

            # 检测公式类型
            if "精准" in line:
                if current_formula and current_type:
                    result[current_type] = " ".join(current_formula).strip()
                current_type = "precise"
                current_formula = []
            elif "泛化" in line or "扩大" in line:
                if current_formula and current_type:
                    result[current_type] = " ".join(current_formula).strip()
                current_type = "broad"
                current_formula = []
            elif current_type and ("AND" in line.upper() or "OR" in line.upper() or "(" in line):
                # 这是公式内容
                current_formula.append(line.strip())

        # 处理最后一个公式
        if current_formula and current_type:
            result[current_type] = " ".join(current_formula).strip()

        return result

    @classmethod
    def extract_keywords_from_formula(cls, formula: str) -> List[str]:
        """
        从布尔公式中提取所有关键词

        Args:
            formula: 布尔搜索公式

        Returns:
            关键词列表
        """
        if not formula:
            return []

        # 匹配引号内的内容或独立单词（排除操作符和括号）
        tokens = re.findall(r'"([^"]+)"|([^\s()]+)', formula)

        keywords = []
        for quoted, unquoted in tokens:
            word = quoted or unquoted
            if word and word.upper() not in ("AND", "OR", "NOT", "(", ")"):
                keywords.append(word)

        return keywords


class StreamingParser:
    """流式解析器 - 边接收边解析"""

    def __init__(self):
        self.buffer = ""
        self.current_module = 0
        self.module_contents = {1: "", 2: "", 3: "", 4: ""}

    def feed(self, chunk: str) -> Optional[Tuple[int, str]]:
        """
        接收新的文本片段

        Args:
            chunk: 新接收的文本片段

        Returns:
            (module_num, new_content) 如果检测到模块内容更新
            None 如果没有更新
        """
        self.buffer += chunk

        # 检测是否进入了新模块
        new_module = self._detect_current_module()

        if new_module > 0:
            if new_module != self.current_module:
                self.current_module = new_module

            # 返回当前模块的完整内容
            content = self._extract_current_module_content()
            if content:
                self.module_contents[self.current_module] = content
                return (self.current_module, content)

        return None

    def _detect_current_module(self) -> int:
        """检测当前正在输出哪个模块"""
        # 从后往前查找最近的模块标记
        for module_num, patterns in reversed(ResultParser.MODULE_PATTERNS):
            for pattern in patterns:
                if re.search(pattern, self.buffer, re.IGNORECASE):
                    # 确认这是最后出现的模块
                    matches = list(re.finditer(pattern, self.buffer, re.IGNORECASE))
                    if matches:
                        return module_num
        return self.current_module

    def _extract_current_module_content(self) -> str:
        """提取当前模块的内容"""
        if self.current_module == 0:
            return ""

        # 找到当前模块的起始位置
        start_pos = 0
        for pattern in ResultParser.MODULE_PATTERNS[self.current_module - 1][1]:
            matches = list(re.finditer(pattern, self.buffer, re.IGNORECASE))
            if matches:
                # 使用最后一个匹配
                match = matches[-1]
                line_start = self.buffer.rfind("\n", 0, match.start()) + 1
                start_pos = max(start_pos, line_start)
                break

        # 找到下一个模块的起始位置（如果有）
        end_pos = len(self.buffer)
        for next_module in range(self.current_module + 1, 5):
            for pattern in ResultParser.MODULE_PATTERNS[next_module - 1][1]:
                match = re.search(pattern, self.buffer[start_pos:], re.IGNORECASE)
                if match:
                    end_pos = min(end_pos, start_pos + match.start())
                    break

        content = self.buffer[start_pos:end_pos].strip()

        # 移除标题行
        return ResultParser._remove_title_line(content)

    def get_result(self) -> ParsedResult:
        """获取最终解析结果"""
        return ParsedResult(
            module1=self.module_contents.get(1, ""),
            module2=self.module_contents.get(2, ""),
            module3=self.module_contents.get(3, ""),
            module4=self.module_contents.get(4, ""),
            raw_text=self.buffer
        )

    def reset(self):
        """重置解析器状态"""
        self.buffer = ""
        self.current_module = 0
        self.module_contents = {1: "", 2: "", 3: "", 4: ""}
