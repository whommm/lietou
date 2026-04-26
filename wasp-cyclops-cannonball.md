# 弱全自动第一版实施计划

## 1. 目标概述

实现从岗位分析到候选人抓取、批量匹配的**全自动流水线**，核心交互流程：

1. 岗位分析完成后，AI输出多轮搜索关键词 + 匹配条件
2. 用户在「匹配条件」标签页确认/编辑匹配标准（一票否决、核心要求等）
3. 进入「候选人抓取」标签页，显示**抓取计划池子**（关键词轮次 + 筛选条件）
4. 点击「开始抓取」→ 弹出**15秒倒计时确认框**，可修改4个城市
5. 倒计时结束或用户确认后，程序自动：
   - 逐轮执行搜索（每轮不同关键词）
   - 每轮应用相同筛选条件（4城联合 + 年限 + 学历 + 性别等）
   - 每轮最多抓30人
   - **每轮抓完立即后台批量匹配**
6. 全部轮次完成后，弹窗显示战果汇总，用户可选择：
   - [收工] → 结束
   - [扩大到全国再抓一次] → 以"全国"为城市条件再跑一轮

---

## 2. 整体架构变更

### 2.1 新增模块

| 模块 | 文件路径 | 职责 |
|------|---------|------|
| 匹配条件标签页 | `src/ui/match_criteria_widget.py` | 显示/编辑岗位匹配标准，单独调用API生成 |
| 匹配条件服务 | `src/core/match_criteria_service.py` | 从岗位分析HTML提取匹配标准，单独调用LLM生成 |
| 城市数据 | `src/utils/city_data.py` | 城市周边映射表（如深圳→广州/东莞/惠州） |

### 2.2 修改模块

| 模块 | 修改内容 |
|------|---------|
| `src/ui/main_window.py` | 新增「匹配条件」标签页；倒计时弹窗；轮次完成回调触发批量匹配；全国扩城弹窗 |
| `src/ui/candidate_library_widget.py` | 抓取计划池子展示（轮次+筛选条件）；城市编辑入口 |
| `src/core/liepin_search_task_service.py` | 每轮max 30人控制；每轮完成后回调；全部完成后回调 |
| `src/core/liepin_search_service.py` | `search()` 支持传入 `filters` 参数，搜索后自动应用筛选 |
| `src/models/search_task.py` | SearchTask 增加 `filters` 字段存储筛选条件 |
| `src/core/batch_match_service.py` | 新增 `match_excel_range()` 方法，支持按行范围匹配 |
| `src/core/prompt.py` | 新增独立的匹配条件生成 prompt |

### 2.3 数据流图

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  岗位分析标签页  │────→│  匹配条件标签页   │────→│ 候选人抓取标签页 │
│  (已存在)       │     │  (新增)          │     │  (改造)         │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │                        │
         │                       │                        │
         ▼                       ▼                        ▼
   AI输出HTML报告         单独API调用生成            15秒倒计时确认框
   + 匹配标准JSON          MatchCriteria              （可改4个城市）
         │                       │                        │
         └───────────────────────┴────────────────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  SearchTask 创建      │
                         │  keywords + filters   │
                         └──────────────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ LiepinSearchTaskService
                         │ 逐轮执行搜索+筛选+抓取 │
                         │ 每轮30人后回调         │
                         └──────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              ┌─────────┐    ┌────────────┐   ┌─────────────┐
              │ 写Excel  │    │ 触发批量匹配 │   │ 继续下一轮   │
              │ (摘要)   │    │ (后台异步)   │   │             │
              └─────────┘    └────────────┘   └─────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ 全部轮次完成回调      │
                         │ 弹窗：收工 / 扩全国   │
                         └──────────────────────┘
