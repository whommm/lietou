"""亮色主题CSS - 营销页面风格"""

LIGHT_CSS = """
/* === 基础样式 === */
* {
    box-sizing: border-box;
}

body {
    font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif;
    font-size: 18px;
    color: #1a1a2e;
    background-color: #ffffff;
    line-height: 1.9;
    padding: 15px;
    margin: 0;
}

/* === 段落样式 === */
p {
    color: #1a1a2e;
    margin: 10px 0;
}

/* === 标题样式 === */
h1 {
    color: #1a1a2e;
    font-size: 30px;
    font-weight: 700;
    margin: 15px 0 12px 0;
    padding-bottom: 10px;
    border-bottom: 3px solid #667eea;
}

h2 {
    color: #2d3748;
    font-size: 24px;
    font-weight: 700;
    margin: 15px 0 10px 0;
    padding-bottom: 8px;
    border-bottom: 2px solid #e0e0e0;
}

h3 {
    color: #2d3748;
    font-size: 20px;
    font-weight: 600;
    margin: 12px 0 8px 0;
}

h4 {
    color: #4a5568;
    font-size: 18px;
    font-weight: 600;
    margin: 10px 0 6px 0;
}

/* === 渐变卡片 === */
.card {
    padding: 20px;
    border-radius: 12px;
    margin: 15px 0;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
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
    background: linear-gradient(135deg, #bdc3c7 0%, #2c3e50 100%);
    color: white;
}

/* === 浅色卡片（带边框） === */
.card-light {
    background: #f8f9fa;
    border: 1px solid #e0e0e0;
    color: #333;
}

.card-light-blue {
    background: linear-gradient(135deg, #e8f0fe 0%, #d4e4ff 100%);
    border: 1px solid #667eea;
    color: #333;
}

.card-light-green {
    background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
    border: 1px solid #11998e;
    color: #333;
}

.card-light-orange {
    background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
    border: 1px solid #f5576c;
    color: #333;
}

/* === 进度条 === */
.progress-container {
    margin: 12px 0;
}

.progress-label {
    font-weight: 600;
    margin-bottom: 6px;
    color: #333;
    display: flex;
    justify-content: space-between;
}

.progress-bar {
    height: 24px;
    background: #e9ecef;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
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
    text-shadow: 0 1px 2px rgba(0,0,0,0.2);
    transition: width 0.5s ease;
}

.progress-blue { background: linear-gradient(90deg, #667eea, #764ba2); }
.progress-green { background: linear-gradient(90deg, #11998e, #38ef7d); }
.progress-orange { background: linear-gradient(90deg, #f093fb, #f5576c); }
.progress-purple { background: linear-gradient(90deg, #4facfe, #00f2fe); }
.progress-red { background: linear-gradient(90deg, #ff416c, #ff4b2b); }
.progress-yellow { background: linear-gradient(90deg, #f7971e, #ffd200); }

/* === 评分条（简化版） === */
.rating {
    display: flex;
    align-items: center;
    margin: 10px 0;
    gap: 12px;
}

.rating-label {
    font-weight: 600;
    min-width: 100px;
    color: #333;
}

.rating-bar {
    flex: 1;
    height: 16px;
    background: #e9ecef;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
}

.rating-fill {
    height: 100%;
    background: linear-gradient(90deg, #667eea, #764ba2);
    border-radius: 8px;
}

.rating-value {
    font-weight: 700;
    color: #667eea;
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
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    transition: transform 0.2s, box-shadow 0.2s;
}

.feature-icon {
    font-size: 36px;
    margin-bottom: 10px;
}

.feature-title {
    font-weight: 600;
    font-size: 15px;
    margin-bottom: 5px;
    color: #333;
}

.feature-desc {
    color: #4a5568;
    font-size: 15px;
}

/* === 提示框 === */
.alert {
    padding: 15px 20px;
    border-radius: 10px;
    margin: 15px 0;
    border-left: 4px solid;
}

.alert-success {
    background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
    border-color: #28a745;
    color: #155724;
}

.alert-warning {
    background: linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%);
    border-color: #ffc107;
    color: #856404;
}

.alert-info {
    background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
    border-color: #17a2b8;
    color: #0c5460;
}

.alert-danger {
    background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
    border-color: #dc3545;
    color: #721c24;
}

.alert-primary {
    background: linear-gradient(135deg, #cce5ff 0%, #b8daff 100%);
    border-color: #007bff;
    color: #004085;
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

.tag-blue { background: #e3f2fd; color: #1976d2; border: 1px solid #90caf9; }
.tag-green { background: #e8f5e9; color: #388e3c; border: 1px solid #a5d6a7; }
.tag-orange { background: #fff3e0; color: #f57c00; border: 1px solid #ffcc80; }
.tag-purple { background: #f3e5f5; color: #7b1fa2; border: 1px solid #ce93d8; }
.tag-red { background: #ffebee; color: #d32f2f; border: 1px solid #ef9a9a; }
.tag-teal { background: #e0f2f1; color: #00796b; border: 1px solid #80cbc4; }
.tag-indigo { background: #e8eaf6; color: #303f9f; border: 1px solid #9fa8da; }
.tag-pink { background: #fce4ec; color: #c2185b; border: 1px solid #f48fb1; }

/* === 精美表格 === */
table {
    border-collapse: collapse;
    width: 100%;
    margin: 15px 0;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 2px 10px rgba(0,0,0,0.08);
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
    border-bottom: 1px solid #e9ecef;
}

tr:nth-child(even) {
    background: #f8f9fa;
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
    margin: 8px 0;
    color: #2d3748;
}

/* === 强调文本 === */
strong, b {
    color: #1a1a2e;
    font-weight: 700;
}

em, i {
    font-style: italic;
    color: #4a5568;
}

li {
    margin: 6px 0;
}

/* === 代码块 === */
code {
    background: #f1f3f4;
    padding: 2px 8px;
    border-radius: 4px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 13px;
    color: #d63384;
}

pre {
    background: #1e1e1e;
    color: #d4d4d4;
    padding: 16px;
    border-radius: 10px;
    overflow-x: auto;
    margin: 15px 0;
    box-shadow: 0 4px 15px rgba(0,0,0,0.15);
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
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    border-radius: 0 10px 10px 0;
    color: #555;
}

/* === 强调文本 === */
strong, b {
    color: #1a1a2e;
    font-weight: 600;
}

em, i {
    font-style: italic;
}

/* === 链接 === */
a {
    color: #667eea;
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

/* === 信息卡片（带图标） === */
.info-card {
    display: flex;
    align-items: flex-start;
    gap: 15px;
    padding: 18px;
    background: #f8f9fa;
    border-radius: 12px;
    margin: 15px 0;
    border: 1px solid #e0e0e0;
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
    color: #333;
}

.info-card-desc {
    color: #666;
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
    color: #666;
    font-size: 13px;
}
"""
