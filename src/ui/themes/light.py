"""亮色主题CSS"""

LIGHT_CSS = """
body {
    font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif;
    font-size: 14px;
    color: #333333;
    background-color: #ffffff;
    line-height: 1.8;
    padding: 15px;
    margin: 0;
}

h1 {
    color: #1a73e8;
    font-size: 22px;
    font-weight: bold;
    border-bottom: 2px solid #1a73e8;
    padding-bottom: 10px;
    margin-top: 20px;
    margin-bottom: 15px;
}

h2 {
    color: #1a73e8;
    font-size: 18px;
    font-weight: bold;
    border-bottom: 1px solid #e0e0e0;
    padding-bottom: 8px;
    margin-top: 18px;
    margin-bottom: 12px;
}

h3 {
    color: #333333;
    font-size: 16px;
    font-weight: bold;
    margin-top: 15px;
    margin-bottom: 10px;
}

h4 {
    color: #555555;
    font-size: 14px;
    font-weight: bold;
    margin-top: 12px;
    margin-bottom: 8px;
}

p {
    margin: 8px 0;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;
}

th {
    background-color: #f0f7ff;
    color: #1a73e8;
    font-weight: bold;
    border: 1px solid #d0e0f0;
    padding: 10px 12px;
    text-align: left;
}

td {
    border: 1px solid #e0e0e0;
    padding: 8px 12px;
    vertical-align: top;
}

tr:nth-child(even) {
    background-color: #fafafa;
}

tr:hover {
    background-color: #f5f8fc;
}

code {
    background-color: #f5f5f5;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 13px;
    color: #d63384;
}

pre {
    background-color: #f8f9fa;
    padding: 15px;
    border-radius: 8px;
    overflow-x: auto;
    border: 1px solid #e0e0e0;
    margin: 12px 0;
}

pre code {
    background-color: transparent;
    padding: 0;
    color: #333333;
}

ul, ol {
    padding-left: 25px;
    margin: 8px 0;
}

li {
    margin: 5px 0;
}

blockquote {
    border-left: 4px solid #1a73e8;
    margin: 12px 0;
    padding: 10px 15px;
    background-color: #f0f7ff;
    color: #555;
    border-radius: 0 8px 8px 0;
}

strong, b {
    color: #1a73e8;
    font-weight: bold;
}

em, i {
    font-style: italic;
    color: #555555;
}

a {
    color: #1a73e8;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

hr {
    border: none;
    border-top: 1px solid #e0e0e0;
    margin: 20px 0;
}

/* 标签样式 - 用于关键词 */
.tag {
    display: inline-block;
    background-color: #e8f0fe;
    color: #1a73e8;
    padding: 4px 10px;
    border-radius: 15px;
    font-size: 12px;
    margin: 2px 4px;
    border: 1px solid #d0e0f0;
}

/* 高亮样式 */
.highlight {
    background-color: #fff3cd;
    padding: 2px 4px;
    border-radius: 3px;
}

/* 警告/提示框 */
.warning {
    background-color: #fff3cd;
    border-left: 4px solid #ffc107;
    padding: 10px 15px;
    margin: 12px 0;
    border-radius: 0 8px 8px 0;
}

.info {
    background-color: #d1ecf1;
    border-left: 4px solid #17a2b8;
    padding: 10px 15px;
    margin: 12px 0;
    border-radius: 0 8px 8px 0;
}

.success {
    background-color: #d4edda;
    border-left: 4px solid #28a745;
    padding: 10px 15px;
    margin: 12px 0;
    border-radius: 0 8px 8px 0;
}

.error {
    background-color: #f8d7da;
    border-left: 4px solid #dc3545;
    padding: 10px 15px;
    margin: 12px 0;
    border-radius: 0 8px 8px 0;
}
"""
