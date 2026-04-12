# 批量匹配模块重设计划

> 状态：设计稿 v1.1（已结合代码评审修正）  
> 原则：**不增加 LLM 单次调用次数**（控制时间成本），通过**结构化匹配标准 + 人机协同校准 + 内部推断链**提升匹配准确性。

---

## 1. 背景与问题诊断

### 1.1 当前流程

当前批量匹配将 **原始 JD 全文** 与 **候选人简历全文** 直接拼接成一个大 prompt，一次性交给 LLM 打分。流程过于粗放，导致：

1. **信息过载**：简历与 JD 都很长，LLM 注意力被华丽项目描述带偏，忽略真正的硬性门槛。
2. **重点不分级**：JD 里混着硬性门槛、核心要求、套话/加分项，LLM 只能凭感觉打分。
3. **评分无统一量规**：每次匹配独立进行，同一人不同批次分数可能差 20 分。
4. **过度纠结形式**：LLM 容易死抠"base 地"、"5 年 vs 4.5 年"等形式差异，忽略实质能力匹配。
5. **缺乏合理推断**：候选人"做过但没写"的能力（如做过电商后端 → 具备微服务/高并发经验）被直接忽略。

### 1.2 根本结论

**不是 LLM 不够聪明，而是 prompt 没给它一张"草稿纸"和一把"统一尺子"。**

---

## 2. 设计目标

| 目标 | 定义 |
|------|------|
| **准确性** | 硬性门槛不过杀，实质能力不错杀，加分项不喧宾夺主 |
| **一致性** | 同一岗位、同一批次候选人使用完全一致的评分标准 |
| **可解释性** | 每个分数都能追溯到具体维度和依据 |
| **人机协同** | 猎头顾问可在 LLM 提取的匹配标准基础上人工校准 |
| **时间可控** | 不增加单次 LLM 调用次数（仍为 1 次/候选人） |

---

## 3. 核心设计原则

### 3.1 岗位分析即"总开关"

- 岗位分析环节不再只输出"给人类看的报告"，还要输出**结构化的机器可读匹配标准**。
- 该标准经人工确认/编辑后，作为后续所有批量匹配的**唯一输入来源**。

### 3.2 单次调用，双阶段内部推理

批量匹配时仍只调用 1 次 LLM/候选人，但 prompt 强制 LLM 内部执行两个阶段：

1. **阶段 A：简历深度解读**（草稿纸）
   - 显式能力清单
   - 推断能力清单（必须注明依据）
   - 待验证点
2. **阶段 B：结构化比对**（打分）
   - 逐条核对匹配标准
   - 按 Rubric 维度评分
   - 后端接管总分计算

### 3.3 推断有授权，瞎猜有禁区

- **允许推断**：基于通用职业知识和项目上下文，推断候选人未明确写出但合理具备的能力。
- **禁止瞎猜**：严禁推断学历细节、年龄、婚姻、籍贯、性格、具体技术版本等无法从简历观察的信息。

### 3.4 权重与容错人工可编辑

- 核心要求的权重、一票否决项的开关、常见误判提醒的文本，全部可在 UI 中修改。
- 批量匹配执行时会锁定一份**快照（snapshot）**，以 JSON 字符串形式存入 `batch_match_jobs`（或 `batch_match_jobs_v2`）表的 `match_criteria_snapshot` 字段，防止中途修改导致同一批次标准不一致。

---

