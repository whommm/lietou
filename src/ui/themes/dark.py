"""暗色主题CSS"""

DARK_CSS = """
body {
    font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif;
    font-size: 14px;
    color: #e0e0e0;
    background-color: #1e1e1e;
    line-height: 1.8;
    padding: 15px;
    margin: 0;
}

h1 {
    color: #8ab4f8;
    font-size: 22px;
    font-weight: bold;
    border-bottom: 2px solid #8ab4f8;
    padding-bottom: 10px;
    margin-top: 20px;
    margin-bottom: 15px;
}

h2 {
    color: #8ab4f8;
    font-size: 18px;
    font-weight: bold;
    border-bottom: 1px solid #444444;
    padding-bottom: 8px;
    margin-top: 18px;
    margin-bottom: 12px;
}

h3 {
    color: #e0e0e0;
    font-size: 16px;
    font-weight: bold;
    margin-top: 15px;
    margin-bottom: 10px;
}

h4 {
    color: #b0b0b0;
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
    background-color: #2d3748;
    color: #8ab4f8;
    font-weight: bold;
    border: 1px solid #4a5568;
    padding: 10px 12px;
    text-align: left;
}

td {
    border: 1px solid #4a5568;
    padding: 8px 12px;
    vertical-align: top;
}

tr:nth-child(even) {
    background-color: #252525;
}

tr:hover {
    background-color: #2d3748;
}

code {
    background-color: #2d3748;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 13px;
    color: #f472b6;
}

pre {
    background-color: #2d3748;
    padding: 15px;
    border-radius: 8px;
    overflow-x: auto;
    border: 1px solid #4a5568;
    margin: 12px 0;
}

pre code {
    background-color: transparent;
    padding: 0;
    color: #e0e0e0;
}

ul, ol {
    padding-left: 25px;
    margin: 8px 0;
}

li {
    margin: 5px 0;
}

blockquote {
    border-left: 4px solid #8ab4f8;
    margin: 12px 0;
    padding: 10px 15px;
    background-color: #2d3748;
    color: #a0aec0;
    border-radius: 0 8px 8px 0;
}

strong, b {
    color: #8ab4f8;
    font-weight: bold;
}

em, i {
    font-style: italic;
    color: #b0b0b0;
}

a {
    color: #8ab4f8;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

hr {
    border: none;
    border-top: 1px solid #4a5568;
    margin: 20px 0;
}

/* 标签样式 - 用于关键词 */
.tag {
    display: inline-block;
    background-color: #3d4a5c;
    color: #8ab4f8;
    padding: 4px 10px;
    border-radius: 15px;
    font-size: 12px;
    margin: 2px 4px;
    border: 1px solid #4a5568;
}

/* 高亮样式 */
.highlight {
    background-color: #4a4a2d;
    padding: 2px 4px;
    border-radius: 3px;
}

/* 警告/提示框 */
.warning {
    background-color: #3d3a2d;
    border-left: 4px solid #ffc107;
    padding: 10px 15px;
    margin: 12px 0;
    border-radius: 0 8px 8px 0;
    color: #e0d0a0;
}

.info {
    background-color: #2d3a3d;
    border-left: 4px solid #17a2b8;
    padding: 10px 15px;
    margin: 12px 0;
    border-radius: 0 8px 8px 0;
    color: #a0d0d8;
}

.success {
    background-color: #2d3d30;
    border-left: 4px solid #28a745;
    padding: 10px 15px;
    margin: 12px 0;
    border-radius: 0 8px 8px 0;
    color: #a0d8a8;
}

.error {
    background-color: #3d2d2e;
    border-left: 4px solid #dc3545;
    padding: 10px 15px;
    margin: 12px 0;
    border-radius: 0 8px 8px 0;
    color: #d8a0a4;
}
"""