```

---

## 3. 核心设计细节

### 3.1 匹配条件标签页（MatchCriteriaWidget）

#### 页面布局

左右双栏布局：
- **左侧面板**：岗位选择（同候选人抓取页）、生成/刷新按钮
- **右侧面板**：匹配条件编辑器

匹配条件编辑器包含4个折叠卡片：
1. **一票否决项**（红色）：可添加/删除/启用，每项有文本描述
2. **核心要求**（橙色）：可添加/删除/启用/设权重，底部显示权重总和校验
3. **基础要求**（蓝色）：可添加/删除/启用
4. **加分项**（绿色）：可添加/删除/启用
5. **常见误判提醒**：文本列表

底部按钮：
- `从岗位分析生成`：调用 MatchCriteriaService 从当前岗位分析HTML提取/生成
- `保存并确认`：持久化到数据库，标记为已确认

#### 数据持久化

在 `analysis_history` 表中，当前已有 `match_criteria_json` 字段（从代码看 main_window 构建 payload 时用了 `record.match_criteria_json`）。

流程：
1. 用户选择岗位分析历史
2. 若该记录已有 `match_criteria_json`，直接加载显示
3. 若不存在或用户点「重新生成」，调用 `MatchCriteriaService.generate(record.result, record.jd_text)`
4. 用户编辑后，保存回 `analysis_history.match_criteria_json`

#### MatchCriteriaService 设计

```python
class MatchCriteriaService:
    def __init__(self, llm_client: LLMClient):
        ...
    
    def extract_from_analysis(self, analysis_html: str) -> Optional[MatchCriteria]:
        """从岗位分析HTML中提取已有的匹配标准JSON"""
        # 正则匹配 prompt.py 要求的 JSON 格式
        
    def generate(self, analysis_html: str, jd_text: str) -> MatchCriteria:
        """单独调用API生成稳定的匹配标准"""
        # 构造专用 prompt（见 3.6 prompt 设计）
        # 调用 LLM，解析 JSON
        # 如果解析失败，返回一个基于JD的保底默认标准
        
    def to_rendered_text(self, criteria: MatchCriteria) -> str:
        """渲染为批量匹配服务可读的文本块"""