## 4. 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│  阶段 1：岗位分析（新增输出：结构化匹配标准）                     │
│  ├─ LLM 输出完整 HTML 报告（给人看）                            │
│  └─ LLM 在 HTML 末尾输出 match_criteria_json（给机器读）       │
├─────────────────────────────────────────────────────────────────┤
│  阶段 2：人工校准（新增 UI：匹配标准编辑器）                     │
│  ├─ 嵌入在岗位分析结果页顶部                                    │
│  ├─ 开关一票否决项                                              │
│  ├─ 增删改核心/基础/加分项                                      │
│  ├─ 调整核心要求权重（滑条，自动归一化）                        │
│  └─ 编辑常见误判提醒                                            │
├─────────────────────────────────────────────────────────────────┤
│  阶段 3：批量匹配（复用已确认的匹配标准）                       │
│  ├─ 读取 match_criteria_snapshot                                │
│  ├─ 对每个候选人调用 1 次 LLM（使用独立 BATCH_MATCH_PROMPT）   │
│  │   ├─ Step 1: 简历深度解读（显式 + 推断 + 待验证）           │
│  │   ├─ Step 2: 硬性门槛核对                                    │
│  │   ├─ Step 3: 维度评分（输出 4 个原始分）                    │
│  │   └─ Step 4: 输出结构化 JSON（供后端精确算总分）            │
│  └─ 后端按权重公式计算总分，生成可解释报告                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. 匹配标准的数据结构（`MatchCriteria`）

建议用 JSON 存储，便于 UI 双向绑定和 Prompt 拼接。

```json
{
  "dealbreakers": [
    {
      "id": "db_1",
      "text": "必须有 5 年以上后端开发经验",
      "enabled": true
    },
    {
      "id": "db_2",
      "text": "必须带过 3 人以上技术团队",
      "enabled": false
    }
  ],
  "core_requirements": [
    {
      "id": "core_1",
      "text": "熟练掌握 Java 及 Spring 生态",
      "weight": 40
    },
    {
      "id": "core_2",
      "text": "具备高并发/分布式系统实战经验",
      "weight": 30
    }
  ],
  "basic_requirements": [
    {
      "id": "basic_1",
      "text": "统招本科及以上学历"
    },
    {
      "id": "basic_2",
      "text": "具备基础的数据库设计能力"
    }
  ],
  "bonuses": [
    {
      "id": "bonus_1",
      "text": "有微服务治理经验（如 Dubbo、Spring Cloud）"
    }
  ],
  "misjudgment_reminders": [
    "年限：JD 要求年限 ±6 个月视为完全匹配，±1 年视为基本可接受，差距 >1 年才视为明显不符",
    "地点：除非 JD 明确写'必须 base 某地且不接受远程'，否则不视为硬门槛",
    "学历：除非明确要求'全日制统招本科'，否则专升本/自考视为等同",
    "技术栈：允许用相近技术替代，如 Vue 和 React 对于前端通用岗位可互通"
  ],
  "version": 1,
  "confirmed_at": "2026-04-11T22:30:00"
}
```

### 5.1 校验规则

- `core_requirements` 中所有启用的项的 `weight` 之和必须等于 100。
- 若用户调整导致和不等于 100，UI 自动归一化（按比例缩放，保留整数）。
- `dealbreakers` 至少允许为空列表。

---

## 6. Prompt 设计

### 6.1 岗位分析 Prompt 新增模块

在现有 `SYSTEM_PROMPT` 末尾新增强制输出区块：

```text
请在报告末尾单独输出一个 <div class="card card-red" id="match-criteria"> 区块，
其中包含匹配标准。同时，请在输出结束后，紧接着输出一段可被程序直接解析的 JSON（不包裹在代码块中），
格式如下：

{"dealbreakers":[{"id":"db_1","text":"...","enabled":true},...],"core_requirements":...}

这段 JSON 必须严格遵循上述 MatchCriteria 结构。
```

**解析注意事项**：由于 LLM 可能把 JSON 嵌在 `<pre>`、`<code>` 标签或 Markdown 代码块中，后端解析时应采用多层 fallback 策略：
1. 优先从响应文本末尾用贪婪正则 `r"\{.*\}\s*$"` 提取裸 JSON。
2. 若失败，尝试提取 Markdown 代码块中的 JSON。
3. 若仍失败，尝试提取 `<pre>` / `<code>` 标签中的 JSON。
4. 最终 fallback：用正则从 HTML 文本中逐条提取硬性门槛、核心要求等信息，手动组装 `MatchCriteria`。

