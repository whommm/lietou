"""卡片组件模块"""

import customtkinter as ctk
from tkinter import messagebox
import re
from typing import Optional, Callable, Dict
from ..utils.helpers import copy_to_clipboard


class ClickableTag(ctk.CTkButton):
    """可点击复制的标签"""

    def __init__(self, master, text: str, **kwargs):
        self.tag_text = text
        super().__init__(
            master,
            text=text,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(size=14),
            fg_color=("gray85", "gray30"),
            hover_color=("gray75", "gray40"),
            text_color=("gray10", "gray90"),
            command=self._on_click,
            **kwargs
        )

    def _on_click(self):
        """点击复制"""
        if copy_to_clipboard(self.tag_text):
            # 临时改变颜色表示已复制
            original_fg = self.cget("fg_color")
            self.configure(fg_color=("green", "darkgreen"))
            self.after(300, lambda: self.configure(fg_color=original_fg))


class KeywordSection(ctk.CTkFrame):
    """关键词分类区域组件"""

    def __init__(self, master, title: str, keywords: list, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.title = title
        self.keywords = keywords
        self._build_ui()

    def _build_ui(self):
        """构建 UI"""
        if not self.keywords:
            # 没有关键词时不占用任何空间
            self.configure(height=0)
            return

        # 小标题
        title_label = ctk.CTkLabel(
            self,
            text=self.title,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        title_label.pack(fill="x", pady=(5, 2), anchor="nw")

        # 关键词标签容器（流式布局）
        tags_frame = ctk.CTkFrame(self, fg_color="transparent")
        tags_frame.pack(fill="x", pady=(0, 2), anchor="nw")

        # 渲染关键词标签
        current_row = ctk.CTkFrame(tags_frame, fg_color="transparent")
        current_row.pack(fill="x", anchor="nw")
        col = 0

        for keyword in self.keywords:
            keyword = keyword.strip()
            if not keyword:
                continue

            tag = ClickableTag(current_row, text=keyword)
            tag.pack(side="left", padx=2, pady=2)

            col += 1
            # 每行最多 6 个标签，换行
            if col >= 6:
                col = 0
                current_row = ctk.CTkFrame(tags_frame, fg_color="transparent")
                current_row.pack(fill="x", anchor="nw")


class ModuleCard(ctk.CTkFrame):
    """模块卡片组件"""

    # 模块配置（改为3个模块）
    MODULE_CONFIG = {
        1: {"icon": "📋", "title": "岗位定性与行业科普", "color": ("#e3f2fd", "#1a237e")},
        2: {"icon": "🎯", "title": "核心门槛提取", "color": ("#fff3e0", "#e65100")},
        3: {"icon": "🏷️", "title": "搜索关键词库", "color": ("#e8f5e9", "#1b5e20")},
    }

    def __init__(self, master, module_num: int, content: str = "", **kwargs):
        # 获取模块配置
        config = self.MODULE_CONFIG.get(module_num, {"icon": "📄", "title": f"模块{module_num}", "color": ("#f5f5f5", "#424242")})

        super().__init__(
            master,
            corner_radius=12,
            border_width=1,
            border_color=("gray70", "gray40"),
            **kwargs
        )

        self.module_num = module_num
        self.content = content
        self.config = config

        self._build_ui()

    def _build_ui(self):
        """构建卡片 UI"""
        # 标题栏
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(12, 5))

        # 图标和标题
        title_label = ctk.CTkLabel(
            header_frame,
            text=f"{self.config['icon']} {self.config['title']}",
            font=ctk.CTkFont(size=17, weight="bold")
        )
        title_label.pack(side="left")

        # 复制按钮
        copy_btn = ctk.CTkButton(
            header_frame,
            text="复制",
            width=50,
            height=26,
            corner_radius=6,
            font=ctk.CTkFont(size=13),
            fg_color=("gray75", "gray35"),
            hover_color=("gray65", "gray45"),
            command=self._on_copy
        )
        copy_btn.pack(side="right")

        # 分隔线
        separator = ctk.CTkFrame(self, height=1, fg_color=("gray80", "gray50"))
        separator.pack(fill="x", padx=15, pady=5)

        # 内容区
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=15, pady=(5, 12))

        # 根据模块类型渲染内容
        if self.module_num == 3 and self.content:
            self._render_keyword_content(content_frame)
        else:
            self._render_text_content(content_frame)

    def _render_text_content(self, parent):
        """渲染普通文本内容"""
        # 解析并格式化内容
        formatted_content = self._format_content(self.content)

        content_label = ctk.CTkLabel(
            parent,
            text=formatted_content,
            font=ctk.CTkFont(size=15),
            justify="left",
            anchor="nw",
            wraplength=500
        )
        content_label.pack(fill="both", expand=True, anchor="nw")

    def _render_keyword_content(self, parent):
        """渲染关键词库内容（模块四）"""
        # 解析关键词分类
        sections = self._parse_keyword_sections(self.content)

        for section_title, keywords in sections.items():
            if keywords:
                section = KeywordSection(parent, title=section_title, keywords=keywords)
                section.pack(fill="x", pady=(0, 4))

    def _parse_keyword_sections(self, content: str) -> Dict[str, list]:
        """解析关键词分类"""
        sections = {
            "🎯 核心岗位词": [],
            "🛠️ 核心技能词": [],
            "🏭 行业/领域词": [],
            "🏢 目标公司": [],
        }

        if not content:
            return sections

        current_section = None
        section_mapping = {
            "核心岗位词": "🎯 核心岗位词",
            "岗位词": "🎯 核心岗位词",
            "核心技能词": "🛠️ 核心技能词",
            "技能词": "🛠️ 核心技能词",
            "行业": "🏭 行业/领域词",
            "领域": "🏭 行业/领域词",
            "目标公司": "🏢 目标公司",
            "公司": "🏢 目标公司",
        }

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue

            # 检测是否是分类标题
            is_title = False
            for key, section_name in section_mapping.items():
                if key in line and ("**" in line or "：" in line or ":" in line):
                    current_section = section_name
                    is_title = True
                    break

            # 如果不是标题且当前有分类，则添加为关键词
            if not is_title and current_section:
                # 清理关键词（去掉 markdown 标记、序号等）
                keyword = re.sub(r'^\d+[\.\、\)\s]*', '', line)  # 去掉序号
                keyword = re.sub(r'\*+', '', keyword)  # 去掉星号
                keyword = re.sub(r'^[-•]\s*', '', keyword)  # 去掉列表符号
                keyword = keyword.strip()

                if keyword and len(keyword) < 50:  # 过滤掉太长的内容（可能是说明文字）
                    sections[current_section].append(keyword)

        return sections

    def _format_content(self, content: str) -> str:
        """格式化内容文本"""
        if not content:
            return "等待分析..."

        # 移除 Markdown 标记，保留结构
        lines = []
        for line in content.split("\n"):
            line = line.strip()
            # 移除 ** 标记
            line = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)
            # 移除 ## 标记
            line = re.sub(r'^#+\s*', '', line)
            if line:
                lines.append(line)

        return "\n".join(lines)

    def _on_copy(self):
        """复制整个卡片内容"""
        if copy_to_clipboard(self.content):
            pass  # 静默复制

    def update_content(self, content: str):
        """更新卡片内容"""
        self.content = content
        # 重新构建内容区
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()


