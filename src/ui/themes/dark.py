"""暗色主题CSS - 营销页面风格"""

DARK_CSS = """
/* === 基础样式 === */
* {
    box-sizing: border-box;
}

body {
    font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif;
    font-size: 16px;
    color: #e0e0e0;
    background-color: #1a1a2e;
    line-height: 1.8;
    padding: 15px;
    margin: 0;
}

/* === 标题样式 === */
h1 {
    color: #ffffff;
    font-size: 28px;
    font-weight: 700;
    margin: 15px 0 12px 0;
    padding-bottom: 10px;
    border-bottom: 3px solid #667eea;
}

h2 {
    color: #ffffff;
    font-size: 22px;
    font-weight: 600;
    margin: 15px 0 10px 0;
    padding-bottom: 8px;
    border-bottom: 2px solid #3a3a5c;
}

h3 {
    color: #e0e0e0;
    font-size: 18px;
    font-weight: 600;
    margin: 12px 0 8px 0;
}

h4 {
    color: #b0b0b0;
    font-size: 16px;
    font-weight: 600;
    margin: 10px 0 6px 0;
}

/* === 渐变卡片 === */
.card {
    padding: 20px;
    border-radius: 12px;
    margin: 15px 0;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}

.card h1, .card h2, .card h3, .card h4 {
    color: inherit;
    border: none;
    padding: 0;
    margin: 0 0 10px 0;
}

.card-blue {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}

.card-green {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    color: white;
}

.card-orange {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    color: white;
}

.card-purple {
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    color: white;
}

.card-red {
    background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
    color: white;
}

.card-yellow {
    background: linear-gradient(135deg, #f7971e 0%, #ffd200 100%);
    color: white;
}

.card-gray {
    background: linear-gradient(135deg, #434343 0%, #000000 100%);
    color: white;
}

/* === 浅色卡片（暗色模式下为深色） === */
.card-light {
    background: #2d2d4a;
    border: 1px solid #3a3a5c;
    color: #e0e0e0;
}

.card-light-blue {
    background: linear-gradient(135deg, #2d3a5c 0%, #3a4a7a 100%);
    border: 1px solid #667eea;
    color: #e0e0e0;
}

.card-light-green {
    background: linear-gradient(135deg, #2d4a3a 0%, #3a5c4a 100%);
    border: 1px solid #11998e;
    color: #e0e0e0;
}

.card-light-orange {
    background: linear-gradient(135deg, #4a3a2d 0%, #5c4a3a 100%);
    border: 1px solid #f5576c;
    color: #e0e0e0;
}

/* === 进度条 === */
.progress-container {
    margin: 12px 0;
}

.progress-label {
    font-weight: 600;
    margin-bottom: 6px;
    color: #e0e0e0;
    display: flex;
    justify-content: space-between;
}

.progress-bar {
    height: 24px;
    background: #2d2d4a;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.3);
}

.progress-fill {
    height: 100%;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 600;
    font-size: 12px;
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
    transition: width 0.5s ease;
}

.progress-blue { background: linear-gradient(90deg, #667eea, #764ba2); }
.progress-green { background: linear-gradient(90deg, #11998e, #38ef7d); }
.progress-orange { background: linear-gradient(90deg, #f093fb, #f5576c); }
.progress-purple { background: linear-gradient(90deg, #4facfe, #00f2fe); }
.progress-red { background: linear-gradient(90deg, #ff416c, #ff4b2b); }
.progress-yellow { background: linear-gradient(90deg, #f7971e, #ffd200); }

/* === 评分条 === */
.rating {
    display: flex;
    align-items: center;
    margin: 10px 0;
    gap: 12px;
}

.rating-label {
    font-weight: 600;
    min-width: 100px;
    color: #e0e0e0;
}

.rating-bar {
    flex: 1;
    height: 16px;
    background: #2d2d4a;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.3);
}

.rating-fill {
    height: 100%;
    background: linear-gradient(90deg, #667eea, #764ba2);
    border-radius: 8px;
}

.rating-value {
    font-weight: 700;
    color: #8ab4f8;
    min-width: 50px;
    text-align: right;
    font-size: 16px;
}

/* === 特性卡片网格 === */
.feature-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 15px;
    margin: 15px 0;
}

.feature-card {
    background: #2d2d4a;
    border: 1px solid #3a3a5c;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}

.feature-icon {
    font-size: 36px;
    margin-bottom: 10px;
}

.feature-title {
    font-weight: 600;
    font-size: 15px;
    margin-bottom: 5px;
    color: #e0e0e0;
}

.feature-desc {
    color: #a0a0a0;
    font-size: 13px;
}

/* === 提示框 === */
.alert {
    padding: 15px 20px;
    border-radius: 10px;
    margin: 15px 0;
    border-left: 4px solid;
}

.alert-success {
    background: linear-gradient(135deg, #1e3a2d 0%, #2d4a3a 100%);
    border-color: #38ef7d;
    color: #a0d8a8;
}

.alert-warning {
    background: linear-gradient(135deg, #3a3a1e 0%, #4a4a2d 100%);
    border-color: #ffc107;
    color: #e0d0a0;
}

.alert-info {
    background: linear-gradient(135deg, #1e2a3a 0%, #2d3a4a 100%);
    border-color: #17a2b8;
    color: #a0c8d0;
}

.alert-danger {
    background: linear-gradient(135deg, #3a1e2a 0%, #4a2d3a 100%);
    border-color: #ff4b2b;
    color: #d8a0a8;
}

.alert-primary {
    background: linear-gradient(135deg, #1e2a4a 0%, #2d3a5a 100%);
    border-color: #667eea;
    color: #a0b0d8;
}

/* === 标签云 === */
.tag-cloud {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 12px 0;
}

.tag {
    display: inline-block;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 500;
}

.tag-blue { background: #2d3a5c; color: #8ab4f8; border: 1px solid #667eea; }
.tag-green { background: #2d4a3a; color: #80d8a0; border: 1px solid #38ef7d; }
.tag-orange { background: #4a3a2d; color: #f8c080; border: 1px solid #f5576c; }
.tag-purple { background: #3a2d4a; color: #c8a0d8; border: 1px solid #7b1fa2; }
.tag-red { background: #4a2d2d; color: #f8a0a0; border: 1px solid #ff4b2b; }
.tag-teal { background: #2d4a4a; color: #80d8d0; border: 1px solid #38ef7d; }
.tag-indigo { background: #2d2d4a; color: #a0a0d8; border: 1px solid #667eea; }
.tag-pink { background: #4a2d3a; color: #f8a0c0; border: 1px solid #f093fb; }

/* === 精美表格 === */
table {
    border-collapse: collapse;
    width: 100%;
    margin: 15px 0;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 2px 10px rgba(0,0,0,0.3);
}

th {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    font-weight: 600;
    padding: 14px 16px;
    text-align: left;
}

td {
    padding: 12px 16px;
    border-bottom: 1px solid #3a3a5c;
}

tr:nth-child(even) {
    background: #2d2d4a;
}

tr:last-child td {
    border-bottom: none;
}

/* === 列表样式 === */
ul, ol {
    padding-left: 25px;
    margin: 10px 0;
}

li {
    margin: 6px 0;
}

/* === 代码块 === */
code {
    background: #2d2d4a;
    padding: 2px 8px;
    border-radius: 4px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 13px;
    color: #f472b6;
}

pre {
    background: #0d0d1a;
    color: #d4d4d4;
    padding: 16px;
    border-radius: 10px;
    overflow-x: auto;
    margin: 15px 0;
    box-shadow: 0 4px 15px rgba(0,0,0,0.4);
}

pre code {
    background: transparent;
    color: #d4d4d4;
    padding: 0;
}

/* === 引用块 === */
blockquote {
    border-left: 4px solid #667eea;
    margin: 15px 0;
    padding: 12px 20px;
    background: linear-gradient(135deg, #2d2d4a 0%, #3a3a5c 100%);
    border-radius: 0 10px 10px 0;
    color: #b0b0b0;
}

/* === 强调文本 === */
strong, b {
    color: #ffffff;
    font-weight: 600;
}

em, i {
    font-style: italic;
}

/* === 链接 === */
a {
    color: #8ab4f8;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

/* === 分隔线 === */
hr {
    border: none;
    height: 2px;
    background: linear-gradient(90deg, #667eea, #764ba2, #f5576c);
    margin: 25px 0;
    border-radius: 1px;
}

/* === 信息卡片 === */
.info-card {
    display: flex;
    align-items: flex-start;
    gap: 15px;
    padding: 18px;
    background: #2d2d4a;
    border-radius: 12px;
    margin: 15px 0;
    border: 1px solid #3a3a5c;
}

.info-card-icon {
    font-size: 28px;
    flex-shrink: 0;
}

.info-card-content {
    flex: 1;
}

.info-card-title {
    font-weight: 600;
    font-size: 15px;
    margin-bottom: 5px;
    color: #e0e0e0;
}

.info-card-desc {
    color: #a0a0a0;
    font-size: 13px;
}

/* === 按钮样式 === */
.btn {
    display: inline-block;
    padding: 10px 20px;
    border-radius: 8px;
    font-weight: 600;
    text-align: center;
    cursor: pointer;
    text-decoration: none;
}

.btn-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}

.btn-success {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    color: white;
}

.btn-warning {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    color: white;
}

/* === 统计数字 === */
.stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 15px;
    margin: 15px 0;
}

.stat-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px;
    border-radius: 12px;
    text-align: center;
}

.stat-value {
    font-size: 28px;
    font-weight: 700;
}

.stat-label {
    font-size: 13px;
    opacity: 0.9;
    margin-top: 5px;
}

/* === 步骤条 === */
.steps {
    margin: 20px 0;
}

.step {
    display: flex;
    align-items: flex-start;
    margin-bottom: 15px;
}

.step-number {
    width: 32px;
    height: 32px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
}

.step-desc {
    color: #a0a0a0;
    font-size: 13px;
}
"""