### 6.2 批量匹配 Prompt（新增独立 `BATCH_MATCH_PROMPT`）

> **重要**：批量匹配使用全新的 `BATCH_MATCH_PROMPT`，**不改动现有的 `RESUME_MATCH_PROMPT`**，以避免影响"简历匹配"标签页的单条 HTML 输出。

```text
你是一位资深猎头顾问，现在需要判断候选人与目标岗位是否值得推进。

【岗位匹配标准 - 已人工校准】
{rendered_criteria}

【推断规则 - 必须遵守】
- 允许基于通用职业知识和项目上下文进行合理推断，但每条推断必须在括号内注明具体依据。
- 例如：候选人写"负责某金融系统的核心交易模块"，可推断"具备金融风控意识（推断依据：负责金融核心交易模块开发）"。
- 严禁推断学历细节、年龄、婚姻、籍贯、性格、具体技术版本等无法从简历观察的信息。

【分析步骤 - 必须按顺序执行，严禁跳过】

步骤 1：简历深度解读
请先客观解读候选人的简历，不要急于下结论。输出以下内容：
- 显式能力：简历上明确提到的核心技能、管理经验、行业背景
- 推断能力：基于项目经历和通用职业知识可以合理推断出的能力。每条推断必须在括号内注明具体依据。
  例如："具备微服务架构经验（推断依据：负责电商平台订单系统后端开发，涉及高并发场景）"
- 待验证点：简历中未提及且无法推断，但对岗位很重要的信息

步骤 2：硬性门槛核对
逐条核对岗位匹配标准中的"一票否决项"（仅核对 enabled=true 的项）：
- 如果明确不满足，直接说明哪条不满足，并将总分封顶为 40 分
- 如果没有一票否决项，或仅存在轻微差异（如地点可协商、年限差 6 个月以内），不要视为否决
- 请严格遵守"常见误判提醒"中的容错规则

步骤 3：维度评分
请严格按以下量规评分，每项给出 0-100 的整数分数，并附一句话依据：

1. 核心能力匹配（权重 {core_weight}%）：[0-100 整数] / 依据：[一句话，可引用推断能力]
2. 经验职级匹配（权重 {exp_weight}%）：[0-100 整数] / 依据：[一句话，注意年限容错规则]
3. 行业背景匹配（权重 {industry_weight}%）：[0-100 整数] / 依据：[一句话]
4. 软性加分项（权重 {soft_weight}%）：[0-100 整数] / 依据：[一句话]

步骤 4：最终结论
- 匹配度分数：由系统根据上述 4 个原始分和权重自动计算，你只需给出 4 个原始分
- 建议动作：[直接推荐 / 顾问深聊后再推 / 信息不足需补充 / 暂不建议推进]
- 一句话结论：[用一句话总结这个候选人为什么值得推或不值得推]
- 关键风险：[最大风险点，或"未发现明显风险"]

【输出格式强制要求】
1. 先输出纯文本分析（按步骤 1-3）
2. 最后必须严格输出以下 JSON 对象，且不要包裹在 Markdown 代码块中：
   {"core_score":85,"exp_score":90,"industry_score":70,"soft_score":60,"dealbreaker_hit":false,"recommendation":"顾问深聊后再推","summary":"技术栈匹配度高，但管理经验待验证","risks":"未明确带过超过5人的团队"}
3. 如果存在一票否决项命中，dealbreaker_hit 必须为 true

【候选人简历】
{resume}
```

### 6.3 权重渲染逻辑

`{rendered_criteria}` 的示例：

```text
<一票否决项>
- [启用] 必须有 5 年以上后端开发经验
- [禁用] 必须带过 3 人以上技术团队

<核心要求>
- 熟练掌握 Java 及 Spring 生态 — 权重 40%
- 具备高并发/分布式系统实战经验 — 权重 30%

<基础要求>
- 统招本科及以上学历
- 具备基础的数据库设计能力

<加分项>
- 有微服务治理经验（如 Dubbo、Spring Cloud）

<常见误判提醒 - 匹配时严格遵守>
- 年限：JD 要求年限 ±6 个月视为完全匹配，±1 年视为基本可接受
- 地点：除非明确写'不接受远程'，否则不视为硬门槛
- 学历：除非明确要求'全日制统招'，否则专升本视为等同
```