class CardContainer(ctk.CTkScrollableFrame):
    """卡片容器 - 可滚动"""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.cards: Dict[int, ModuleCard] = {}
        self._init_cards()

        # 增大滚动速度
        self._setup_scroll_speed()

    def _setup_scroll_speed(self):
        """设置滚动速度 - 通过修改内部 canvas 的滚动单位"""
        # CTkScrollableFrame 内部有一个 _parent_canvas 属性
        # 我们通过调整 yscrollincrement 来改变滚动速度
        try:
            # 设置滚动增量，数值越大滚动越快（默认约为5-10，设为15适中）
            self._parent_canvas.configure(yscrollincrement=15)
        except Exception:
            pass  # 如果失败就使用默认值

    def _init_cards(self):
        """初始化三个模块卡片"""
        for i in range(1, 4):
            card = ModuleCard(self, module_num=i, content="")
            card.pack(fill="x", padx=5, pady=8)
            self.cards[i] = card

    def update_module(self, module_num: int, content: str):
        """更新指定模块的内容"""
        if module_num in self.cards:
            self.cards[module_num].update_content(content)

    def clear_all(self):
        """清空所有卡片内容"""
        for card in self.cards.values():
            card.update_content("")

    def get_all_content(self) -> str:
        """获取所有卡片的内容"""
        contents = []
        for i in range(1, 4):
            if self.cards[i].content:
                config = ModuleCard.MODULE_CONFIG[i]
                contents.append(f"## {config['icon']} {config['title']}\n\n{self.cards[i].content}")
        return "\n\n".join(contents)