```

### 3.2 候选人抓取页改造（CandidateLibraryWidget）

#### 新增区域：抓取计划池子

在左侧面板（控制面板）下方新增一个只读展示区域：

```
┌─ 抓取计划 ─────────────────────────┐
│                                     │
│ 筛选条件：                           │
│   城市：深圳、广州、东莞、惠州 [修改]  │
│   工作年限：3-5年                    │
│   教育经历：本科及以上               │
│   性别：不限                         │
│                                     │
│ 搜索轮次（共3轮，每轮最多30人）：      │
│   第1轮：LED灯具 结构设计           │
│   第2轮：散热 注塑 灯具             │
│   第3轮：结构工程师 照明            │
│                                     │
└─────────────────────────────────────┘
```

**数据来源**：
- 筛选条件中的城市：从岗位分析HTML提取工作地址，结合城市周边映射表默认带出3个周边城市
- 其他筛选条件（年限、学历、性别）：从岗位分析HTML提取，或从匹配条件中推断
- 搜索轮次：`payload["strategy"]["executable_rounds"]`

**「修改」按钮**：点击后弹出一个小窗口，让用户修改4个城市（岗位城市+周边3个）。

#### 输入框调整

保留现有输入框：
- 抓取人数上限（默认改为30，因为每轮30人）
- 抓取页数上限（保留，作为兜底）

#### 回调接口变更

`on_run_task` 回调签名从：
```python
on_run_task(job_label, payload, max_candidates, max_pages)
```

改为：
```python
on_run_task(job_label, payload, filters, max_candidates, max_pages)
```

其中 `filters` 是一个字典：
```python
{
    "目前城市": ["深圳", "广州", "东莞", "惠州"],
    "工作年限": "3-5年",
    "教育经历": "本科",
    "性别": "不限",
}
```

### 3.3 15秒倒计时确认框

使用 `customtkinter.CTkToplevel` 实现模态弹窗。

#### 界面设计

```
┌─ 自动抓取确认 ─────────────────────────────┐
│                                             │
│  即将按以下条件自动抓取：                      │
│                                             │
│  岗位：LED灯具结构设计师                      │
│                                             │
│  筛选条件（点击可修改）：                      │
│  ┌─────────────────────────────────────┐   │
│  │ 城市：深圳、广州、东莞、惠州  [修改]  │   │
│  │ 年限：3-5年                          │   │
│  │ 学历：本科及以上                      │   │
│  │ 性别：不限                           │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  搜索计划（共3轮，每轮最多30人）：             │
│  • 第1轮：LED灯具 结构设计                  │
│  • 第2轮：散热 注塑 灯具                    │
│  • 第3轮：结构工程师 照明                   │
│                                             │
│  执行策略：每轮抓取后自动批量匹配              │
│                                             │
│         [ 立即开始 ]    [ 取消 ]            │
│                                             │
│              15秒后自动开始...               │
│                                             │
└─────────────────────────────────────────────┘
```

#### 交互逻辑

1. 弹窗打开时，启动一个 `self.after(1000, ...)` 倒计时
2. 每秒更新倒计时文字
3. 15秒结束时，若用户未操作，自动调用「立即开始」的逻辑
4. 点击「修改」按钮：弹出一个小的城市编辑框（4个输入框，对应岗位城市和周边3城）
5. 点击「立即开始」：关闭弹窗，返回 `filters` 字典给调用方
6. 点击「取消」：关闭弹窗，返回 `None`

#### 城市编辑小窗

```
┌─ 修改搜索城市 ──────────────┐
│                              │
│  岗位城市（必填）：深圳        │
│  周边城市1：广州              │
│  周边城市2：东莞              │
│  周边城市3：惠州              │
│                              │
│     [确认]    [恢复默认]     │
│                              │
└──────────────────────────────┘
```

**默认城市来源**：
- 岗位城市：从岗位分析HTML中提取的"工作地点"或"城市"
- 周边3城：从 `src/utils/city_data.py` 的 `CITY_ADJACENT` 映射表查

```python
CITY_ADJACENT = {
    "深圳": ["广州", "东莞", "惠州"],
    "北京": ["天津", "廊坊", "保定"],
    "上海": ["苏州", "杭州", "无锡"],
    "广州": ["深圳", "佛山", "东莞"],
    "杭州": ["上海", "苏州", "宁波"],
    # ... 可逐步扩充
}
```

### 3.4 搜索执行时序改造

#### SearchTask 模型扩展

在 `keywords` 字段中增加 `filters` 子字段：

```python
keywords = {
    "precise_keywords": [...],
    "expansion_keywords": [...],
    "executable_rounds": [...],
    "filters": {
        "目前城市": ["深圳", "广州", "东莞", "惠州"],
        "工作年限": "3-5年",
        "教育经历": "本科及以上",
        "性别": "不限",
    }
}
```

不需要修改 `SearchTask` 的表结构，复用现有的 `keywords_json` 字段。

#### liepin_search_service.py 改造

**方案A（推荐）：修改 `search()` 方法**

```python
def search(self, keyword: str, filters: Optional[Dict[str, Any]] = None) -> List[LiepinSearchCandidate]:
    """Run a keyword search, optionally apply filters, and return candidates."""
    ...
    def _run(page):
        self._execute_search(page, keyword.strip())
        if filters:
            self.apply_filters(filters)
        return self.extract_candidates_from_page(page)
```

**方案B：保持 `search()` 不变，在 `run_task()` 中先后调用**

```python
candidates = self.search_service.search(query)
self.search_service.apply_filters(task.keywords.get("filters", {}))
candidates = self.search_service.extract_current_page_candidates()
```

推荐**方案A**，因为筛选条件应该在搜索提交后立即应用，否则可能先看到无筛选的结果。

**关于城市多选**：

猎聘城市弹窗支持一次选最多5个城市。`liepin_search_service.py` 的 `_apply_city_filter()` 需要改造：

```python
def _apply_city_filter(self, page, spec, value):
    # value 可能是字符串（单城市）或列表（多城市）
    cities = value if isinstance(value, list) else [value]
    # 打开弹窗后，对每个城市：
    #   输入城市名 → 点击联想结果
    # 最后点击确认