---

## 7. UI/UX 设计

### 7.1 新增「匹配标准编辑器」组件

嵌入在**岗位分析结果展示页**（`job_analysis_widget.py`）的最上方，因为这是最重要的 actionable output。

建议新建独立组件 `MatchCriteriaEditor`，作为可复用控件，嵌入在 `JobAnalysisWidget` 的结果面板顶部。

#### 布局（三栏或卡片堆叠）

```
┌─────────────────────────────────────────────┐
│  匹配标准编辑器                              │
│  [保存并用于后续批量匹配]  [恢复默认]        │
├─────────────────────────────────────────────┤
│  一票否决项                                  │
│  ☑ 必须有 5 年以上后端开发经验      [删除]  │
│  ☐ 必须带过 3 人以上技术团队        [删除]  │
│  [+ 新增]                                    │
├─────────────────────────────────────────────┤
│  核心要求（权重自动归一化）                  │
│  熟练掌握 Java 及 Spring 生态  [====40%===]  │
│  具备高并发/分布式实战经验     [====30%===]  │
│  具备云原生/DevOps 经验        [====30%===]  │
│                                              │
│  当前权重总和：100% ✅                       │
├─────────────────────────────────────────────┤
│  基础要求                                    │
│  统招本科及以上学历        [🔴][删除]        │
│  [+ 新增]                                    │
├─────────────────────────────────────────────┤
│  加分项                                      │
│  有微服务治理经验                   [删除]  │
│  [+ 新增]                                    │
├─────────────────────────────────────────────┤
│  常见误判提醒                                │
│  [多行文本编辑区]                            │
└─────────────────────────────────────────────┘
```

#### 交互细节

- **权重滑条**：拖动时实时显示百分比，鼠标松开后自动归一化所有核心要求权重。
- **保存按钮**：保存后显示绿色提示"匹配标准已保存，后续批量匹配将使用此版本"。
- **重置按钮**：可恢复为 LLM 最初生成的版本。
- **必填校验**：至少要有 1 条核心要求；若全部核心要求权重为 0，保存时弹出提示。
- **基础要求升级**：基础要求列表右侧增加"🔴 设为硬门槛"按钮，点击后从基础列表移除，自动追加到 dealbreakers 列表末尾，`enabled=true`。

### 7.2 批量匹配结果展示优化

在现有的结果展示中，增加每个候选人的**维度拆解**（展示在 `BatchMatchWidget` 的摘要区域）：

```
晋** — 综合匹配度 82 分
  核心能力 85 分 | 经验职级 80 分 | 行业背景 90 分 | 软性加分 70 分
  建议：顾问深聊后再推
  关键风险：管理经验待验证（简历未明确带过超过 5 人的团队）
  [查看详细推断]
```

点击"查看详细推断"可展开 LLM 在步骤 1 中输出的"显式能力 + 推断能力 + 待验证点"。

---

## 8. 数据流与模块职责

### 8.1 新增/改造的数据模型

```python
# src/models/match_criteria.py

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MatchCriterionItem:
    id: str
    text: str
    enabled: bool = True
    weight: int = 0  # 仅 core_requirements 使用


@dataclass
class MatchCriteria:
    dealbreakers: List[MatchCriterionItem]
    core_requirements: List[MatchCriterionItem]
    basic_requirements: List[MatchCriterionItem]
    bonuses: List[MatchCriterionItem]
    misjudgment_reminders: List[str]
    version: int = 1
    confirmed_at: Optional[str] = None
```

### 8.2 模块职责

