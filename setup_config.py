#!/usr/bin/env python3
"""
快速配置脚本
帮助用户创建config.json文件
"""
import json
import sys
from pathlib import Path


def main():
    print("="*60)
    print("截图还原工具 - 配置向导")
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
    
    # 获取API Key
    print("请输入你的OpenAI API Key:")
    print("(可以从 https://platform.openai.com/api-keys 获取)")
    api_key = input("API Key (sk-...): ").strip()
    
    if not api_key:
        print("❌ API Key不能为空")
        sys.exit(1)
    
    if not api_key.startswith("sk-"):
        print("⚠ 警告: API Key通常以 'sk-' 开头")
        response = input("是否继续? (y/N): ").strip().lower()
        if response != 'y':
            print("已取消")
            return
    
    # 选择模型
    print()
    print("选择AI模型:")
    print("  1. gpt-4-vision-preview (推荐，最准确)")
    print("  2. gpt-4o (更快)")
    print("  3. gpt-4-turbo (平衡)")
    
    model_choice = input("选择 (1-3) [1]: ").strip() or "1"
    
    models = {
        "1": "gpt-4-vision-preview",
        "2": "gpt-4o",
        "3": "gpt-4-turbo"
    }
    
    model = models.get(model_choice, "gpt-4-vision-preview")
    
    # 创建配置
    config = {
        "openai_api_key": api_key,
        "model": model,
        "max_tokens": 4096,
        "temperature": 0.2
    }
    
    # 写入文件
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print()
        print("="*60)
        print("✅ 配置文件创建成功!")
        print("="*60)
        print(f"文件位置: {config_path}")
        print(f"API Key: {api_key[:10]}...")
        print(f"模型: {model}")
        print()
        print("下一步:")
        print("  python check_env.py          # 检查环境")
        print("  python process_single.py task_0001  # 处理task")
        
    except Exception as e:
        print(f"❌ 创建配置文件失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n已取消")
        sys.exit(0)
