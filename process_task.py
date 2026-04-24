#!/usr/bin/env python3
"""
批量处理task目录的脚本
从截图生成Vue3+Vite项目
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


async def process_single_task(
    task_dir: str,
    api_key: str,
    model: str = "gpt-4-vision-preview",
    min_visual_similarity: float = 0.90,
    max_restore_attempts: int = 5
):
    """处理单个task"""
    print(f"\n{'='*60}")
    print(f"Processing: {task_dir}")
    print(f"{'='*60}\n")
    
    request = TaskProcessRequest(
        task_dir=task_dir,
        api_key=api_key,
        model=model,
        min_visual_similarity=min_visual_similarity,
        max_restore_attempts=max_restore_attempts
    )
    
    try:
        result = await batch_process_task(request)
        
        print(f"\n✅ Success!")
        print(f"Output directory: {result.output_dir}")
        print(f"Files generated: {len(result.files_generated)}")
        for file in result.files_generated:
            print(f"  - {file}")
        
        return True
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def process_all_tasks(
    base_dir: str,
    api_key: str,
    model: str = "gpt-4-vision-preview",
    min_visual_similarity: float = 0.90,
    max_restore_attempts: int = 5
):
    """处理所有task目录"""
    base_path = Path(base_dir)
    
    # 查找所有task_XXXX目录
    task_dirs = sorted([
        d for d in base_path.iterdir()
        if d.is_dir() and d.name.startswith("task_")
    ])
    
    if not task_dirs:
        print("No task directories found!")
        return
    
    print(f"Found {len(task_dirs)} task directories")
    
    results = []
    for task_dir in task_dirs:
        success = await process_single_task(
            str(task_dir),
            api_key,
            model,
            min_visual_similarity,
            max_restore_attempts
        )
        results.append({
            "task": task_dir.name,
            "success": success
        })
    
    # 打印总结
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    
    success_count = sum(1 for r in results if r["success"])
    print(f"Total: {len(results)}")
    print(f"Success: {success_count}")
    print(f"Failed: {len(results) - success_count}")
    
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['task']}")


def main():
    """主函数"""
    # 加载配置文件
    config = load_config()
    
    # 获取API Key (优先级: 配置文件 > 环境变量)
    api_key = config.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        print("Error: OPENAI_API_KEY not found!")
        print("Please either:")
        print("  1. Set it in config.json file")
        print("  2. Set environment variable: export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)
    
    # 获取模型配置
    model = config.get("model", "gpt-4-vision-preview")
    min_visual_similarity = float(config.get("min_visual_similarity", 0.90))
    max_restore_attempts = int(config.get("max_restore_attempts", 5))
    
    # 获取基础目录
    if len(sys.argv) > 1:
        base_dir = sys.argv[1]
    else:
        base_dir = Path(__file__).parent
    
    print(f"Base directory: {base_dir}")
    print(f"Model: {model}")
    print(f"Min visual similarity: {min_visual_similarity:.0%}")
    print(f"Max restore attempts: {max_restore_attempts}")
    print(f"API Key: {api_key[:10]}...")
    
    # 运行处理
    asyncio.run(
        process_all_tasks(
            base_dir,
            api_key,
            model,
            min_visual_similarity,
            max_restore_attempts
        )
    )


if __name__ == "__main__":
    main()
