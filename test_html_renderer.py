"""测试HTML渲染器 - 验证tkinterweb技术可行性"""

import sys
import os

# 确保能正确导入src模块
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)


def test_imports():
    """测试依赖导入"""
    print("=" * 50)
    print("测试1: 依赖导入")
    print("=" * 50)

    try:
        import tkinterweb
        version = tkinterweb.__version__ if hasattr(tkinterweb, '__version__') else '未知'
        print(f"  [OK] tkinterweb 版本: {version}")
    except ImportError as e:
        print(f"  [FAIL] tkinterweb 导入失败: {e}")
        assert False, f"tkinterweb 导入失败: {e}"

    try:
        import markdown
        version = getattr(markdown, '__version__', '未知')
        print(f"  [OK] markdown 版本: {version}")
    except ImportError as e:
        print(f"  [FAIL] markdown 导入失败: {e}")
        assert False, f"markdown 导入失败: {e}"

    try:
        import importlib.util

        spec = importlib.util.find_spec("src.ui.html_renderer")
        if spec is None:
            print("  [FAIL] HtmlRenderer 导入失败: 模块不存在")
            assert False, "HtmlRenderer 导入失败: 模块不存在"
        from src.ui.html_renderer import HtmlRenderer  # noqa: F401
        print("  [OK] HtmlRenderer 导入成功")
    except ImportError as e:
        print(f"  [FAIL] HtmlRenderer 导入失败: {e}")
        assert False, f"HtmlRenderer 导入失败: {e}"

    try:
        from src.ui.themes import LIGHT_CSS, DARK_CSS
        print(f"  [OK] 主题CSS导入成功 (亮色: {len(LIGHT_CSS)}字节, 暗色: {len(DARK_CSS)}字节)")
    except ImportError as e:
        print(f"  [FAIL] 主题CSS导入失败: {e}")
        assert False, f"主题CSS导入失败: {e}"

    print("\n所有依赖导入成功!")
    assert True


def test_markdown_conversion():
    """测试Markdown转换"""
    print("\n" + "=" * 50)
    print("测试2: Markdown转换")
    print("=" * 50)

    import markdown

    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'nl2br'])

    test_content = """
# 测试标题

这是一个**粗体**和*斜体*的测试。

## 二级标题

- 列表项1
- 列表项2
- 列表项3

### 表格测试

| 姓名 | 年龄 | 职位 |
|------|------|------|
| 张三 | 28 | 工程师 |
| 李四 | 32 | 经理 |

### 代码块测试

```python
def hello():
    print("Hello World")
```

> 这是一个引用块
"""
    try:
        html = md.convert(test_content)
        print("  [OK] Markdown转换成功")
        print(f"  输出HTML长度: {len(html)} 字节")
        print("\nHTML预览 (前500字符):")
        print("-" * 40)
        print(html[:500])
        print("-" * 40)
        assert True
    except Exception as e:
        print(f"  [FAIL] Markdown转换失败: {e}")
        assert False, f"Markdown转换失败: {e}"


def test_gui():
    """测试GUI显示（需要手动验证）"""
    import pytest
    pytest.skip("GUI test requires manual interaction")

    print("\n" + "=" * 50)
    print("测试3: GUI显示测试")
    print("=" * 50)
    print("即将打开GUI窗口，请验证:")
    print("  1. 窗口是否正常显示")
    print("  2. HTML内容是否正确渲染")
    print("  3. 深色/亮色主题是否正常")
    print("\n关闭窗口后继续...\n")

    import customtkinter as ctk
    from src.ui.html_renderer import HtmlRenderer

    # 创建测试窗口
    ctk.set_appearance_mode("light")
    root = ctk.CTk()
    root.title("HTML渲染器测试")
    root.geometry("800x600")

    # 测试内容
    test_content = """
# 岗位分析测试

## 模块一：岗位定性与行业科普

**所属行业：** 互联网/科技 - 人工智能

**大白话解释：** 这个人招进来主要是为了开发和优化AI算法，提升产品智能化水平。

### 行业科普

人工智能（AI）是当前最热门的技术领域之一，主要涉及：

- **机器学习**：让计算机从数据中学习规律
- **深度学习**：使用神经网络处理复杂任务
- **自然语言处理**：让机器理解和生成人类语言

### 知名企业

| 公司 | 领域 | 特点 |
|------|------|------|
| 百度 | 自动驾驶、搜索 | Apollo平台 |
| 阿里 | 电商AI、云计算 | 达摩院 |
| 字节跳动 | 推荐算法 | 抖音核心 |

## 模块二：核心门槛提取

**必须具备的硬条件：**
- 精通Python编程
- 熟悉TensorFlow或PyTorch
- 3年以上AI项目经验

**加分项：**
- 有顶会论文发表经验
- 熟悉分布式训练
- 有大模型微调经验

## 模块三：搜索关键词库

**核心岗位词：**
- AI工程师
- 机器学习工程师
- 算法工程师

**核心技能词：**
- Python
- TensorFlow
- PyTorch
- 深度学习

> 💡 **提示**：以上关键词可直接复制使用于招聘平台搜索
"""

    # 创建HTML渲染器
    renderer = HtmlRenderer(root, theme="light")
    renderer.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    # 设置内容
    renderer.set_content(test_content)

    # 配置权重
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)

    # 主题切换按钮
    def toggle_theme():
        current = renderer.theme
        new_theme = "dark" if current == "light" else "light"
        renderer.set_theme(new_theme)
        ctk.set_appearance_mode(new_theme)
        theme_btn.configure(text=f"切换到{'亮色' if new_theme == 'dark' else '暗色'}主题")

    theme_btn = ctk.CTkButton(
        root,
        text="切换到暗色主题",
        command=toggle_theme,
        width=150
    )
    theme_btn.grid(row=1, column=0, pady=10)

    root.mainloop()

    return True


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("  HTML渲染器技术可行性测试")
    print("=" * 60)

    # 测试导入
    if not test_imports():
        print("\n✗ 导入测试失败，请检查依赖安装")
        return False

    # 测试Markdown转换
    if not test_markdown_conversion():
        print("\n✗ Markdown转换测试失败")
        return False

    # 测试GUI
    input("\n按Enter键开始GUI测试...")
    test_gui()

    print("\n" + "=" * 60)
    print("  所有测试完成!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    main()
