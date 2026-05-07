# 工作流 API 与多轮 Agent 集成改造计划

## 1. 背景与目标

当前项目已经具备完整的猎头工作台能力：公司调研、岗位分析、匹配条件生成、搜索策略生成、猎聘浏览器自动化、候选人 Excel 入库、批量匹配、打招呼文本生成与自动打招呼。

但当前主流程主要由桌面 UI 固定编排，属于“单轮弱智能”：一次生成分析、一次生成搜索策略、按固定轮次执行。它缺少一个可以被外部多轮 Agent 调用的稳定执行接口，因此难以支持“观察结果 -> 调整策略 -> 再执行 -> 再判断”的循环决策。

本计划目标是把现有项目改造成：

1. 保留桌面工作台作为人工控制台。
2. 新增本地工作流 API 服务，暴露稳定的工具能力。
3. 支持类似 ComfyUI 的 JSON 工作流描述，但先做轻量版。
4. 允许外部多轮 Agent 调用本项目的工具接口，负责策略推理、反思和迭代。
5. 将本项目定位为“猎聘工作流执行后端 + 桌面控制台”，外部 Agent 作为“多轮决策大脑”。

## 2. 设计原则

1. 不推倒重写，优先复用 `src/core` 里的服务。
2. 不把外部 Agent 直接耦合到 UI 控件。
3. 浏览器自动化任务必须串行，避免多个调用抢同一个 Playwright 会话。
4. 所有长任务走任务队列，API 返回 `job_id`，调用方轮询状态。
5. 配置密钥只存在本机 `config.json`，API 不返回真实密钥。
6. 自动打招呼、登录、批量抓取前保留人类确认机制。
7. 先做稳定的工具 API，再做完整 DAG 工作流。

## 3. 目标架构

```text
外部多轮 Agent
    |
    | HTTP / JSON-RPC / MCP 工具调用
    v
Workflow API Server
    |
    +-- ToolRegistry
    +-- WorkflowRunner
    +-- JobManager
    +-- ArtifactStore
    +-- BrowserSessionService
    |
    v
现有 core 服务
    |
    +-- LLMClient
    +-- MatchCriteriaService
    +-- SearchStrategyGenerationService
    +-- LiepinBrowserManager
    +-- LiepinSearchTaskService
    +-- CandidateExcelService
    +-- BatchMatchService
    +-- AutoGreetingService
```

桌面 UI 后续也可以逐步改为调用同一套服务层，而不是直接承担编排逻辑。

## 4. 第一阶段：工具 API

第一阶段不做复杂 DAG，只暴露一组稳定工具接口，让外部 Agent 可以单步调用。

### 4.1 建议接口

#### `GET /api/health`

返回服务状态、版本、浏览器状态摘要。

#### `POST /api/tools/analyze_jd`

输入：

```json
{
  "jd_text": "...",
  "company_context": ""
}
```

输出：

```json
{
  "record_id": "20260508_120000_123",
  "title": "高级产品经理",
  "analysis_html": "..."
}
```

#### `POST /api/tools/generate_match_criteria`

输入：

```json
{
  "record_id": "..."
}
```

输出：

```json
{
  "record_id": "...",
  "match_criteria": {}
}
```

#### `POST /api/tools/generate_search_strategy`

输入：

```json
{
  "record_id": "...",
  "override_prompt_hint": ""
}
```

输出：

```json
{
  "record_id": "...",
  "strategy": {
    "executable_rounds": [],
    "filters": {}
  }
}
```

#### `POST /api/tools/run_liepin_capture`

输入：

```json
{
  "record_id": "...",
  "strategy": {},
  "filters": {},
  "max_pages": 1,
  "max_candidates": 30,
  "per_round_limit": 30
}
```

输出：

```json
{
  "job_id": "browser-task-id"
}
```

该接口必须异步执行。调用方通过任务查询接口拿结果。

#### `POST /api/tools/batch_match_candidates`

输入：

```json
{
  "record_id": "...",
  "excel_path": "...",
  "row_indexes": [],
  "max_workers": 5
}
```

输出：

```json
{
  "job_id": "compute-task-id"
}
```

#### `POST /api/tools/generate_greeting_text`

输入：

```json
{
  "record_id": "...",
  "style": "general"
}
```

输出：

```json
{
  "text": "您好，我是猎头顾问..."
}
```

#### `GET /api/jobs/{job_id}`

输出：

