#!/usr/bin/env python3
"""
多模型配置向导
支持OpenAI、通义千问、文心一言、智谱GLM等
"""
import json
import sys
from pathlib import Path


def main():
    print("="*60)
    print("截图还原工具 - 多模型配置向导")
    print("="*60)
    print()
    
    config_path = Path(__file__).parent / "config.json"
    
    # 检查是否已存在配置
    if config_path.exists():
        print(f"⚠ 配置文件已存在: {config_path}")
        response = input("是否覆盖? (y/N): ").strip().lower()
        if response != 'y':
            print("已取消")
            return
        print()
    
    # 选择AI提供商
    print("选择AI提供商:")
    print("  1. OpenAI (GPT-4 Vision) - 国际领先，需要科学上网")
    print("  2. 通义千问 (Qwen-VL) - 阿里云，国内可用")
    print("  3. 文心一言 (ERNIE-Bot) - 百度，国内可用")
    print("  4. 智谱GLM (GLM-4V) - 清华，国内可用")
    print("  5. 豆包 (Doubao Vision) - 字节跳动，国内可用")
    print()
    
    provider_choice = input("选择 (1-5) [1]: ").strip() or "1"
    
    providers = {
        "1": ("openai", "OpenAI"),
        "2": ("qwen", "通义千问"),
        "3": ("ernie", "文心一言"),
        "4": ("glm", "智谱GLM"),
        "5": ("doubao", "豆包")
    }
    
    if provider_choice not in providers:
        print("❌ 无效选择")
        sys.exit(1)
    
    provider, provider_name = providers[provider_choice]
    print(f"\n已选择: {provider_name}")
    print()
    
    # 根据不同提供商配置
    config = {
        "provider": provider,
        "max_tokens": 4096,
        "temperature": 0.2
    }
    
    if provider == "openai":
        config.update(configure_openai())
    elif provider == "qwen":
        config.update(configure_qwen())
    elif provider == "ernie":
        config.update(configure_ernie())
    elif provider == "glm":
        config.update(configure_glm())
    elif provider == "doubao":
        config.update(configure_doubao())
    
    # 写入文件
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print()
        print("="*60)
        print("✅ 配置文件创建成功!")
        print("="*60)
        print(f"文件位置: {config_path}")
        print(f"提供商: {provider_name}")
        print(f"模型: {config.get('model', 'N/A')}")
        print()
        print("下一步:")
        print("  python check_env.py                    # 检查环境")
        print("  python process_single.py task_0001     # 处理task")
        print()
        print("注意: 不同模型的效果可能有差异，建议先用小任务测试")
        
    except Exception as e:
        print(f"❌ 创建配置文件失败: {e}")
        sys.exit(1)


def configure_openai():
    """配置OpenAI"""
    print("OpenAI配置:")
    print("获取API Key: https://platform.openai.com/api-keys")
    print()
    
    api_key = input("API Key (sk-...): ").strip()
    if not api_key:
        print("❌ API Key不能为空")
        sys.exit(1)
    
    print()
    print("选择模型:")
    print("  1. gpt-4-vision-preview (推荐，最准确)")
    print("  2. gpt-4o (更快，更便宜)")
    print("  3. gpt-4-turbo (平衡)")
    
    model_choice = input("选择 (1-3) [1]: ").strip() or "1"
    
    models = {
        "1": "gpt-4-vision-preview",
        "2": "gpt-4o",
        "3": "gpt-4-turbo"
    }
    
    model = models.get(model_choice, "gpt-4-vision-preview")
    
    # 可选: 自定义base_url
    print()
    base_url = input("自定义Base URL (可选，直接回车跳过): ").strip()
    
    config = {
        "openai_api_key": api_key,
        "model": model
    }
    
    if base_url:
        config["openai_base_url"] = base_url
    
    return config