| 模块 | 职责 |
|------|------|
| `prompt.py` | 修改 `SYSTEM_PROMPT`（增加匹配标准 JSON 输出要求）；**新增** `BATCH_MATCH_PROMPT`（批量匹配专用，不影响 `RESUME_MATCH_PROMPT`） |
| `llm_client.py` | `analyze_jd()` 返回的 HTML 末尾会包含匹配标准 JSON；保持不变即可 |
| `analysis_history_repository.py` | 新增 `match_criteria_json` 字段的读写；注意使用 `ALTER TABLE` 而非删库重建 |
| `history.py` | `HistoryRecord` 增加 `match_criteria_json` 字段；`AnalysisHistoryRepository` 已处理持久化 |
| `batch_match_service.py` | 读取已确认的匹配标准 → 渲染 prompt → 调用 LLM → 解析 JSON 原始分 → 精确计算总分 |
| `job_analysis_widget.py` | 在结果面板顶部嵌入 `MatchCriteriaEditor`；负责展示/编辑/保存匹配标准 |
| `batch_match_widget.py` | 批量匹配结果摘要中展示 4 维拆解 + 加权总分 |
| `main_window.py` | 串联"保存匹配标准 → 触发批量匹配"的交互；负责把 `match_criteria` 注入 `BatchMatchService` |

### 8.3 关键函数签名建议

```python
# batch_match_service.py
class BatchMatchService:
    def match_excel_candidates(
        self,
        job_description: str,          # 保留兼容，但实际用于兜底
        match_criteria: MatchCriteria,  # 新增：核心输入
        candidates: Iterable[CandidateExcelRecord],
        progress_callback: Optional[Callable] = None,
    ) -> List[BatchMatchTextResult]:
        ...

    def _build_batch_match_prompt(
        self,
        match_criteria: MatchCriteria,
        resume: str,
    ) -> str:
        ...

    def _compute_weighted_score(
        self,
        core_score: int,
        exp_score: int,
        industry_score: int,
        soft_score: int,
        dealbreaker_hit: bool,
        match_criteria: MatchCriteria,
    ) -> int:
        ...


# src/ui/match_criteria_editor.py（建议新建）
class MatchCriteriaEditor(ctk.CTkFrame):
    def __init__(
        self,
        master,
        criteria: MatchCriteria,
        on_save: Callable[[MatchCriteria], None],
        on_change: Optional[Callable[[MatchCriteria], None]] = None,
    ):
        ...

    def set_criteria(self, criteria: MatchCriteria):
        ...

    def get_criteria(self) -> MatchCriteria:
        ...
```

---

## 9. 数据库迁移方案（渐进式，保护历史数据）

当前数据库 `liepin_workbench.db` 中已存在旧版 `batch_match_jobs`、`batch_match_results`、`batch_match_job_candidates` 等表，且 `analysis_history` 已有真实历史记录。**不允许直接删库重建**。

### 9.1 analysis_history 表（ALTER TABLE 迁移）

```sql
ALTER TABLE analysis_history ADD COLUMN match_criteria_json TEXT;
ALTER TABLE analysis_history ADD COLUMN match_criteria_confirmed BOOLEAN DEFAULT 0;
```

### 9.2 批量匹配新表（新建 v2 表，保留旧数据）

旧表 `batch_match_jobs` 和 `batch_match_results` 的字段与新版设计不符，建议保留旧表、新建 v2 表：

```sql
-- 批量匹配任务（新版）
CREATE TABLE IF NOT EXISTS batch_match_jobs_v2 (
    id TEXT PRIMARY KEY,
    job_history_id TEXT REFERENCES analysis_history(id),
    match_criteria_snapshot TEXT NOT NULL,  -- 锁定执行时的标准版本 JSON
    candidate_count INTEGER,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    started_at TEXT,
    finished_at TEXT
);

-- 批量匹配结果（新版）
CREATE TABLE IF NOT EXISTS batch_match_results_v2 (
    id TEXT PRIMARY KEY,
    batch_job_id TEXT REFERENCES batch_match_jobs_v2(id),
    candidate_id TEXT,
    core_score INTEGER,
    exp_score INTEGER,
    industry_score INTEGER,
    soft_score INTEGER,
    weighted_score INTEGER,
    dealbreaker_hit BOOLEAN,
    recommendation TEXT,
    summary TEXT,
    risks TEXT,
    detail TEXT,           -- LLM 完整原始输出
    inferred_abilities TEXT, -- 推断能力 JSON 或文本
    status TEXT DEFAULT 'completed',
    created_at TEXT
);
```

