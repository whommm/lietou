# UI布局统一设计文档

## 一、目标

将"简历匹配"和"公司调研"标签页的布局、按钮风格统一为与"岗位分析"一致的左右分栏布局。

## 二、岗位分析布局参考

```
+--------------------------------------------------+
|  左侧 (weight=2)           |  右侧 (weight=3)    |
+--------------------------------------------------+
|  标题: 原始岗位描述(JD)     |  标题: 分析结果      |
|  [JD文本输入框]             |  [原文] [卡片] [历史] |
|                            |  [复制全部] [清空]   |
|                            |  [结果文本框/卡片容器] |
|  [清空]        [开始分析]   |                     |
+--------------------------------------------------+
```

## 三、简历匹配布局改造

### 当前布局（垂直pack）
```
[岗位选择下拉框]
[简历输入框]
[开始匹配分析按钮]
[结果文本框]
```

### 目标布局（左右分栏）
```
+--------------------------------------------------+
|  左侧 (weight=2)           |  右侧 (weight=3)    |
+--------------------------------------------------+
|  标题: 📋 简历匹配分析       |  标题: 匹配结果      |
|  描述文字                    |  [复制全部] [清空]   |
|  选择岗位: [下拉框]          |  [结果文本框]        |
|  候选人简历: [文本框]        |                     |
|  [清空]        [开始匹配分析] |                     |
+--------------------------------------------------+
```

## 四、公司调研布局改造

### 当前布局
```
+--------------------------------------------------+
|  左侧                     |  右侧                 |
+--------------------------------------------------+
|  🔍 公司深度调研            |  标题: 调研报告       |
|  描述文字                   |  [复制全部]          |
|  历史记录: [下拉框]          |  [结果文本框]        |
|  公司名称: [输入框]          |                     |
|  [开始深度调研] [清空]       |                     |
+--------------------------------------------------+
```

### 目标布局
```
+--------------------------------------------------+
|  左侧 (weight=2)           |  右侧 (weight=3)    |
+--------------------------------------------------+
|  标题: 🔍 公司深度调研       |  标题: 调研报告      |
|  描述文字                   |  [复制全部] [清空]   |
|  公司名称: [输入框]          |  [结果文本框]        |
|  [清空]        [开始深度调研] |                     |
+--------------------------------------------------+
```

## 五、详细修改方案

### 5.1 `src/ui/resume_match_widget.py` 完整重写

**修改要点：**
1. 将 `_setup_ui()` 从 `pack` 布局改为 `grid` 左右分栏
2. 新增 `_build_input_panel()` 方法构建左侧输入面板
3. 新增 `_build_result_panel()` 方法构建右侧结果面板
4. 新增 `_on_clear_click()` 清空输入方法
5. 新增 `_on_clear_result_click()` 清空结果方法
6. 新增 `_on_copy_all_click()` 复制全部方法
7. 新增 `set_matching()` 方法控制按钮状态
8. 修改 `append_result()` 方法，增加 `state="normal"/"disabled"` 控制
9. 修改 `enable_match_button()` 方法，调用 `set_matching(False)`

**新文件结构：**
```python
class ResumeMatchWidget(ctk.CTkFrame):
    def __init__(self, master, on_match, job_list, **kwargs)
    def _setup_ui(self)           # 改为grid布局
    def _build_input_panel(self)  # 新增：左侧输入面板
    def _build_result_panel(self) # 新增：右侧结果面板
    def _on_match_click(self)     # 修改：使用messagebox提示
    def _on_clear_click(self)     # 新增：清空输入
    def _on_clear_result_click(self)  # 新增：清空结果
    def _on_copy_all_click(self)  # 新增：复制全部
    def set_matching(self, matching)  # 新增：设置匹配状态
    def update_job_list(self, job_list, job_data_map)
    def append_result(self, text) # 修改：增加state控制
    def enable_match_button(self) # 修改：调用set_matching
```

### 5.2 `src/ui/company_research_widget.py` 修改

**修改要点：**
1. 修改 `_build_input_panel()` 中的按钮布局：
   - 将"开始深度调研"和"清空"按钮放在同一个 `btn_frame` 中
   - 清空按钮左对齐 (`sticky="w"`)
   - 开始调研按钮右对齐 (`sticky="e"`)
2. 修改 `_build_result_panel()` 中的按钮布局：
   - 添加清空按钮（位于复制全部按钮左侧）

**具体修改：**
```python
# _build_input_panel() 按钮区修改
btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
btn_frame.grid(row=6, column=0, padx=10, pady=(0, 10), sticky="ew")
btn_frame.grid_columnconfigure(0, weight=1)

self.clear_btn = ctk.CTkButton(
    btn_frame, text="清空", width=60, fg_color="gray",
    command=self._on_clear_click
)
self.clear_btn.grid(row=0, column=0, padx=5, sticky="w")

self.research_btn = ctk.CTkButton(
    btn_frame, text="开始深度调研",
    command=self._on_research_click
)
self.research_btn.grid(row=0, column=1, padx=5, sticky="e")

# _build_result_panel() 添加清空按钮
self.clear_result_btn = ctk.CTkButton(
    header_frame, text="清空", width=60, height=28,
    fg_color="gray", command=self._on_clear_result_click
)
self.clear_result_btn.pack(side="right", padx=5)
```

## 六、修改文件清单

| 文件 | 修改类型 | 说明 |
|------|---------|------|
| `src/ui/resume_match_widget.py` | 重写 | 改为左右分栏布局 |
| `src/ui/company_research_widget.py` | 部分修改 | 调整按钮布局，添加清空结果按钮 |

## 七、验证清单

- [ ] 简历匹配标签页显示为左右分栏布局
- [ ] 简历匹配左侧包含：标题、描述、岗位选择、简历输入、清空/开始匹配按钮
- [ ] 简历匹配右侧包含：标题、复制全部/清空按钮、结果文本框
- [ ] 公司调研左侧按钮：清空左对齐，开始调研右对齐
- [ ] 公司调研右侧包含：标题、复制全部/清空按钮、结果文本框
- [ ] 三个标签页的按钮风格和布局一致
