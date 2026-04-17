#!/usr/bin/env python3
"""
环境检查脚本
检查所有必要的依赖和配置
"""
import os
import sys
from pathlib import Path


def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    print(f"Python版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 10:
        print("  ✅ Python版本符合要求 (>= 3.10)")
        return True
    else:
        print("  ❌ Python版本过低，需要 >= 3.10")
        return False


def check_dependencies():
    """检查Python依赖"""
    required = [
        "fastapi",
        "uvicorn",
        "openai",
        "dotenv",
    ]
    
    print("\nPython依赖检查:")
    all_ok = True
    
    for package in required:
        try:
            if package == "dotenv":
                __import__("dotenv")
            else:
                __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (未安装)")
            all_ok = False
    
    return all_ok


def check_api_key():
    """检查API Key"""
    print("\nAPI Key检查:")
    
    # 检查配置文件
    config_path = Path(__file__).parent / "config.json"
    config_api_key = None
    
    if config_path.exists():
        try:
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                config_api_key = config.get("openai_api_key")
        except Exception as e:
            print(f"  ⚠ config.json读取失败: {e}")
    
    # 检查环境变量
    env_api_key = os.environ.get("OPENAI_API_KEY")
    
    # 判断结果
    if config_api_key and config_api_key != "your-api-key-here":
        print(f"  ✅ config.json中已设置: {config_api_key[:10]}...")
        return True
    elif env_api_key:
        print(f"  ✅ 环境变量中已设置: {env_api_key[:10]}...")
        return True
    else:
        print("  ❌ OPENAI_API_KEY未设置")
        print("     请选择以下方式之一:")
        print("     1. 在config.json中设置 (推荐)")
        print("     2. 设置环境变量:")
        print("        Windows: $env:OPENAI_API_KEY='your-key'")
        print("        Linux/Mac: export OPENAI_API_KEY='your-key'")
        return False


def check_project_structure():
    """检查项目结构"""
    print("\n项目结构检查:")
    base_dir = Path(__file__).parent
    
    required_paths = [
        "screenshot-to-code/backend",
        "screenshot-to-code/backend/routes/batch_process.py",
        "screenshot-to-code/backend/codegen/vue_extractor.py",
        "task_0001",
        "task_0001/checkpoints",
    ]
    
    all_ok = True
    for path in required_paths:
        full_path = base_dir / path
        if full_path.exists():
            print(f"  ✅ {path}")
        else:
            print(f"  ❌ {path} (不存在)")
            all_ok = False
    
    return all_ok


def check_task_data():
    """检查task数据"""
    print("\nTask数据检查:")
    base_dir = Path(__file__).parent
    
    # 查找所有task目录
    task_dirs = sorted([
        d for d in base_dir.iterdir()
        if d.is_dir() and d.name.startswith("task_")
    ])
    
    if not task_dirs:
        print("  ❌ 未找到task目录")
        return False
    
    print(f"  找到 {len(task_dirs)} 个task目录:")
    
    for task_dir in task_dirs:
        checkpoints = task_dir / "checkpoints"
        if checkpoints.exists():
            checkpoint_files = list(checkpoints.glob("step_*.png"))
            print(f"    ✅ {task_dir.name} ({len(checkpoint_files)} 张截图)")
        else:
            print(f"    ❌ {task_dir.name} (无checkpoints)")
    
    return True


def main():
    """主函数"""
    print("="*60)
    print("环境检查")
    print("="*60)
    
    checks = [
        ("Python版本", check_python_version()),
        ("Python依赖", check_dependencies()),
        ("API Key", check_api_key()),
        ("项目结构", check_project_structure()),
        ("Task数据", check_task_data()),
    ]
    
    print("\n" + "="*60)
    print("检查结果")
    print("="*60)
    
    for name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    all_passed = all(result for _, result in checks)
    
    if all_passed:
        print("\n✅ 所有检查通过！可以开始使用。")
        print("\n下一步:")
        print("  python process_single.py task_0001")
    else:
        print("\n❌ 部分检查未通过，请先解决上述问题。")
        print("\n安装依赖:")
        print("  pip install fastapi uvicorn openai python-dotenv aiofiles")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