```

#### liepin_search_task_service.py 改造

核心变更点：

1. **每轮最多抓30人**
   - 当前 `max_candidates` 是任务级的总人数上限
   - 新增每轮上限：每轮抓到30人或翻完 `max_pages` 后停止
   - 修改 `_process_candidate_batch()` 或 `run_task()` 的循环逻辑

2. **每轮完成后回调触发批量匹配**
   - `run_task()` 新增可选参数 `on_round_complete: Optional[Callable]`
   - 每轮循环结束后调用：`on_round_complete(excel_path, round_index, current_round_candidates)`

3. **全部完成后回调**
   - `run_task()` 新增可选参数 `on_all_complete: Optional[Callable]`
   - 所有轮次结束后调用：`on_all_complete(summary)`

修改后的 `run_task()` 核心逻辑：

```python
def run_task(
    self,
    task_id: str,
    cancel_event=None,
    on_round_complete: Optional[Callable] = None,
    on_all_complete: Optional[Callable] = None,
) -> SearchTaskExecutionSummary:
    ...
    for round_index, round_info in enumerate(rounds, start=1):
        ...
        candidates = self.search_service.search(query, filters=task.keywords.get("filters"))
        
        round_accepted = 0
        page_num = 1
        while page_num <= max_pages and round_accepted < 30:
            # 处理当前页候选人
            accepted = self._process_candidate_batch(
                candidates=candidates,
                max_accept=30 - round_accepted,
                ...
            )
            round_accepted += accepted
            
            # 翻页
            if round_accepted < 30:
                if not self.search_service.go_to_next_result_page():
                    break
                candidates = self.search_service.extract_current_page_candidates()
                page_num += 1
        
        # 本轮结束，触发回调
        if on_round_complete:
            on_round_complete(summary.excel_path, round_index, ...)
    
    # 全部完成
    if on_all_complete:
        on_all_complete(summary)
    
    return summary
```

### 3.5 批量匹配自动触发

#### 触发时机

每轮30人抓完后，在 `main_window._on_round_complete()` 中：

```python
def _on_round_complete(self, excel_path: str, round_index: int, ...):
    """每轮抓取完成后，自动提交批量匹配任务。"""
    # 1. 获取当前轮次新抓取的候选人（通过Excel行号范围或抓取时间筛选）
    # 2. 获取已确认的 MatchCriteria
    # 3. 提交批量匹配任务到 TaskQueue（COMPUTE 类别）
    
    match_criteria = self._get_confirmed_match_criteria(job_history_id)
    if not match_criteria:
        logger.warning("未确认匹配条件，跳过本轮批量匹配")
        return
    
    candidates = self.candidate_excel_service.load_candidates_for_round(excel_path, round_index)
    
    task_id = self.task_queue.submit(
        name=f"批量匹配 - 第{round_index}轮",
        category=TaskCategory.COMPUTE,
        target=self._do_round_batch_match,
        args=(excel_path, candidates, match_criteria, round_index),
    )