```json
{
  "job_id": "...",
  "status": "running",
  "progress_current": 3,
  "progress_total": 30,
  "message": "正在处理候选人",
  "result": {},
  "error": ""
}
```

## 5. 第二阶段：轻量工作流 API

第二阶段增加 JSON 工作流执行能力。先支持步骤列表，不急着做可视化节点编辑器。

### 5.1 工作流格式

```json
{
  "name": "岗位寻访基础流程",
  "inputs": {
    "jd_text": "...",
    "company_context": ""
  },
  "steps": [
    {
      "id": "analysis",
      "tool": "analyze_jd",
      "inputs": {
        "jd_text": "$inputs.jd_text",
        "company_context": "$inputs.company_context"
      }
    },
    {
      "id": "criteria",
      "tool": "generate_match_criteria",
      "inputs": {
        "record_id": "$steps.analysis.record_id"
      }
    },
    {
      "id": "strategy",
      "tool": "generate_search_strategy",
      "inputs": {
        "record_id": "$steps.analysis.record_id"
      }
    },
    {
      "id": "capture",
      "tool": "run_liepin_capture",
      "inputs": {
        "record_id": "$steps.analysis.record_id",
        "strategy": "$steps.strategy.strategy",
        "max_pages": 1,
        "max_candidates": 30
      }
    }
  ]
}
```

### 5.2 执行语义

1. 每个 step 的输出写入上下文。
2. 支持 `$inputs.xxx` 和 `$steps.step_id.xxx` 引用。
3. 遇到异步任务时，默认等待任务完成，也可以配置为只提交任务。
4. 失败时返回失败节点、错误信息、已完成节点输出。
5. 暂不支持并行节点，避免浏览器任务并发复杂度。

## 6. 第三阶段：Agent 闭环增强

当外部 Agent 可以调用工具后，真正价值在多轮闭环。

### 6.1 搜索策略迭代

外部 Agent 可以执行：

```text
生成初始搜索策略
执行第 1 轮搜索
读取轮次统计：原始候选人数、去重数、抓取成功率、A/B 档比例
判断关键词过窄或过泛
修改 query / position_filter / 城市 / 活跃度
继续执行下一轮
```

### 6.2 样本驱动优化

可以先抓 10-20 个候选人做小样本批量匹配，再根据 A/B 比例决定是否扩池。

建议给 Agent 暴露这些观察指标：

1. 每轮 query。
2. 搜索页数。
3. 原始候选人数。
4. 去重后候选人数。
5. 完整简历抓取数。
6. 抓取失败数。
7. A/B/C/D 档分布。
8. 常见命中词和常见误杀原因。

### 6.3 人类确认点

以下动作建议默认需要人工确认：

1. 首次打开猎聘浏览器并登录。
2. 自动抓取开始前。
3. 自动打招呼开始前。
4. 单次打招呼数量超过阈值。
5. Agent 想放宽到“全国/不限活跃度”等大范围搜索时。

## 7. 推荐新增模块

```text
src/
  api/
    __init__.py
    app.py
    schemas.py
    tool_routes.py
    job_routes.py
    workflow_routes.py

  workflow/
    __init__.py
    tool_registry.py
    workflow_runner.py
    job_manager.py
    artifact_store.py
    context_resolver.py

  core/
    workflow_facade.py
```

### 7.1 `workflow_facade.py`

封装现有服务，提供非 UI 的业务入口。它是 API 和桌面 UI 共享的薄门面。

### 7.2 `tool_registry.py`

负责注册工具名到 Python callable 的映射。

### 7.3 `job_manager.py`

管理长任务状态。可以先复用现有 `TaskQueue`，后续再抽象为 UI 无关版本。

### 7.4 `artifact_store.py`

统一保存中间产物：

1. LLM 原始输出。
2. 搜索策略 JSON。
3. Excel 路径。
4. debug snapshot 路径。
5. 批量匹配结果摘要。

## 8. 数据存储演进

短期继续使用现有 SQLite + Excel。

中期建议将候选人和匹配结果更多落到 SQLite：

1. Excel 作为导出物，而不是唯一候选人数据库。
2. 每次搜索轮次、候选人来源、匹配结果都可被 API 查询。
3. 外部 Agent 不必解析 Excel，就能读取结构化结果。

建议新增或完善：

1. `candidates`
2. `candidate_sources`
3. `candidate_match_results`
4. `workflow_runs`
5. `workflow_step_runs`
6. `artifacts`