def configure_qwen():
    """配置通义千问"""
    print("通义千问配置:")
    print("获取API Key: https://dashscope.console.aliyun.com/")
    print()
    
    api_key = input("API Key: ").strip()
    if not api_key:
        print("❌ API Key不能为空")
        sys.exit(1)
    
    print()
    print("选择模型:")
    print("  1. qwen-vl-max (推荐，最强视觉理解)")
    print("  2. qwen-vl-plus (平衡)")
    
    model_choice = input("选择 (1-2) [1]: ").strip() or "1"
    
    models = {
        "1": "qwen-vl-max",
        "2": "qwen-vl-plus"
    }
    
    model = models.get(model_choice, "qwen-vl-max")
    
    return {
        "qwen_api_key": api_key,
        "model": model
    }


def configure_ernie():
    """配置文心一言"""
    print("文心一言配置:")
    print("获取API Key: https://console.bce.baidu.com/qianfan/ais/console/applicationConsole/application")
    print()
    
    api_key = input("API Key: ").strip()
    if not api_key:
        print("❌ API Key不能为空")
        sys.exit(1)
    
    secret_key = input("Secret Key: ").strip()
    if not secret_key:
        print("❌ Secret Key不能为空")
        sys.exit(1)
    
    print()
    print("选择模型:")
    print("  1. ernie-bot-4 (推荐)")
    print("  2. ernie-bot-turbo (更快)")
    
    model_choice = input("选择 (1-2) [1]: ").strip() or "1"
    
    models = {
        "1": "ernie-bot-4",
        "2": "ernie-bot-turbo"
    }
    
    model = models.get(model_choice, "ernie-bot-4")
    
    return {
        "ernie_api_key": api_key,
        "ernie_secret_key": secret_key,
        "model": model
    }


def configure_glm():
    """配置智谱GLM"""
    print("智谱GLM配置:")
    print("获取API Key: https://open.bigmodel.cn/")
    print()
    
    api_key = input("API Key: ").strip()
    if not api_key:
        print("❌ API Key不能为空")
        sys.exit(1)
    
    print()
    print("选择模型:")
    print("  1. glm-4.1v-thinking-flash (推荐，最新思维链模型)")
    print("  2. glm-4v (经典视觉模型)")
    print("  3. glm-4v-plus (增强版)")
    print("  4. glm-4 (纯文本)")
    
    model_choice = input("选择 (1-4) [1]: ").strip() or "1"
    
    models = {
        "1": "glm-4.1v-thinking-flash",
        "2": "glm-4v",
        "3": "glm-4v-plus",
        "4": "glm-4"
    }
    
    model = models.get(model_choice, "glm-4.1v-thinking-flash")
    
    return {
        "glm_api_key": api_key,
        "model": model
    }


def configure_doubao():
    """配置字节跳动豆包"""
    print("豆包配置:")
    print("获取API Key: https://console.volcengine.com/ark/")
    print()
    
    api_key = input("API Key (ark-...): ").strip()
    if not api_key:
        print("❌ API Key不能为空")
        sys.exit(1)
    
    print()
    print("选择模型:")
    print("  1. doubao-vision-pro (独立视觉模型，按量付费)")
    print("  2. doubao-vision-lite (独立视觉模型，轻量版，按量付费)")
    print("  3. doubao-4-vision (独立视觉模型，旗舰版，按量付费)")
    print("  4. doubao-seed-2.0-code (⭐ Coding Plan 订阅包含，编程优化，支持视觉)")
    print("  5. doubao-seed-2.0-pro (Coding Plan 订阅包含，全能模型，支持视觉)")
    
    model_choice = input("选择 (1-5) [4]: ").strip() or "4"
    
    models = {
        "1": "doubao-vision-pro",
        "2": "doubao-vision-lite",
        "3": "doubao-4-vision",
        "4": "doubao-seed-2.0-code",
        "5": "doubao-seed-2.0-pro"
    }
    
    model = models.get(model_choice, "doubao-seed-2.0-code")
    
    print()
    base_url = input("自定义Base URL (可选，直接回车跳过): ").strip()
    
    config = {
        "doubao_api_key": api_key,
        "model": model
    }
    
    if base_url:
        config["doubao_base_url"] = base_url
    
    return config


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n已取消")
        sys.exit(0)
