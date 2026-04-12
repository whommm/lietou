#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能岗位分析与寻访助手 - 主入口
"""

import sys
import os
import logging
import multiprocessing


def _global_exception_handler(exc_type, exc_value, exc_traceback):
    """全局异常处理，防止未捕获异常导致闪退"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.error("未捕获异常", exc_info=(exc_type, exc_value, exc_traceback))

    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "程序异常",
            f"发生未知错误：\n{exc_value}\n\n错误日志已保存到 logs/error.log",
        )
        root.destroy()
    except Exception:
        pass


sys.excepthook = _global_exception_handler

# 确保能正确导入 src 模块
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 配置日志
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "error.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

sys.path.insert(0, BASE_DIR)

from src.ui.main_window import MainWindow  # noqa: E402


def main():
    """程序主入口"""
    app = MainWindow()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
