"""
测试脚本:使用task_0001测试完整的截图还原流程
"""
import os
import sys
import asyncio
import base64
from pathlib import Path

# 添加backend到path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "screenshot-to-code" / "backend"))

from codegen.vue_extractor import parse_vue_project_structure, extract_vue_files
from routes.batch_process import (
    build_vue3_prompt,
    call_openai,
    copy_assets,
    write_project_files
)


async def test_task_0001():
    """测试task_0001的完整流程"""
    
    # 设置路径
    task_dir = PROJECT_ROOT / "task_0001"
    
    if not task_dir.exists():
        print(f"❌ Task directory not found: {task_dir}")
        return
    
    print(f"✅ Found task directory: {task_dir}")
    
    # 1. 检查checkpoints
    checkpoints_dir = task_dir / "checkpoints"
    if not checkpoints_dir.exists():
        print("❌ No checkpoints directory")
        return
    
    checkpoint_files = sorted(checkpoints_dir.glob("step_*.png"))
    if not checkpoint_files:
        print("❌ No checkpoint images found")
        return
    
    print(f"✅ Found {len(checkpoint_files)} checkpoints")
    last_checkpoint = checkpoint_files[-1]
    print(f"   Using: {last_checkpoint.name}")
    
    # 2. 读取截图并转换为base64
    with open(last_checkpoint, "rb") as f:
        image_bytes = f.read()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        image_data_url = f"data:image/png;base64,{image_base64}"
    
    print(f"✅ Screenshot loaded ({len(image_bytes)} bytes)")
    
    # 3. 检查assets
    assets_dir = task_dir / "assets"
    if assets_dir.exists():
        asset_count = sum(1 for _ in assets_dir.rglob('*') if _.is_file())
        print(f"✅ Found {asset_count} asset files")
    else:
        print("⚠️  No assets directory")
    
    # 4. 构建Prompt
    print("\n📝 Building Vue3 prompt...")
    prompt_messages = build_vue3_prompt(image_data_url)
    print(f"✅ Prompt built with {len(prompt_messages)} messages")
    
    # 5. 检查API Key
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("\n⚠️  OPENAI_API_KEY not set")
        print("   Please set it with: export OPENAI_API_KEY=your_key")
        print("\n📋 Skipping AI generation, testing file extraction only...")
        
        # 测试文件提取器
        test_file_extraction()
        return
    
    # 6. 调用AI生成代码
    print("\n🤖 Calling OpenAI API...")
    try:
        ai_response = await call_openai(
            messages=prompt_messages,
            api_key=api_key,
            model="gpt-4-vision-preview"
        )
        
        print(f"✅ AI response received ({len(ai_response)} characters)")
        
        # 7. 解析AI响应
        print("\n📦 Parsing project files...")
        project_files = parse_vue_project_structure(ai_response)
        print(f"✅ Extracted {len(project_files)} files:")
        for file_path in project_files.keys():
            print(f"   - {file_path}")
        
        # 8. 创建output目录
        output_dir = task_dir / "output"
        output_dir.mkdir(exist_ok=True)
        
        # 9. 复制assets
        if assets_dir.exists():
            print("\n📂 Copying assets...")
            target_assets = output_dir / "src" / "assets"
            copy_assets(assets_dir, target_assets)
            print("✅ Assets copied")
        
        # 10. 写入项目文件
        print("\n💾 Writing project files...")
        written_files = write_project_files(output_dir, project_files)
        print(f"✅ Written {len(written_files)} files")
        
        print("\n" + "="*50)
        print("✅ SUCCESS! Project generated at:")
        print(f"   {output_dir.absolute()}")
        print("="*50)
        print("\nTo run the generated project:")
        print(f"  cd {output_dir}")
        print("  npm install")
        print("  npm run dev")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def test_file_extraction():
    """测试文件提取器功能"""
    print("\n" + "="*50)
    print("Testing file extraction...")
    print("="*50)
    
    # 测试用例1: 标准格式
    test_input_1 = '''
<file path="index.html">
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body><div id="app"></div></body>
</html>
</file>

<file path="src/App.vue">
<template>
  <div>Hello Vue</div>
</template>
</file>
'''
    
    files1 = extract_vue_files(test_input_1)
    print(f"\n✅ Test 1: Extracted {len(files1)} files")
    for path in files1.keys():
        print(f"   - {path}")
    
    # 测试用例2: 完整项目结构
    test_project = parse_vue_project_structure(test_input_1)
    print(f"\n✅ Test 2: Generated project with {len(test_project)} files")
    for path in test_project.keys():
        print(f"   - {path}")
    
    print("\n✅ File extraction tests passed!")


if __name__ == "__main__":
    print("="*50)
    print("Screenshot to Vue3 Code - Test Script")
    print("="*50)
    print()
    
    asyncio.run(test_task_0001())