> 注：`batch_match_service.py` 的 `repository` 目前为可选参数（`None` 时走内存模式），因此新版表结构的对接不会影响现有无 repository 的单元测试路径。

---

## 10. 实施里程碑

### Milestone 0：最小可用闭环（强烈推荐先做）
**周期：1 天 | 不碰 UI 和数据库**
- 手写 1 个真实岗位的 `MatchCriteria` JSON，硬编码在 `main_window.py` 中。
- 新建 `BATCH_MATCH_PROMPT`，改造 `BatchMatchService.match_excel_candidates()` 接受 `match_criteria`。
- 跑 5-10 个真实简历，验证 JSON 输出稳定和评分逻辑合理。
- **目标**：确认 Prompt 设计无需大改后再进入正式开发。

### Milestone 1：Prompt 验证 + 数据结构
**周期：2-3 天**
- [ ] 手写 3-5 个真实 JD 和简历
- [ ] 用新 prompt 在 ChatGPT/Claude 上跑通，观察推断质量和 JSON 稳定性
- [ ] 定义 `MatchCriteria` 数据类
- [ ] 根据验证结果微调"常见误判提醒"和"推断授权"边界

### Milestone 2：后端解析逻辑 + 单元测试
**周期：2-3 天**
- [ ] 修改 `SYSTEM_PROMPT`（增加匹配标准 JSON 输出）
- [ ] 新增 `BATCH_MATCH_PROMPT`
- [ ] 改造 `batch_match_service.py` 的 `_parse_report` 和 `_compute_weighted_score`
- [ ] 跑单元测试验证解析逻辑（包括 JSON fallback 路径）

### Milestone 3：岗位分析结果持久化
**周期：1-2 天**
- [ ] `analysis_history` 表执行 `ALTER TABLE`
- [ ] 修改 `analysis_history_repository.py` 和 `HistoryRecord`
- [ ] 在 `main_window.py` 的岗位分析完成回调中解析并保存 `match_criteria_json`
- [ ] 验证 LLM 输出的 JSON 能被稳定解析（含多层 fallback）

### Milestone 4：匹配标准编辑器 UI
**周期：4-6 天（最大工作量）**
- [ ] 在 `job_analysis_widget.py` 的结果面板顶部嵌入 `MatchCriteriaEditor`
- [ ] 实现权重自动归一化、增删改、保存/重置
- [ ] 打通"保存标准 → 触发批量匹配"的数据流

### Milestone 5：集成测试与验收
**周期：2-3 天**
- [ ] 端到端测试：分析岗位 → 编辑标准 → 批量匹配 → 查看维度拆解
- [ ] 用 10-20 个真实候选人做效果验证
- [ ] 根据效果做最后微调

---

## 11. 验收标准

### 11.1 功能性验收
- [ ] 岗位分析结果页出现可编辑的"匹配标准"卡片
- [ ] 保存后的匹配标准能被批量匹配正确读取
- [ ] 批量匹配结果展示 4 个维度分 + 加权总分 + 推断依据
- [ ] 运行中的批量匹配任务不受中途修改标准的影响

### 11.2 效果验收（主观 + 案例）
- [ ] **不过杀**：做过电商后端但简历没写"微服务"的候选人，不再因关键词缺失被一票否决
- [ ] **不错杀**：4.5 年经验 vs 5 年要求，不再被 LLM 过度扣分
- [ ] **不瞎推**：明显缺少核心管理经验的候选人，核心能力维度分应低于 60
- [ ] **可解释**：任意一个候选人的总分，都能从 4 个维度分 + 权重公式反推出来

