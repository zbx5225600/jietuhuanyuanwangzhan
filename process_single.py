#!/usr/bin/env python3
"""
处理单个task目录的简单脚本
用法: python process_single.py task_0001
"""
import os
import sys
import json
import asyncio
from pathlib import Path

# 添加backend到Python路径
backend_path = Path(__file__).parent / "screenshot-to-code" / "backend"
sys.path.insert(0, str(backend_path))

from routes.batch_process import batch_process_task, TaskProcessRequest


def load_config():
    """从配置文件加载配置"""
    config_path = Path(__file__).parent / "config.json"
    
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
        except Exception as e:
            print(f"Warning: Failed to load config.json: {e}")
    
    return {}


async def main():
    # 检查参数
    if len(sys.argv) < 2:
        print("Usage: python process_single.py <task_directory>")
        print("Example: python process_single.py task_0001")
        sys.exit(1)
    
    task_name = sys.argv[1]
    
    # 加载配置文件
    config = load_config()
    
    # 获取提供商
    provider = config.get("provider", "openai")
    
    # 根据提供商获取API Key
    if provider == "openai":
        api_key = config.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")
    elif provider == "qwen":
        api_key = config.get("qwen_api_key") or os.environ.get("QWEN_API_KEY")
    elif provider == "ernie":
        api_key = config.get("ernie_api_key") or os.environ.get("ERNIE_API_KEY")
    elif provider == "glm":
        api_key = config.get("glm_api_key") or os.environ.get("GLM_API_KEY")
    elif provider == "doubao":
        api_key = config.get("doubao_api_key") or os.environ.get("DOUBAO_API_KEY")
    else:
        api_key = config.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        print(f"Error: API Key for {provider} not found!")
        print("Please either:")
        print("  1. Set it in config.json file")
        print("  2. Run: python setup_config_multi.py")
        sys.exit(1)
    
    # 获取模型配置
    model = config.get("model", "gpt-4-vision-preview")
    min_visual_similarity = float(config.get("min_visual_similarity", 0.90))
    max_restore_attempts = int(config.get("max_restore_attempts", 5))
    secret_key = config.get("ernie_secret_key", "")
    if provider == "doubao":
        base_url = config.get("doubao_base_url", "")
    else:
        base_url = config.get("openai_base_url", "")
    
    # 构建完整路径
    base_dir = Path(__file__).parent
    task_dir = base_dir / task_name
    
    if not task_dir.exists():
        print(f"Error: Task directory not found: {task_dir}")
        sys.exit(1)
    
    print(f"Processing task: {task_name}")
    print(f"Task directory: {task_dir}")
    print(f"Provider: {provider}")
    print(f"Model: {model}")
    print(f"Min visual similarity: {min_visual_similarity:.0%}")
    print(f"Max restore attempts: {max_restore_attempts}")
    print(f"API Key: {api_key[:10]}...")
    print()
    
    # 创建请求
    request = TaskProcessRequest(
        task_dir=str(task_dir),
        api_key=api_key,
        model=model,
        provider=provider,
        secret_key=secret_key,
        base_url=base_url,
        min_visual_similarity=min_visual_similarity,
        max_restore_attempts=max_restore_attempts
    )
    
    try:
        # 处理task
        result = await batch_process_task(request)
        
        print(f"\n✅ Success!")
        print(f"Output directory: {result.output_dir}")
        print(f"\nGenerated files ({len(result.files_generated)}):")
        for file in result.files_generated:
            print(f"  ✓ {file}")
        
        print(f"\nTo run the generated project:")
        print(f"  cd {result.output_dir}")
        print(f"  npm install")
        print(f"  npm run dev")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