```

#### BatchMatchService 适配

当前 `match_excel_candidates()` 接受的是 `Iterable[CandidateExcelRecord]`，并且是多线程并发。

需要确认：并发调LLM时是否需要每个线程独立的LLMClient？当前代码中 `_match_single_excel_candidate()` 已经创建了独立client，所以可以直接复用。

新增 `CandidateExcelService.load_candidates_for_round()` 方法，根据 `round_index` 或 `source_keyword` 加载对应候选人。

或者更简单的方式：每轮抓完后，直接把本轮的候选人列表传给 `_do_round_batch_match`，不需要再从Excel读。

#### 战果汇总弹窗

全部轮次完成后，弹窗显示：

```
┌─ 抓取完成 ───────────────────────────────┐
│                                           │
│  全部轮次执行完毕！                        │
│                                           │
│  共执行3轮搜索                            │
│  累计抓取：87人（去重后）                  │
│                                           │
│  批量匹配进度：                            │
│  第1轮：已完成  S:2  A:8  B:15  C:5      │
│  第2轮：匹配中...                         │
│  第3轮：等待中                            │
│                                           │
│  当前城市范围：深圳+广州+东莞+惠州         │
│                                           │
│  [抓取结果已保存，打开Excel]              │
│                                           │
│     [收工]      [扩大到全国再抓一次]       │
│                                           │
└───────────────────────────────────────────┘
```

点击「扩大到全国再抓一次」：
1. 创建一个新的 SearchTask
2. `filters["目前城市"]` 改为空列表（表示全国）或移除城市筛选
3. 使用同样的 `executable_rounds`
4. 再次执行（不再弹15秒倒计时，直接开始）

### 3.6 Prompt 设计

#### 匹配条件生成专用 Prompt

当前 `prompt.py` 的 `MATCH_CRITERIA_PROMPT_APPENDIX` 是作为岗位分析 prompt 的附录，要求AI在分析岗位时顺便输出匹配标准。

新设计：单独一个 prompt，专门用于生成/修正匹配条件，更稳定。

```python
MATCH_CRITERIA_GENERATION_PROMPT = """
你是一位资深猎头顾问。请根据以下岗位描述（JD），输出一份结构化的候选人匹配标准。

【输出格式】
必须输出一个可被程序直接解析的 JSON 对象，格式如下：
{
  "dealbreakers": [
    {"id":"db_1","text":"...","enabled":true,"weight":0}
  ],
  "core_requirements": [
    {"id":"cr_1","text":"...","enabled":true,"weight":40},
    {"id":"cr_2","text":"...","enabled":true,"weight":30},
    {"id":"cr_3","text":"...","enabled":true,"weight":30}
  ],
  "basic_requirements": [
    {"id":"br_1","text":"...","enabled":true,"weight":0}
  ],
  "bonuses": [
    {"id":"bo_1","text":"...","enabled":true,"weight":0}
  ],
  "misjudgment_reminders": [
    "..."
  ],
  "version": 1,
  "confirmed_at": ""
}

【规则】
1. dealbreakers（一票否决）：不超过3项，必须是绝对硬门槛
2. core_requirements（核心要求）：3-6项，weight之和必须等于100
3. basic_requirements（基础要求）：2-4项
4. bonuses（加分项）：2-4项
5. misjudgment_reminders：列出2-3条容易误判的情况
6. 所有 text 必须具体可判断，避免模糊表述如"综合素质好"
7. 如果JD中某信息缺失，不要编造，而是降低该条件的重要性或移除

岗位描述：
{job_description}
"""
```

#### 筛选条件提取 Prompt（用于从岗位分析HTML提取）

如果已经有岗位分析HTML报告，可以从中提取城市、年限、学历等信息：

```python
FILTER_EXTRACTION_PROMPT = """
从以下岗位分析报告中，提取用于猎聘搜索的筛选条件。

请输出JSON：
{
  "work_city": "深圳",
  "work_years": "3-5年",
  "education": "本科及以上",
  "gender": "不限"
}

如果某项无法确定，输出空字符串。
"""
```

不过更实际的做法是：**从岗位分析HTML中用正则/文本提取**，而不是再调一次API。因为城市、年限这些信息在JD原文中通常很明确，不需要LLM也能提取（比如正则匹配"工作地点：深圳"、"本科及以上学历"、"3年以上经验"）。

### 3.7 筛选条件的数据来源与优先级

| 筛选条件 | 数据来源 | 提取方式 |
|---------|---------|---------|
| 城市 | 岗位分析HTML中的"工作地点" | 正则提取 + 城市映射表 |
| 工作年限 | 岗位分析HTML中的年限要求 | 正则提取（如"3-5年"、"5年以上"） |
| 教育经历 | 岗位分析HTML中的学历要求 | 正则提取（本科/硕士/大专） |
| 性别 | 岗位分析HTML | 正则提取（若JD未提，默认"不限"） |
| 年龄 | 岗位分析HTML | 正则提取（如"35岁以下"）→ 暂不实现 |

提取逻辑放在 `search_strategy_service.py` 或新建的 `match_criteria_service.py` 中。

---

## 4. 实施步骤（Phase划分）

### Phase 1：匹配条件标签页（2-3天）

1. 新建 `src/core/match_criteria_service.py`
   - 实现 `extract_from_analysis()`：从HTML提取已有匹配标准
   - 实现 `generate()`：单独调API生成匹配标准
   - 实现 `to_rendered_text()`

2. 新建 `src/ui/match_criteria_widget.py`
   - 左右双栏布局
   - 4个条件卡片（一票否决、核心要求、基础要求、加分项）
   - 权重校验显示
   - 生成/保存按钮

3. 修改 `src/ui/main_window.py`
   - 新增「匹配条件」标签页
   - 岗位分析完成后自动同步到匹配条件页

4. 修改 `src/core/prompt.py`
   - 新增 `MATCH_CRITERIA_GENERATION_PROMPT`

### Phase 2：候选人抓取页改造 + 倒计时弹窗（2-3天）

1. 新建 `src/utils/city_data.py`
   - `CITY_ADJACENT` 映射表
   - `extract_city_from_text(text)` 正则提取城市
   - `get_default_adjacent_cities(city)` 查询周边城市

2. 修改 `src/ui/candidate_library_widget.py`
   - 新增抓取计划池子展示区域
   - 城市编辑小窗
   - 筛选条件展示

3. 修改 `src/ui/main_window.py`
   - 实现15秒倒计时确认框（`AutoGrabConfirmDialog`）
   - 从岗位分析结果提取默认筛选条件
   - 倒计时结束后调用 `_on_run_candidate_task()`

4. 修改 `src/core/search_strategy_service.py`
   - 新增 `extract_filters_from_analysis()` 方法

### Phase 3：搜索执行改造（2-3天）

1. 修改 `src/core/liepin_search_service.py`
   - `search()` 支持 `filters` 参数
   - `_apply_city_filter()` 支持多城市列表

2. 修改 `src/core/liepin_search_task_service.py`
   - 每轮max 30人控制
   - `on_round_complete` / `on_all_complete` 回调
   - 从 `task.keywords["filters"]` 读取筛选条件

3. 修改 `src/models/search_task.py`
   - 确认 `keywords` 字段能容纳 `filters` 子字段（当前已经是Dict，无需改表结构）

### Phase 4：批量匹配自动触发 + 扩城弹窗（2-3天）

1. 修改 `src/core/batch_match_service.py`
   - 新增 `match_excel_range()` 或确认 `match_excel_candidates()` 可按范围调用

2. 修改 `src/core/candidate_excel_service.py`
   - 新增 `get_candidates_by_round()` 或类似方法

3. 修改 `src/ui/main_window.py`
   - `_on_round_complete()`：提交批量匹配任务
   - `_on_all_complete()`：弹出战果汇总 + 扩城选择
   - `_on_expand_to_nationwide()`：创建全国范围的新任务

4. 修改 `src/core/liepin_search_task_service.py`
   - 回调接口的最终集成

### Phase 5：联调与真实岗位验证（1-2天）

1. 端到端走通一条真实岗位链路
2. 测试城市多选筛选
3. 测试每轮30人后自动批量匹配
4. 测试扩城弹窗
5. 修bug

**总工期预估：9-14天（视bug数量浮动）**

---

## 5. 风险与备选方案

### 风险1：城市多选在猎聘弹窗中不稳定

- **风险**：猎聘城市弹窗虽然支持多选，但不同浏览器/账号的弹窗结构可能有差异
- **备选**：若多选不稳定，改为单城市依次搜索（深圳搜一轮→广州搜一轮→...），每城抓30/4≈8人
- **当前判断**：风险中等，因为代码里已有 `_apply_city_filter()` 的弹窗操作基础

### 风险2：匹配条件单独调API增加费用和延迟

- **风险**：每分析一个岗位要多调一次API，增加成本和等待时间
- **备选**：第一次调岗位分析API时，在prompt中强制要求匹配标准JSON必须稳定输出；只有在解析失败时才单独调一次
- **当前判断**：风险低，因为匹配条件生成是轻量级调用（比岗位分析简单）

### 风险3：每轮30人后批量匹配导致Excel频繁读写

- **风险**：每轮都要从Excel读取候选人、匹配完再写回，I/O可能成为瓶颈
- **备选**：批量匹配结果先缓存到内存，全部轮次完成后再一次性写回Excel
- **当前判断**：风险低，30人×3轮=90人，Excel文件很小，当前实现应该够用

### 风险4：筛选条件正则提取不准确

- **风险**：JD写法千变万化，正则提取城市/年限可能漏或错
- **备选**：提取后让用户在15秒倒计时里确认/修改；AI辅助提取（调轻量API）
- **当前判断**：风险中等，但倒计时确认机制已经兜底

---

## 6. 接口变更清单

### 新增类/方法

| 类/方法 | 所在文件 | 说明 |
|---------|---------|------|
| `MatchCriteriaService` | `src/core/match_criteria_service.py` | 匹配条件生成与管理 |
| `MatchCriteriaWidget` | `src/ui/match_criteria_widget.py` | 匹配条件标签页UI |
| `AutoGrabConfirmDialog` | `src/ui/main_window.py` (内嵌) | 15秒倒计时确认弹窗 |
| `CityEditDialog` | `src/ui/main_window.py` (内嵌) | 4城市编辑小窗 |
| `CITY_ADJACENT` | `src/utils/city_data.py` | 城市周边映射表 |
| `extract_filters_from_analysis()` | `src/core/search_strategy_service.py` | 从HTML提取筛选条件 |
| `search(keyword, filters=None)` | `src/core/liepin_search_service.py` | 扩展签名 |
| `run_task(..., on_round_complete, on_all_complete)` | `src/core/liepin_search_task_service.py` | 扩展签名 |

### 修改类/方法

| 类/方法 | 修改内容 |
|---------|---------|
| `CandidateLibraryWidget` | 新增计划池子展示、城市编辑回调 |
| `MainWindow` | 新增匹配条件标签页、倒计时弹窗、批量匹配自动触发、扩城弹窗 |
| `LiepinSearchTaskService.run_task()` | 每轮30人限制、回调触发 |
| `LiepinSearchService._apply_city_filter()` | 支持多城市列表 |
| `SearchTaskRepository.create()` | 无修改（filters存入keywords即可） |
| `BatchMatchService` | 确认/新增按范围匹配方法 |
| `CandidateExcelService` | 新增按轮次读取方法 |

---

## 7. 用户确认事项

以下事项需要在实施前或实施中确认：

1. **城市映射表**：我先提供Top 20城市的默认周边映射，你是否需要覆盖更多城市？
2. **每轮30人**：是指"本轮所有页加起来30人"，还是"每页30人只抓1页"？（当前设计是前者：翻页直到够30人或无下一页）
3. **扩大到全国**：是全国（不设城市筛选），还是"当前4城+全国其他城市"？（当前设计是"不设城市筛选"，即全国）
4. **匹配条件标签页的入口位置**：放在"岗位分析"和"候选人抓取"之间，还是放在最后？（推荐放中间：岗位分析 → 匹配条件 → 候选人抓取 → 批量匹配）
