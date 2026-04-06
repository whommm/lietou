"""亮色主题 CSS。"""

LIGHT_CSS = """
* { box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', 'PingFang SC', sans-serif;
    font-size: 16px;
    color: #1b2942;
    background:
        radial-gradient(circle at top left, rgba(98, 124, 255, 0.12), transparent 28%),
        radial-gradient(circle at top right, rgba(82, 169, 255, 0.10), transparent 26%),
        linear-gradient(180deg, #eef4ff 0%, #f8fbff 56%, #f0f5ff 100%);
    line-height: 1.72;
    padding: 30px;
    margin: 0;
}

p { color: #33425f; margin: 12px 0 16px; }
h1, h2, h3, h4, h5, h6 { color: #13233d; font-weight: 800; line-height: 1.28; letter-spacing: -0.02em; }
h1 { font-size: 30px; margin: 22px 0 14px; }
h2 { font-size: 24px; margin: 18px 0 10px; }
h3 { font-size: 20px; margin: 16px 0 8px; }
h4 { font-size: 18px; margin: 14px 0 8px; }

.card {
    padding: 22px;
    border-radius: 24px;
    margin: 18px 0;
    border: 1px solid #d9e5ff;
    background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(246,249,255,0.92));
    box-shadow: 0 18px 48px rgba(77, 101, 171, 0.10), inset 0 1px 0 rgba(255,255,255,0.88);
}
.card h1, .card h2, .card h3, .card h4 { border: none; padding: 0; margin: 0 0 12px; }
.card-blue { background: linear-gradient(180deg, #edf4ff, #dde9ff); border-color: #c9d8ff; color: #1d4ed8; }
.card-green { background: linear-gradient(180deg, #ecfdf5, #dcfce7); border-color: #b7eccd; color: #166534; }
.card-orange { background: linear-gradient(180deg, #fff5eb, #ffe8d2); border-color: #ffd3ae; color: #9a3412; }
.card-purple { background: linear-gradient(180deg, #f5efff, #eadfff); border-color: #dccdff; color: #6b21a8; }
.card-red { background: linear-gradient(180deg, #fff0f3, #ffe0e7); border-color: #ffc7d3; color: #be123c; }
.card-yellow { background: linear-gradient(180deg, #fffbe6, #fff1b8); border-color: #f4e08a; color: #854d0e; }
.card-gray { background: linear-gradient(180deg, #f9fbff, #f1f5fd); border-color: #dbe4f3; color: #44526a; }

.progress-container { margin: 16px 0; }
.progress-label { font-weight: 700; margin-bottom: 8px; color: #3b4b66; display: flex; justify-content: space-between; font-size: 14px; }
.progress-bar {
    height: 22px;
    background: rgba(210, 223, 248, 0.66);
    border-radius: 999px;
    overflow: hidden;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);
}
.progress-fill {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, #4f7cff 0%, #7297ff 55%, #7d6bff 100%);
    transition: width 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 700;
    font-size: 12px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.22);
}
.progress-blue { background: linear-gradient(90deg, #4f7cff, #7aa6ff); }
.progress-green { background: linear-gradient(90deg, #10b981, #3dd5a1); }
.progress-orange { background: linear-gradient(90deg, #f59e0b, #fb923c); }
.progress-purple { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
.progress-red { background: linear-gradient(90deg, #ef4444, #fb7185); }

.rating { display: flex; align-items: center; margin: 12px 0; gap: 12px; }
.rating-label { font-weight: 700; min-width: 92px; color: #52627c; font-size: 14px; }
.rating-bar { flex: 1; height: 10px; background: rgba(210, 223, 248, 0.66); border-radius: 999px; overflow: hidden; }
.rating-fill { height: 100%; background: linear-gradient(90deg, #4f7cff, #7d6bff); border-radius: 999px; }
.rating-value { font-weight: 800; color: #13233d; min-width: 44px; text-align: right; font-size: 14px; }

.alert {
    padding: 14px 16px;
    border-radius: 18px;
    margin: 16px 0;
    border: 1px solid;
    font-size: 14px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.35);
}
.alert-success { background: #ecfdf5; border-color: #a7f3d0; color: #166534; }
.alert-warning { background: #fff7e6; border-color: #fcd34d; color: #92400e; }
.alert-info { background: #edf4ff; border-color: #bfd3ff; color: #1d4ed8; }
.alert-danger { background: #fff0f3; border-color: #f9a8d4; color: #be123c; }
.alert-primary { background: #f5f8ff; border-color: #d9e5ff; color: #44526a; }

.feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin: 16px 0; }
.feature-card {
    background: rgba(255,255,255,0.86);
    border: 1px solid #d9e5ff;
    border-radius: 22px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 12px 28px rgba(77, 101, 171, 0.08);
}
.feature-icon { font-size: 32px; margin-bottom: 12px; color: #4f7cff; }
.feature-title { font-weight: 800; font-size: 15px; margin-bottom: 6px; color: #13233d; }
.feature-desc { color: #5b6b84; font-size: 14px; }

.tag-cloud { display: flex; flex-wrap: wrap; gap: 10px; margin: 12px 0; }
.tag {
    display: inline-flex;
    align-items: center;
    padding: 8px 14px;
    border-radius: 999px;
    font-size: 14px;
    font-weight: 700;
    background-color: rgba(255,255,255,0.82);
    color: #52627c;
    border: 1px solid #d9e5ff;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.2s ease;
    box-shadow: 0 8px 20px rgba(101, 122, 173, 0.08);
}
.tag:hover { transform: translateY(-1px); text-decoration: none; filter: brightness(0.99); }
.tag-blue { background: #edf4ff; color: #1d4ed8; border-color: #c9d8ff; }
.tag-green { background: #ecfdf5; color: #15803d; border-color: #b7eccd; }
.tag-orange { background: #fff1e7; color: #c2410c; border-color: #fdba74; }
.tag-purple { background: #f5efff; color: #7e22ce; border-color: #dccdff; }
.tag-red { background: #fff0f3; color: #be123c; border-color: #f9a8d4; }

table { border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 14px; overflow: hidden; border-radius: 18px; }
th, td { padding: 12px 14px; border: 1px solid #d9e5ff; text-align: left; }
th { background: #edf4ff; color: #13233d; font-weight: 800; }
tr:nth-child(even) { background: rgba(255,255,255,0.56); }
tr:hover { background: rgba(237,244,255,0.72); }

ul, ol { padding-left: 24px; margin: 12px 0 16px 0; }
li { margin: 6px 0; color: #33425f; }
strong, b { color: #13233d; font-weight: 800; }
em, i { font-style: italic; color: #5b6b84; }
code {
    background-color: #edf4ff;
    padding: 2px 6px;
    border-radius: 8px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 13px;
    color: #db2777;
}
pre {
    background-color: #f6f9ff;
    border: 1px solid #d9e5ff;
    padding: 16px;
    border-radius: 18px;
    overflow-x: auto;
    margin: 16px 0;
}
pre code { background-color: transparent; color: #33425f; padding: 0; font-size: 13px; }
blockquote {
    border-left: 4px solid #c9d8ff;
    margin: 16px 0;
    padding: 10px 16px;
    background-color: rgba(255,255,255,0.74);
    border-radius: 0 16px 16px 0;
    color: #5b6b84;
}
a { color: #2563eb; text-decoration: none; }
a:hover { text-decoration: underline; }
hr { border: none; height: 1px; background-color: #d9e5ff; margin: 24px 0; }

.steps { margin: 20px 0; }
.step {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 12px 14px;
    margin-bottom: 12px;
    border-radius: 18px;
    background: rgba(255,255,255,0.74);
    border: 1px solid #d9e5ff;
}
.step-number {
    width: 30px;
    height: 30px;
    background: linear-gradient(135deg, #4f7cff, #7d6bff);
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    flex-shrink: 0;
}
.step-title { font-weight: 800; color: #13233d; margin-bottom: 4px; }
.step-desc { color: #5b6b84; font-size: 13px; }
"""
