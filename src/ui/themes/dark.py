"""暗色主题CSS - 专业工具风格。"""

DARK_CSS = """
/* === 基础样式 === */
* {
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', 'PingFang SC', Roboto, 'Helvetica Neue', Arial, sans-serif;
    font-size: 20px;
    color: #cbd5e1;
    background-color: #0f172a;
    line-height: 1.6;
    padding: 24px;
    margin: 0;
}

/* === 段落样式 === */
p {
    color: #cbd5e1;
    margin: 12px 0 16px 0;
}

/* === 标题样式 === */
h1, h2, h3, h4, h5, h6 {
    color: #f8fafc;
    font-weight: 600;
    line-height: 1.3;
}

h1 {
    font-size: 32px;
    margin: 24px 0 16px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #334155;
}

h2 {
    font-size: 28px;
    margin: 20px 0 12px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid #1e293b;
}

h3 {
    font-size: 24px;
    margin: 16px 0 8px 0;
}

h4 {
    font-size: 20px;
    margin: 16px 0 8px 0;
}

/* === 卡片 === */
.card {
    padding: 20px;
    border-radius: 8px;
    margin: 16px 0;
    border: 1px solid #334155;
    background-color: #111827;
    box-shadow: 0 2px 8px rgba(0,0,0,0.22);
}

.card h1, .card h2, .card h3, .card h4 {
    border: none;
    padding: 0;
    margin: 0 0 12px 0;
    color: inherit;
}

.card-blue { background-color: #172554; border-color: #1d4ed8; color: #dbeafe; }
.card-green { background-color: #052e16; border-color: #16a34a; color: #dcfce7; }
.card-orange { background-color: #431407; border-color: #ea580c; color: #ffedd5; }
.card-purple { background-color: #3b0764; border-color: #9333ea; color: #f3e8ff; }
.card-red { background-color: #450a0a; border-color: #dc2626; color: #fee2e2; }
.card-yellow { background-color: #422006; border-color: #ca8a04; color: #fef9c3; }
.card-gray { background-color: #111827; border-color: #334155; color: #cbd5e1; }

.card-light, .card-light-blue, .card-light-green, .card-light-orange {
    background-color: #0f172a;
    border: 1px solid #334155;
    color: #cbd5e1;
}

/* === 进度条 === */
.progress-container {
    margin: 16px 0;
}

.progress-label {
    font-weight: 600;
    margin-bottom: 8px;
    color: #e2e8f0;
    display: flex;
    justify-content: space-between;
    font-size: 15px;
}

.progress-bar {
    height: 24px;
    background: #1e293b;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.35);
}

.progress-fill {
    height: 100%;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 600;
    font-size: 13px;
    text-shadow: 0 1px 1px rgba(0,0,0,0.25);
    transition: width 0.3s ease;
}

.progress-blue { background-color: #2563eb; }
.progress-green { background-color: #16a34a; }
.progress-orange { background-color: #ea580c; }
.progress-purple { background-color: #9333ea; }
.progress-red { background-color: #dc2626; }

/* === 评分条 === */
.rating {
    display: flex;
    align-items: center;
    margin: 10px 0;
    gap: 12px;
}

.rating-label {
    font-weight: 500;
    min-width: 90px;
    color: #94a3b8;
    font-size: 14px;
}

.rating-bar {
    flex: 1;
    height: 8px;
    background: #1e293b;
    border-radius: 4px;
    overflow: hidden;
}

.rating-fill {
    height: 100%;
    background-color: #22c55e;
    border-radius: 4px;
}

.rating-value {
    font-weight: 600;
    color: #f8fafc;
    min-width: 40px;
    text-align: right;
    font-size: 14px;
}

/* === 提示框 === */
.alert {
    padding: 12px 16px;
    border-radius: 6px;
    margin: 16px 0;
    border-left: 4px solid;
    font-size: 14px;
}

.alert-success { background-color: #052e16; border-left-color: #22c55e; color: #bbf7d0; }
.alert-warning { background-color: #451a03; border-left-color: #f59e0b; color: #fde68a; }
.alert-info { background-color: #172554; border-left-color: #3b82f6; color: #bfdbfe; }
.alert-danger { background-color: #450a0a; border-left-color: #ef4444; color: #fecaca; }
.alert-primary { background-color: #111827; border-left-color: #64748b; color: #cbd5e1; }

/* === 特性卡片网格 === */
.feature-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin: 16px 0;
}

.feature-card {
    background-color: #111827;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 1px 2px rgba(0,0,0,0.2);
}

.feature-icon {
    font-size: 32px;
    margin-bottom: 12px;
    color: #60a5fa;
}

.feature-title {
    font-weight: 600;
    font-size: 15px;
    margin-bottom: 6px;
    color: #f8fafc;
}

.feature-desc {
    color: #94a3b8;
    font-size: 14px;
}

/* === 标签云 === */
.tag-cloud {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin: 12px 0;
}

.tag {
    display: inline-flex;
    align-items: center;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 15px;
    font-weight: 500;
    background-color: #1e293b;
    color: #cbd5e1;
    border: 1px solid #334155;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.2s ease;
    box-shadow: 0 1px 2px rgba(0,0,0,0.2);
}

.tag:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    filter: brightness(1.05);
    text-decoration: none;
}

.tag:active {
    transform: translateY(0);
    box-shadow: 0 1px 2px rgba(0,0,0,0.2);
}

.tag-blue { background-color: #172554; color: #bfdbfe; border-color: #1d4ed8; }
.tag-green { background-color: #052e16; color: #bbf7d0; border-color: #16a34a; }
.tag-orange { background-color: #431407; color: #fdba74; border-color: #ea580c; }
.tag-purple { background-color: #3b0764; color: #e9d5ff; border-color: #9333ea; }
.tag-red { background-color: #450a0a; color: #fecaca; border-color: #dc2626; }

/* === 表格 === */
table {
    border-collapse: collapse;
    width: 100%;
    margin: 16px 0;
    font-size: 14px;
}

th, td {
    padding: 10px 14px;
    border: 1px solid #334155;
    text-align: left;
}

th {
    background-color: #111827;
    color: #f8fafc;
    font-weight: 600;
}

tr:nth-child(even) {
    background-color: #0f172a;
}

tr:hover {
    background-color: #1e293b;
}

/* === 列表样式 === */
ul, ol {
    padding-left: 24px;
    margin: 12px 0 16px 0;
}

li {
    margin: 6px 0;
    color: #cbd5e1;
}

/* === 强调文本 === */
strong, b {
    color: #f8fafc;
    font-weight: 600;
}

em, i {
    font-style: italic;
    color: #94a3b8;
}

/* === 代码块 === */
code {
    background-color: #111827;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
    font-size: 13px;
    color: #f472b6;
}

pre {
    background-color: #020617;
    border: 1px solid #334155;
    padding: 16px;
    border-radius: 6px;
    overflow-x: auto;
    margin: 16px 0;
}

pre code {
    background-color: transparent;
    color: #cbd5e1;
    padding: 0;
    font-size: 13px;
}

/* === 引用块 === */
blockquote {
    border-left: 4px solid #475569;
    margin: 16px 0;
    padding: 12px 16px;
    background-color: #111827;
    color: #94a3b8;
}

/* === 链接 === */
a {
    color: #93c5fd;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

/* === 分隔线 === */
hr {
    border: none;
    border-top: 1px solid #334155;
    margin: 20px 0;
}

/* === 步骤条 === */
.steps {
    margin: 20px 0;
}

.step {
    display: flex;
    align-items: flex-start;
    margin-bottom: 16px;
}

.step-number {
    width: 32px;
    height: 32px;
    background-color: #2563eb;
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    margin-right: 15px;
    flex-shrink: 0;
}

.step-content {
    flex: 1;
    padding-top: 5px;
}

.step-title {
    font-weight: 600;
    margin-bottom: 3px;
    color: #f8fafc;
}

.step-desc {
    color: #94a3b8;
    font-size: 13px;
}
"""