## 9. 安全与边界

1. API 默认只监听 `127.0.0.1`。
2. 默认不开放公网。
3. 可选配置本地 token，例如 `WORKFLOW_API_TOKEN`。
4. API 不返回 API Key、Tavily Key、浏览器 profile 路径细节。
5. 对自动打招呼接口做数量上限和确认机制。
6. 对文件路径参数做白名单限制，优先限制在项目目录和 `exports/` 目录。

## 10. 实施路线

### Phase 1：抽出非 UI 门面

目标：让核心流程不依赖 `MainWindow`。

任务：

1. 新增 `WorkflowFacade`。
2. 封装 LLM 配置读取。
3. 封装岗位分析、匹配条件生成、搜索策略生成。
4. 封装候选人抓取任务创建。
5. 封装批量匹配任务创建。
6. 保持现有 UI 逻辑不动，只新增 API 可用入口。

验收：

1. 单元测试可直接调用 `WorkflowFacade`。
2. 不启动 GUI 也能完成分析、策略生成等纯后端动作。

### Phase 2：FastAPI 本地服务

目标：外部 Agent 可以通过 HTTP 调用工具。

任务：

1. 新增 `src/api/app.py`。
2. 新增 `schemas.py` 定义请求/响应模型。
3. 实现 `/api/health`。
4. 实现核心工具接口。
5. 实现任务查询接口。
6. 新增启动命令，例如 `python -m src.api.app`。

验收：

1. `curl` 可以调用岗位分析。
2. `curl` 可以提交抓取任务并查询状态。
3. 不影响 `main.py` 桌面启动。

### Phase 3：工作流 Runner

目标：支持轻量 JSON 工作流。

任务：

1. 新增 `WorkflowRunner`。
2. 新增上下文引用解析。
3. 支持步骤串行执行。
4. 支持失败恢复信息。
5. 实现 `/api/workflows/run`。
6. 保存每次 workflow run 的步骤结果。

验收：

1. 提交一份工作流 JSON 能自动跑完分析、匹配条件、搜索策略。
2. 浏览器抓取步骤可异步执行并返回任务状态。

### Phase 4：Agent 观察接口

目标：让外部 Agent 能根据结果调整策略。

任务：

1. 暴露搜索轮次统计查询。
2. 暴露候选人摘要查询。
3. 暴露匹配结果分布查询。
4. 暴露 debug snapshot 路径和失败原因。
5. 支持按上一轮结果创建下一轮搜索策略。

验收：

1. 外部 Agent 可以读取 A/B/C/D 分布。
2. 外部 Agent 可以基于统计结果提交下一轮搜索。

## 11. 风险与应对

### 风险 1：浏览器任务并发冲突

应对：所有浏览器任务走单独队列，严格串行。

### 风险 2：API 与 GUI 同时操作状态不一致

应对：先让 API 和 GUI 共享 `WorkflowFacade` 与任务队列；状态集中在 `JobManager`。

### 风险 3：外部 Agent 放宽条件导致误抓太多

应对：对 `max_candidates`、`max_pages`、活跃度、城市范围设置默认上限。

### 风险 4：Excel 不适合 Agent 读取

应对：短期返回 Excel 路径和摘要；中期把候选人结构化落 SQLite。

### 风险 5：自动打招呼误触

应对：打招呼接口默认只创建待确认任务，不直接发送；UI 或人工确认后才执行。

## 12. 推荐优先级

最高优先级：

1. `WorkflowFacade`
2. `FastAPI` 本地服务
3. `job_id` 异步任务查询
4. 搜索策略生成与抓取任务 API

第二优先级：

1. 工作流 JSON Runner
2. 搜索结果统计查询
3. 批量匹配结果结构化查询

第三优先级：

1. SQLite 候选人库增强
2. 桌面 UI 改为调用统一 facade
3. 可视化工作流编辑器

## 13. 最小可行版本

MVP 不需要完整 ComfyUI 式节点系统，只需要：

1. 启动本地 API 服务。
2. 外部 Agent 能调用：
   - `analyze_jd`
   - `generate_search_strategy`
   - `run_liepin_capture`
   - `get_job_status`
   - `batch_match_candidates`
3. 每个接口返回结构化 JSON。
4. 浏览器抓取和批量匹配支持异步任务。

完成 MVP 后，外部 Agent 就能开始做真正的多轮搜索策略优化。
