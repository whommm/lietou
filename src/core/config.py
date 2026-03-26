"""配置管理模块"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class AppConfig:
    """应用配置数据类"""
    api_base_url: str = ""
    api_key: str = ""
    model_name: str = "deepseek-chat"
    tavily_api_key: str = ""  # Tavily API Key
    timeout: int = 120
    theme: str = "dark"
    stream_mode: bool = False  # 流式输出开关，默认关闭


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            # 配置文件放在程序同级目录
            self.config_path = self._get_default_config_path()
        else:
            self.config_path = config_path
        self.config = self._load_config()

    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        # 支持打包后的路径
        if getattr(os.sys, 'frozen', False):
            base_dir = os.path.dirname(os.sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_dir, "config.json")

    def _load_config(self) -> AppConfig:
        """从文件加载配置"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return AppConfig(**data)
            except (json.JSONDecodeError, TypeError, KeyError):
                return AppConfig()
        return AppConfig()

    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.config), f, ensure_ascii=False, indent=2)
            return True
        except IOError:
            return False

    def update(self, **kwargs) -> None:
        """更新配置项"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
