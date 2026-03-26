"""测试公司调研功能"""

# 测试导入
try:
    from src.core.company_research_client import CompanyResearchClient, CompanyResearchError
    from src.ui.company_research_widget import CompanyResearchWidget
    print("OK: 导入成功")
except Exception as e:
    print("ERROR: 导入失败: {}".format(e))
    exit(1)

# 测试配置
try:
    from src.core.config import AppConfig
    config = AppConfig()
    print("OK: 配置类正常，包含 tavily_api_key: {}".format(hasattr(config, 'tavily_api_key')))
except Exception as e:
    print("ERROR: 配置测试失败: {}".format(e))
    exit(1)

print("\n所有基础测试通过！")
print("\n使用说明：")
print("1. 启动程序后，在配置区第二行输入 Tavily API Key")
print("2. 点击'保存配置'按钮")
print("3. 切换到'公司调研'标签页")
print("4. 输入公司名称，点击'开始深度调研'")
print("5. 等待调研完成，结果会流式显示")
