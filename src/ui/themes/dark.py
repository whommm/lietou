"""暗色主题CSS - Aurora Glass 报告风格"""

DARK_CSS = """
* { box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', 'PingFang SC', sans-serif;
    font-size: 16px;
    color: #d9e6ff;
    background:
        radial-gradient(circle at top left, rgba(139, 92, 246, 0.22), transparent 28%),
        radial-gradient(circle at top right, rgba(59, 130, 246, 0.18), transparent 26%),
        radial-gradient(circle at bottom center, rgba(236, 72, 153, 0.12), transparent 34%),
        linear-gradient(180deg, #08101d 0%, #0b1527 52%, #101b31 100%);
    line-height: 1.7;
    padding: 28px;
    margin: 0;
}

p { color: #c8d8f7; margin: 12px 0 16px 0; }
h1, h2, h3, h4, h5, h6 { color: #f7f9ff; font-weight: 700; line-height: 1.3; }
h1 { font-size: 30px; margin: 22px 0 14px; }
h2 { font-size: 24px; margin: 18px 0 10px; }
h3 { font-size: 20px; margin: 16px 0 8px; }
h4 { font-size: 18px; margin: 14px 0 8px; }

.card {
    padding: 22px;
    border-radius: 22px;
    margin: 18px 0;
    border: 1px solid rgba(79, 124, 255, 0.22);
    background: linear-gradient(180deg, rgba(18, 31, 53, 0.92), rgba(12, 24, 43, 0.88));
    box-shadow: 0 28px 80px rgba(2, 8, 23, 0.36), inset 0 1px 0 rgba(255,255,255,0.06);
}

.card h1, .card h2, .card h3, .card h4 { border: none; padding: 0; margin: 0 0 12px 0; }
.card-blue { background: linear-gradient(180deg, rgba(19, 36, 70, 0.94), rgba(17, 43, 96, 0.82)); border-color: rgba(96, 165, 250, 0.35); color: #dbeafe; }
.card-green { background: linear-gradient(180deg, rgba(7, 45, 30, 0.94), rgba(7, 62, 44, 0.84)); border-color: rgba(74, 222, 128, 0.3); color: #dcfce7; }
.card-orange { background: linear-gradient(180deg, rgba(69, 26, 3, 0.94), rgba(96, 42, 12, 0.84)); border-color: rgba(251, 146, 60, 0.34); color: #ffedd5; }
.card-purple { background: linear-gradient(180deg, rgba(53, 16, 93, 0.94), rgba(72, 25, 136, 0.84)); border-color: rgba(196, 181, 253, 0.32); color: #f3e8ff; }
.card-red { background: linear-gradient(180deg, rgba(69, 10, 10, 0.94), rgba(97, 20, 20, 0.84)); border-color: rgba(248, 113, 113, 0.32); color: #ffe4e6; }
.card-yellow { background: linear-gradient(180deg, rgba(69, 39, 7, 0.94), rgba(104, 67, 14, 0.84)); border-color: rgba(250, 204, 21, 0.32); color: #fef3c7; }
.card-gray { background: linear-gradient(180deg, rgba(17, 24, 39, 0.94), rgba(18, 31, 53, 0.84)); border-color: rgba(71, 85, 105, 0.34); color: #d9e6ff; }

.progress-container { margin: 16px 0; }
.progress-label { font-weight: 600; margin-bottom: 8px; color: #e2e8f0; display: flex; justify-content: space-between; font-size: 14px; }
.progress-bar {
    height: 22px;
    background: rgba(29, 50, 83, 0.66);
    border-radius: 999px;
    overflow: hidden;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.35);
}
.progress-fill {
    height: 100%;
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 700;
    font-size: 12px;
    text-shadow: 0 1px 1px rgba(0,0,0,0.25);
    transition: width 0.3s ease;
    background: linear-gradient(90deg, #4f7cff 0%, #8b5cf6 100%);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.15);
}
.progress-blue { background: linear-gradient(90deg, #4f7cff, #60a5fa); }
.progress-green { background: linear-gradient(90deg, #10b981, #34d399); }
.progress-orange { background: linear-gradient(90deg, #f59e0b, #fb923c); }
.progress-purple { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
.progress-red { background: linear-gradient(90deg, #ef4444, #fb7185); }

.rating { display: flex; align-items: center; margin: 12px 0; gap: 12px; }
.rating-label { font-weight: 600; min-width: 92px; color: #b7c7e6; font-size: 14px; }
.rating-bar { flex: 1; height: 10px; background: rgba(29, 50, 83, 0.66); border-radius: 999px; overflow: hidden; }
.rating-fill { height: 100%; background: linear-gradient(90deg, #4f7cff, #8b5cf6); border-radius: 999px; }
.rating-value { font-weight: 700; color: #f8fbff; min-width: 44px; text-align: right; font-size: 14px; }

.alert {
    padding: 14px 16px;
    border-radius: 16px;
    margin: 16px 0;
    border: 1px solid;
    font-size: 14px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
}
.alert-success { background: rgba(6, 78, 59, 0.44); border-color: rgba(74, 222, 128, 0.34); color: #bbf7d0; }
.alert-warning { background: rgba(120, 53, 15, 0.42); border-color: rgba(251, 191, 36, 0.34); color: #fde68a; }
.alert-info { background: rgba(30, 58, 138, 0.38); border-color: rgba(96, 165, 250, 0.3); color: #bfdbfe; }
.alert-danger { background: rgba(127, 29, 29, 0.38); border-color: rgba(248, 113, 113, 0.32); color: #fecdd3; }
.alert-primary { background: rgba(23, 37, 64, 0.6); border-color: rgba(79,124,255,0.24); color: #d9e6ff; }

.feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin: 16px 0; }
.feature-card {
    background: rgba(14, 27, 46, 0.88);
    border: 1px solid rgba(79,124,255,0.2);
    border-radius: 20px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 18px 36px rgba(2, 8, 23, 0.24);
}
.feature-icon { font-size: 32px; margin-bottom: 12px; color: #7db2ff; }
.feature-title { font-weight: 700; font-size: 15px; margin-bottom: 6px; color: #f7f9ff; }
.feature-desc { color: #9bb0d7; font-size: 14px; }

.tag-cloud { display: flex; flex-wrap: wrap; gap: 10px; margin: 12px 0; }
.tag {
    display: inline-flex;
    align-items: center;
    padding: 8px 14px;
    border-radius: 999px;
    font-size: 14px;
    font-weight: 700;
    background-color: rgba(16, 30, 54, 0.88);
    color: #d9e6ff;
    border: 1px solid rgba(79,124,255,0.24);
    text-decoration: none;
    cursor: pointer;
    transition: all 0.2s ease;
    box-shadow: 0 16px 36px rgba(2, 8, 23, 0.22);
}
.tag:hover { transform: translateY(-1px); text-decoration: none; filter: brightness(1.05); }
.tag-blue { background: rgba(20, 45, 92, 0.92); color: #bfdbfe; border-color: rgba(96,165,250,0.32); }
.tag-green { background: rgba(6, 78, 59, 0.84); color: #bbf7d0; border-color: rgba(74,222,128,0.26); }
.tag-orange { background: rgba(120, 53, 15, 0.84); color: #fed7aa; border-color: rgba(251,146,60,0.28); }
.tag-purple { background: rgba(76, 29, 149, 0.84); color: #e9d5ff; border-color: rgba(196,181,253,0.28); }
.tag-red { background: rgba(127, 29, 29, 0.84); color: #fecdd3; border-color: rgba(248,113,113,0.28); }

table { border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 14px; overflow: hidden; border-radius: 16px; }
th, td { padding: 12px 14px; border: 1px solid rgba(79,124,255,0.22); text-align: left; }
th { background: rgba(18, 31, 53, 0.96); color: #f8fbff; font-weight: 700; }
tr:nth-child(even) { background: rgba(11, 21, 39, 0.5); }
tr:hover { background: rgba(27, 45, 80, 0.44); }

ul, ol { padding-left: 24px; margin: 12px 0 16px 0; }
li { margin: 6px 0; color: #c8d8f7; }
strong, b { color: #f7f9ff; font-weight: 700; }
em, i { font-style: italic; color: #9bb0d7; }
code {
    background-color: rgba(18, 31, 53, 0.96);
    padding: 2px 6px;
    border-radius: 8px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 13px;
    color: #f9a8d4;
}
pre {
    background-color: rgba(9, 17, 31, 0.96);
    border: 1px solid rgba(79,124,255,0.2);
    padding: 16px;
    border-radius: 18px;
    overflow-x: auto;
    margin: 16px 0;
}
pre code { background-color: transparent; color: #d9e6ff; padding: 0; font-size: 13px; }
blockquote {
    border-left: 4px solid rgba(96,165,250,0.42);
    margin: 16px 0;
    padding: 10px 16px;
    background-color: rgba(16, 30, 54, 0.84);
    border-radius: 0 16px 16px 0;
    color: #9bb0d7;
}
a { color: #93c5fd; text-decoration: none; }
a:hover { text-decoration: underline; }
hr { border: none; height: 1px; background-color: rgba(79,124,255,0.2); margin: 24px 0; }

.steps { margin: 20px 0; }
.step {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    margin-bottom: 12px;
    padding: 12px 14px;
    border-radius: 18px;
    background: rgba(14, 27, 46, 0.88);
    border: 1px solid rgba(79,124,255,0.2);
}
.step-number {
    width: 30px;
    height: 30px;
    background: linear-gradient(135deg, #4f7cff, #8b5cf6);
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    flex-shrink: 0;
}
.step-content { flex: 1; }
.step-title { font-weight: 700; margin-bottom: 4px; color: #f8fbff; }
.step-desc { color: #97a9ce; font-size: 13px; }
"""
