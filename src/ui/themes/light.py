"""亮色主题CSS - 现代专业风格"""

LIGHT_CSS = """
/* === 基础样式 === */
* {
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', 'PingFang SC', Roboto, 'Helvetica Neue', Arial, sans-serif;
    font-size: 20px;
    color: #334155;
    background-color: #ffffff;
    line-height: 1.6;
    padding: 24px;
    margin: 0;
}

/* === 段落样式 === */
p {
    color: #334155;
    margin: 12px 0 16px 0;
}

/* === 标题样式 === */
h1, h2, h3, h4, h5, h6 {
    color: #0f172a;
    font-weight: 600;
    line-height: 1.3;
}

h1 {
    font-size: 32px;
    margin: 24px 0 16px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #e2e8f0;
}

h2 {
    font-size: 28px;
    margin: 20px 0 12px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid #f1f5f9;
}

h3 {
    font-size: 24px;
    margin: 16px 0 8px 0;
}

h4 {
    font-size: 20px;
    margin: 16px 0 8px 0;
}

/* === 渐变卡片 (降级为简约纯色/微阴影以提升专业感) === */
.card {
    padding: 20px;
    border-radius: 8px;
    margin: 16px 0;
    border: 1px solid #e2e8f0;
    background-color: #ffffff;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.card h1, .card h2, .card h3, .card h4 {
    border: none;
    padding: 0;
    margin: 0 0 12px 0;
}

/* === 保留原有的辅助色类名，但改为柔和纯色设计 === */
.card-blue { background-color: #eff6ff; border-color: #bfdbfe; color: #1e3a8a; }
.card-green { background-color: #f0fdf4; border-color: #bbf7d0; color: #14532d; }
.card-orange { background-color: #fff7ed; border-color: #fed7aa; color: #7c2d12; }
.card-purple { background-color: #faf5ff; border-color: #e9d5ff; color: #581c87; }
.card-red { background-color: #fef2f2; border-color: #fecaca; color: #7f1d1d; }
.card-yellow { background-color: #fefce8; border-color: #fef08a; color: #713f12; }
.card-gray { background-color: #f8fafc; border-color: #e2e8f0; color: #334155; }

/* 浅色卡片保持统一视觉 */
.card-light, .card-light-blue, .card-light-green, .card-light-orange {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    color: #334155;
}

/* === 进度条 === */
.progress-container {
    margin: 16px 0;
}

.progress-label {
    font-weight: 600;
    margin-bottom: 8px;
    color: #334155;
    display: flex;
    justify-content: space-between;
    font-size: 15px;
}

.progress-bar {
    height: 24px;
    background: #e2e8f0;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);
}

.progress-fill {
    height: 100%;
    border-radius: 12px;
    background-color: #3b82f6; /* 主题蓝 */
    transition: width 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 600;
    font-size: 13px;
    text-shadow: 0 1px 1px rgba(0,0,0,0.1);
}

/* 添加进度条颜色变体 */
.progress-blue { background-color: #3b82f6; }
.progress-green { background-color: #10b981; }
.progress-orange { background-color: #f59e0b; }
.progress-purple { background-color: #8b5cf6; }
.progress-red { background-color: #ef4444; }

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
    color: #475569;
    font-size: 14px;
}

.rating-bar {
    flex: 1;
    height: 8px;
    background: #f1f5f9;
    border-radius: 4px;
    overflow: hidden;
}

.rating-fill {
    height: 100%;
    background-color: #10b981; /* 主题绿 */
    border-radius: 4px;
}

.rating-value {
    font-weight: 600;
    color: #0f172a;
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

.alert-success { background-color: #f0fdf4; border-left-color: #22c55e; color: #15803d; }
.alert-warning { background-color: #fffbeb; border-left-color: #f59e0b; color: #b45309; }
.alert-info { background-color: #eff6ff; border-left-color: #3b82f6; color: #1d4ed8; }
.alert-danger { background-color: #fef2f2; border-left-color: #ef4444; color: #b91c1c; }
.alert-primary { background-color: #f8fafc; border-left-color: #64748b; color: #334155; }

/* === 特性卡片网格 === */
.feature-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin: 16px 0;
}

.feature-card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
    transition: transform 0.2s, box-shadow 0.2s;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.feature-icon {
    font-size: 32px;
    margin-bottom: 12px;
    color: #3b82f6;
}

.feature-title {
    font-weight: 600;
    font-size: 15px;
    margin-bottom: 6px;
    color: #0f172a;
}

.feature-desc {
    color: #475569;
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
    background-color: #f1f5f9;
    color: #475569;
    border: 1px solid #e2e8f0;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.2s ease;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.tag:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    filter: brightness(0.95);
    text-decoration: none;
}

.tag:active {
    transform: translateY(0);
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.tag-blue { background-color: #eff6ff; color: #1d4ed8; border-color: #bfdbfe; }
.tag-green { background-color: #f0fdf4; color: #15803d; border-color: #bbf7d0; }
.tag-orange { background-color: #fff7ed; color: #c2410c; border-color: #fed7aa; }
.tag-purple { background-color: #faf5ff; color: #6b21a8; border-color: #e9d5ff; }
.tag-red { background-color: #fef2f2; color: #b91c1c; border-color: #fecaca; }

/* === 精美表格 === */
table {
    border-collapse: collapse;
    width: 100%;
    margin: 16px 0;
    font-size: 14px;
}

th, td {
    padding: 10px 14px;
    border: 1px solid #e2e8f0;
    text-align: left;
}

th {
    background-color: #f8fafc;
    color: #0f172a;
    font-weight: 600;
}

tr:nth-child(even) {
    background-color: #f8fafc;
}

tr:hover {
    background-color: #f1f5f9;
}

/* === 列表样式 === */
ul, ol {
    padding-left: 24px;
    margin: 12px 0 16px 0;
}

li {
    margin: 6px 0;
    color: #334155;
}

/* === 强调文本 === */
strong, b {
    color: #0f172a;
    font-weight: 600;
}

em, i {
    font-style: italic;
    color: #475569;
}

/* === 代码块 === */
code {
    background-color: #f1f5f9;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 13px;
    color: #db2777;
}

pre {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    padding: 16px;
    border-radius: 6px;
    overflow-x: auto;
    margin: 16px 0;
}

pre code {
    background-color: transparent;
    color: #334155;
    padding: 0;
    font-size: 13px;
}

/* === 引用块 === */
blockquote {
    border-left: 4px solid #cbd5e1;
    margin: 16px 0;
    padding: 8px 16px;
    background-color: #f8fafc;
    border-radius: 0 6px 6px 0;
    color: #475569;
}

/* === 链接 === */
a {
    color: #2563eb;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

/* === 分隔线 === */
hr {
    border: none;
    height: 1px;
    background-color: #e2e8f0;
    margin: 24px 0;
}

/* === 信息卡片 === */
.info-card {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 16px;
    background-color: #f8fafc;
    border-radius: 8px;
    margin: 16px 0;
    border: 1px solid #e2e8f0;
}

.info-card-icon {
    font-size: 24px;
    flex-shrink: 0;
    color: #3b82f6;
}

.info-card-content {
    flex: 1;
}

.info-card-title {
    font-weight: 600;
    font-size: 15px;
    margin-bottom: 4px;
    color: #0f172a;
}

.info-card-desc {
    color: #475569;
    font-size: 14px;
    margin: 0;
}

/* === 按钮样式 === */
.btn {
    display: inline-block;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: 500;
    font-size: 14px;
    text-align: center;
    cursor: pointer;
    text-decoration: none;
    border: 1px solid transparent;
}

.btn-primary { background-color: #3b82f6; color: white; }
.btn-primary:hover { background-color: #2563eb; }
.btn-success { background-color: #10b981; color: white; }
.btn-warning { background-color: #f59e0b; color: white; }

/* === 统计数字 === */
.stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 16px;
    margin: 16px 0;
}

.stat-card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    padding: 16px;
    border-radius: 8px;
    text-align: center;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.stat-value {
    font-size: 24px;
    font-weight: 700;
    color: #0f172a;
}

.stat-label {
    font-size: 13px;
    color: #64748b;
    margin-top: 4px;
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
    width: 28px;
    height: 28px;
    background-color: #f1f5f9;
    color: #3b82f6;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 14px;
    margin-right: 12px;
    flex-shrink: 0;
    border: 1px solid #e2e8f0;
}

.step-content {
    flex: 1;
    padding-top: 2px;
}

.step-title {
    font-weight: 600;
    margin-bottom: 4px;
    color: #0f172a;
    font-size: 15px;
}

.step-desc {
    color: #475569;
    font-size: 14px;
    margin: 0;
}
"""