### 11.3 性能验收
- [ ] 60 个候选人的批量匹配总时间不超过当前版本的 1.1 倍（即不显著变慢）

---

## 12. 风险与回退方案

| 风险 | 概率 | 影响 | 回退方案 |
|------|------|------|----------|
| LLM JSON 输出不稳定 | 中 | 解析失败率高 | 已有 3 层 fallback（末尾裸 JSON → Markdown 代码块 → `<pre>` 标签）；若仍不稳定，改为强制要求 LLM 输出 `---JSON_START--- {...} ---JSON_END---` 固定分隔符文本 |
| 推断授权导致过度推断 | 中 | 给不匹配的人高分 | 收紧"推断禁区"描述；增加"每条推断必须基于简历原文中的具体句子"的约束 |
| 用户不想编辑匹配标准 | 低 | 新 UI 成摆设 | LLM 生成的默认标准可直接使用，编辑是可选增值功能 |
| 权重归一化逻辑出错 | 低 | 总分计算错误 | UI 中增加"当前权重和 = X%"的实时提示，保存时校验；后端计算时再次校验权重和是否为 100 |
| 旧 Prompt 被误替换 | 低 | 简历匹配页崩溃 | `BATCH_MATCH_PROMPT` 与 `RESUME_MATCH_PROMPT` 完全独立，单条匹配继续输出 HTML |
| 数据库迁移导致历史数据丢失 | 低 | 已有记录不可用 | `analysis_history` 用 `ALTER TABLE`；batch_match 数据走 `v2` 新表；迁移前自动备份 `.db` 文件 |

---

## 13. 已确认的设计决策

经讨论，以下 4 个关键问题已确认：

1. **推断边界**：**允许更宽松的合理推断**。候选人写"负责某金融系统的核心交易模块"，可以推断出"具备金融风控意识"。系统默认授权 LLM 基于通用职业知识做推断，但仍要求注明依据。
2. **默认权重**：**自动按比例重新分配**。当用户增删核心要求或调整某条权重时，UI 自动将剩余启用的核心要求权重归一化到 100%，无需用户手动调平。
3. **基础要求可升级**：**允许**。任何基础要求都可以通过勾选"升级为一票否决项"变为 dealbreaker。UI 中基础要求列表的每项右侧增加一个🔴图标按钮，点击后该项移动到"一票否决项"列表中。
4. **Mini-batch**：**目前不用**。保持 1 次 LLM 调用/候选人的设计，暂不做 batching 优化。

### 因确认而补充的设计细节

- **推断授权条款需写入 Prompt**：在批量匹配 prompt 的"推断规则"中明确写入"基于业务模块可推断该模块所需的通用能力，如负责金融核心交易模块可推断具备金融风控意识"。
- **权重自动归一化算法**：
  ```python
  def normalize_weights(raw_weights: list[int]) -> list[int]:
      total = sum(raw_weights)
      if total == 0:
          return raw_weights
      normalized = [round(w / total * 100) for w in raw_weights]
      # 处理四舍五入导致总和为 99 或 101 的情况
      diff = 100 - sum(normalized)
      if diff != 0:
          max_idx = normalized.index(max(normalized))
          normalized[max_idx] += diff
      return normalized
  ```
- **基础要求升级交互**：基础要求列表右侧增加"🔴 设为硬门槛"按钮，点击后从基础列表移除，自动追加到 dealbreakers 列表末尾，`enabled=true`。

---

**作者**：Kimi Code CLI  
**最后更新**：2026-04-11（v1.1 已结合代码评审修正）  
**状态**：设计确认完毕，等待进入 Milestone 0（最小可用闭环验证）  
**建议下一步动作**：先做 Milestone 0：手写一个 `MatchCriteria`，硬编码传给 `BatchMatchService`，用 5-10 份真实简历验证 Prompt 稳定性。
