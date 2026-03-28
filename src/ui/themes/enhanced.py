"""增强版精美CSS主题"""

ENHANCED_CSS = """
/* ==================== 基础样式 ==================== */
body {
    font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif;
    font-size: 14px;
    color: #333333;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    line-height: 1.8;
    padding: 20px;
    margin: 0;
    min-height: 100vh;
}

/* ==================== 标题样式 ==================== */
h1 {
    color: #2c3e50;
    font-size: 28px;
    font-weight: bold;
    background: linear-gradient(90deg, #667eea, #764ba2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    padding-bottom: 15px;
    margin-top: 25px;
    margin-bottom: 20px;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
}

h2 {
    color: #34495e;
    font-size: 22px;
    font-weight: bold;
    border-left: 5px solid #667eea;
    padding-left: 15px;
    margin-top: 25px;
    margin-bottom: 15px;
}

h3 {
    color: #2c3e50;
    font-size: 18px;
    font-weight: bold;
    margin-top: 20px;
    margin-bottom: 12px;
}

h4 {
    color: #555555;
    font-size: 16px;
    font-weight: bold;
    margin-top: 15px;
    margin-bottom: 10px;
}

/* ==================== 渐变卡片组件 ==================== */
.card {
    background: #ffffff;
    border-radius: 12px;
    padding: 20px;
    margin: 15px 0;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    border: 1px solid rgba(255,255,255,0.8);
}

.card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 25px rgba(0,0,0,0.15);
}

/* 蓝色渐变卡片 */
.card-blue {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #ffffff;
    border: none;
}

.card-blue h3, .card-blue h4 {
    color: #ffffff;
}

/* 绿色渐变卡片 */
.card-green {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    color: #ffffff;
    border: none;
}

.card-green h3, .card-green h4 {
    color: #ffffff;
}

/* 橙色渐变卡片 */
.card-orange {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    color: #ffffff;
    border: none;
}

.card-orange h3, .card-orange h4 {
    color: #ffffff;
}

/* 紫色渐变卡片 */
.card-purple {
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    color: #ffffff;
    border: none;
}

.card-purple h3, .card-purple h4 {
    color: #ffffff;
}

/* 红色渐变卡片 */
.card-red {
    background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
    color: #ffffff;
    border: none;
}

.card-red h3, .card-red h4 {
    color: #ffffff;
}

/* ==================== 进度条组件 ==================== */
.progress-container {
    background: #e9ecef;
    border-radius: 10px;
    height: 20px;
    margin: 10px 0;
    overflow: hidden;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
}

.progress-bar {
    height: 100%;
    border-radius: 10px;
    background: linear-gradient(90deg, #667eea, #764ba2);
    transition: width 0.5s ease;
    position: relative;
}

.progress-bar::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.3) 50%, rgba(255,255,255,0) 100%);
    animation: shimmer 2s infinite;
}

@keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}

/* 不同颜色的进度条 */
.progress-blue {
    background: linear-gradient(90deg, #667eea, #764ba2);
}

.progress-green {
    background: linear-gradient(90deg, #11998e, #38ef7d);
}

.progress-orange {
    background: linear-gradient(90deg, #f093fb, #f5576c);
}

.progress-purple {
    background: linear-gradient(90deg, #4facfe, #00f2fe);
}

.progress-red {
    background: linear-gradient(90deg, #fa709a, #fee140);
}

/* 进度条标签 */
.progress-label {
    display: flex;
    justify-content: space-between;
    margin-bottom: 5px;
    font-weight: bold;
    color: #495057;
}

/* ==================== 评分条组件 ==================== */
.rating {
    display: flex;
    align-items: center;
    margin: 10px 0;
}

.rating-star {
    color: #ffc107;
    font-size: 24px;
    margin-right: 5px;
    text-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.rating-star.empty {
    color: #e0e0e0;
}

.rating-score {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #ffffff;
    padding: 5px 12px;
    border-radius: 20px;
    font-weight: bold;
    font-size: 16px;
    margin-left: 10px;
}

/* 评分条 */
.rating-bar {
    display: flex;
    align-items: center;
    margin: 8px 0;
}

.rating-bar-label {
    width: 120px;
    font-weight: bold;
    color: #495057;
}

.rating-bar-container {
    flex-grow: 1;
    background: #e9ecef;
    border-radius: 8px;
    height: 12px;
    margin: 0 10px;
    overflow: hidden;
}

.rating-bar-fill {
    height: 100%;
    border-radius: 8px;
    background: linear-gradient(90deg, #ffc107, #ffca28);
}

.rating-bar-value {
    width: 50px;
    text-align: right;
    font-weight: bold;
    color: #495057;
}

/* ==================== 特性卡片 ==================== */
.feature-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 25px;
    margin: 15px 0;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    text-align: center;
    transition: all 0.3s ease;
    border-top: 4px solid #667eea;
}

.feature-card:hover {
    transform: translateY(-8px);
    box-shadow: 0 12px 30px rgba(0,0,0,0.15);
}

.feature-icon {
    font-size: 48px;
    margin-bottom: 15px;
    display: block;
}

.feature-title {
    font-size: 18px;
    font-weight: bold;
    color: #2c3e50;
    margin-bottom: 10px;
}

.feature-desc {
    color: #6c757d;
    font-size: 14px;
}

/* 特性卡片不同颜色 */
.feature-blue {
    border-top-color: #667eea;
}

.feature-green {
    border-top-color: #11998e;
}

.feature-orange {
    border-top-color: #f5576c;
}

.feature-purple {
    border-top-color: #764ba2;
}

.feature-red {
    border-top-color: #fa709a;
}

/* ==================== 提示框组件 ==================== */
.alert {
    padding: 15px 20px;
    margin: 15px 0;
    border-radius: 10px;
    display: flex;
    align-items: center;
    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}

.alert-icon {
    font-size: 24px;
    margin-right: 15px;
    flex-shrink: 0;
}

.alert-content {
    flex-grow: 1;
}

.alert-title {
    font-weight: bold;
    margin-bottom: 5px;
}

/* 成功提示 */
.alert-success {
    background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
    border-left: 5px solid #28a745;
    color: #155724;
}

/* 信息提示 */
.alert-info {
    background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
    border-left: 5px solid #17a2b8;
    color: #0c5460;
}

/* 警告提示 */
.alert-warning {
    background: linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%);
    border-left: 5px solid #ffc107;
    color: #856404;
}

/* 错误提示 */
.alert-danger {
    background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
    border-left: 5px solid #dc3545;
    color: #721c24;
}

/* ==================== 表格样式 ==================== */
.table-container {
    background: #ffffff;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    margin: 20px 0;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 0;
}

thead {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #ffffff;
}

th {
    padding: 15px 12px;
    text-align: left;
    font-weight: bold;
    color: #ffffff;
    border: none;
}

td {
    padding: 12px;
    border-bottom: 1px solid #e9ecef;
    vertical-align: middle;
}

tr:last-child td {
    border-bottom: none;
}

tr:nth-child(even) {
    background-color: #f8f9fa;
}

tr:hover {
    background-color: #e9ecef;
    transition: background-color 0.3s ease;
}

/* 表格中的标签 */
.table-tag {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 15px;
    font-size: 12px;
    font-weight: bold;
    margin: 2px;
}

.tag-high {
    background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
    color: #ffffff;
}

.tag-medium {
    background: linear-gradient(135deg, #ffc107 0%, #ffca28 100%);
    color: #212529;
}

.tag-low {
    background: linear-gradient(135deg, #dc3545 0%, #e83e8c 100%);
    color: #ffffff;
}

/* ==================== 模块化布局 ==================== */
.module {
    background: #ffffff;
    border-radius: 12px;
    padding: 20px;
    margin: 20px 0;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    border: 1px solid rgba(255,255,255,0.8);
}

.module-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #ffffff;
    padding: 15px 20px;
    margin: -20px -20px 20px -20px;
    border-radius: 12px 12px 0 0;
    font-weight: bold;
    font-size: 16px;
}

.module-title {
    display: flex;
    align-items: center;
}

.module-icon {
    margin-right: 10px;
    font-size: 20px;
}

/* 不同颜色的模块头 */
.module-header-blue {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.module-header-green {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
}

.module-header-orange {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.module-header-purple {
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.module-header-red {
    background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
}

/* ==================== 按钮样式 ==================== */
.btn {
    display: inline-block;
    padding: 10px 20px;
    border-radius: 25px;
    font-weight: bold;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    border: none;
}

.btn-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #ffffff;
}

.btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 15px rgba(102,126,234,0.4);
}

.btn-success {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    color: #ffffff;
}

.btn-success:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 15px rgba(17,153,142,0.4);
}

.btn-warning {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    color: #ffffff;
}

.btn-warning:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 15px rgba(245,87,108,0.4);
}

/* ==================== 标签样式 ==================== */
.tag {
    display: inline-block;
    padding: 5px 12px;
    border-radius: 15px;
    font-size: 12px;
    font-weight: bold;
    margin: 3px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.tag-blue {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #ffffff;
}

.tag-green {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    color: #ffffff;
}

.tag-orange {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    color: #ffffff;
}

.tag-purple {
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    color: #ffffff;
}

.tag-red {
    background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
    color: #ffffff;
}

/* ==================== 高亮样式 ==================== */
.highlight {
    background: linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%);
    padding: 3px 6px;
    border-radius: 4px;
    font-weight: bold;
}

/* ==================== 引用样式 ==================== */
blockquote {
    border-left: 5px solid #667eea;
    margin: 15px 0;
    padding: 15px 20px;
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    border-radius: 0 10px 10px 0;
    box-shadow: 0 2px 5px rgba(0,0,0,0.05);
}

/* ==================== 代码样式 ==================== */
code {
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    padding: 3px 8px;
    border-radius: 5px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 13px;
    color: #e83e8c;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

pre {
    background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
    padding: 20px;
    border-radius: 10px;
    overflow-x: auto;
    margin: 15px 0;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}

pre code {
    background: transparent;
    color: #ecf0f1;
    padding: 0;
}

/* ==================== 列表样式 ==================== */
ul, ol {
    padding-left: 25px;
    margin: 10px 0;
}

li {
    margin: 8px 0;
    padding-left: 5px;
}

/* 带图标的列表 */
.icon-list {
    list-style: none;
    padding-left: 0;
}

.icon-list li {
    position: relative;
    padding-left: 30px;
    margin: 10px 0;
}

.icon-list li::before {
    content: '✓';
    position: absolute;
    left: 0;
    color: #28a745;
    font-weight: bold;
}

/* ==================== 链接样式 ==================== */
a {
    color: #667eea;
    text-decoration: none;
    transition: all 0.3s ease;
}

a:hover {
    color: #764ba2;
    text-decoration: underline;
}

/* ==================== 分割线 ==================== */
hr {
    border: none;
    height: 2px;
    background: linear-gradient(90deg, #667eea, #764ba2, #667eea);
    margin: 25px 0;
    border-radius: 2px;
}

/* ==================== 工具类 ==================== */
.text-center {
    text-align: center;
}

.text-right {
    text-align: right;
}

.mt-10 {
    margin-top: 10px;
}

.mb-10 {
    margin-bottom: 10px;
}

.mt-20 {
    margin-top: 20px;
}

.mb-20 {
    margin-bottom: 20px;
}

.p-10 {
    padding: 10px;
}

.p-20 {
    padding: 20px;
}

.flex {
    display: flex;
}

.flex-wrap {
    flex-wrap: wrap;
}

.gap-10 {
    gap: 10px;
}

.gap-20 {
    gap: 20px;
}

.justify-between {
    justify-content: space-between;
}

.align-center {
    align-items: center;
}

/* ==================== 网格布局 ==================== */
.grid {
    display: flex;
    flex-wrap: wrap;
    margin: -10px;
}

.grid-item {
    flex: 1;
    min-width: 250px;
    padding: 10px;
}

.grid-2 .grid-item {
    flex: 0 0 50%;
}

.grid-3 .grid-item {
    flex: 0 0 33.333%;
}

.grid-4 .grid-item {
    flex: 0 0 25%;
}
"""
