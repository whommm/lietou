#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能岗位分析与寻访助手 - 主入口
"""

import sys
import os

# 确保能正确导入 src 模块
if getattr(sys, 'frozen', False):
    # 打包后的路径
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

from src.ui.main_window import MainWindow


def main():
    """程序主入口"""
    app = MainWindow()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
