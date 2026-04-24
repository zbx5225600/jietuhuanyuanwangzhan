"""
测试文件提取器和项目生成功能(不需要API Key)
"""
import sys
import os
from pathlib import Path

# 添加backend到path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "screenshot-to-code" / "backend"))

from codegen.vue_extractor import (
    extract_vue_files,
    parse_vue_project_structure,
    convert_html_to_vue,
    ensure_config_files
)
from routes.batch_process import write_project_files


def test_extract_vue_files():
    """测试Vue文件提取"""
    print("\n" + "="*60)
    print("测试 1: Vue文件提取功能")
    print("="*60)
    
    # 测试用例: 标准多文件格式
    test_input = '''
Here is the Vue3 project:

<file path="index.html">
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Test App</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
</file>

<file path="package.json">
{
  "name": "test-app",
  "version": "1.0.0"
}
</file>

<file path="src/App.vue">
<template>
  <div class="app">
    <h1>Hello Vue 3</h1>
    <p>This is a test app</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
const message = ref('Hello')
</script>

<style scoped>
.app {
  text-align: center;
  padding: 20px;
}
</style>
</file>
'''
    
    files = extract_vue_files(test_input)
    
    print(f"\n✅ 提取到 {len(files)} 个文件:")
    for path, content in files.items():
        print(f"\n📄 {path} ({len(content)} 字符)")
        # 显示前100个字符
        preview = content[:100].replace('\n', ' ')
        print(f"   {preview}...")
    
    assert len(files) == 3, f"期望3个文件,实际{len(files)}个"
    assert 'index.html' in files, "缺少index.html"
    assert 'package.json' in files, "缺少package.json"
    assert 'src/App.vue' in files, "缺少src/App.vue"
    
    print("\n✅ 测试通过!")
    return True


def test_parse_project_structure():
    """测试项目结构解析"""
    print("\n" + "="*60)
    print("测试 2: 项目结构解析")
    print("="*60)
    
    # 测试用例: 单个HTML文件
    html_input = '''
<!DOCTYPE html>
<html>
<head>
  <title>Test</title>
  <style>
    body { margin: 0; padding: 20px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Hello World</h1>
  </div>
</body>
</html>
'''
    
    project = parse_vue_project_structure(html_input)
    
    print(f"\n✅ 生成项目包含 {len(project)} 个文件:")
    for path in project.keys():
        print(f"   📄 {path}")
    
    # 验证必需文件
    required_files = [
        'index.html',
        'package.json',
        'vite.config.ts',
        'tsconfig.json',
        'tsconfig.node.json',
        'src/main.ts',
        'src/App.vue'
    ]
    
    for file_path in required_files:
        assert file_path in project, f"缺少必需文件: {file_path}"
        print(f"   ✅ {file_path} 存在")
    
    print("\n✅ 测试通过!")
    return True


def test_convert_html_to_vue():
    """测试HTML转Vue组件"""
    print("\n" + "="*60)
    print("测试 3: HTML转Vue组件")
    print("="*60)
    
    html = '''
<!DOCTYPE html>
<html>
<head>
  <style>
    .container { max-width: 1200px; margin: 0 auto; }
    h1 { color: #333; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Test Page</h1>
    <p>This is a test</p>
  </div>
  <script>
    console.log('Hello')
  </script>
</body>
</html>
'''
    
    vue_sfc = convert_html_to_vue(html)
    
    print("\n✅ 转换结果:")
    print("-" * 60)
    print(vue_sfc)
    print("-" * 60)
    
    # 验证包含必要的部分
    assert '<template>' in vue_sfc, "缺少template"
    assert '<script' in vue_sfc, "缺少script"
    assert '<style' in vue_sfc, "缺少style"
    
    print("\n✅ 测试通过!")
    return True


def test_write_project_files():
    """测试项目文件写入"""
    print("\n" + "="*60)
    print("测试 4: 项目文件写入")
    print("="*60)
    
    # 创建测试项目
    test_project = {
        'index.html': '<!DOCTYPE html><html><body><div id="app"></div></body></html>',
        'package.json': '{"name": "test"}',
        'src/main.ts': "import { createApp } from 'vue'\nimport App from './App.vue'\ncreateApp(App).mount('#app')",
        'src/App.vue': '<template><div>Test</div></template>',
        'src/components/Test.vue': '<template><div>Component</div></template>'
    }
    
    # 写入到测试目录
    test_output = PROJECT_ROOT / "test_output"
    test_output.mkdir(exist_ok=True)
    
    print(f"\n📂 写入测试目录: {test_output.absolute()}")
    
    written_files = write_project_files(test_output, test_project)
    
    print(f"\n✅ 写入 {len(written_files)} 个文件:")
    for file_path in written_files:
        full_path = test_output / file_path
        exists = full_path.exists()
        size = full_path.stat().st_size if exists else 0
        print(f"   {'✅' if exists else '❌'} {file_path} ({size} bytes)")
        assert exists, f"文件未创建: {file_path}"
    
    print("\n✅ 测试通过!")
    
    # 清理测试目录
    import shutil
    shutil.rmtree(test_output)
    print(f"🧹 已清理测试目录")
    
    return True


def test_complete_flow():
    """测试完整流程"""
    print("\n" + "="*60)
    print("测试 5: 完整流程 (task_0001)")
    print("="*60)
    
    task_dir = Path("task_0001")
    
    if not task_dir.exists():
        print(f"❌ Task目录不存在: {task_dir}")
        return False
    
    print(f"✅ 找到task目录: {task_dir.absolute()}")
    
    # 检查checkpoints
    checkpoints = sorted(task_dir.glob("checkpoints/step_*.png"))
    if not checkpoints:
        print("❌ 没有checkpoint文件")
        return False
    
    print(f"✅ 找到 {len(checkpoints)} 个checkpoint:")
    for cp in checkpoints:
        size_kb = cp.stat().st_size / 1024
        print(f"   📷 {cp.name} ({size_kb:.1f} KB)")
    
    # 检查assets
    assets_dir = task_dir / "assets"
    if assets_dir.exists():
        asset_count = sum(1 for _ in assets_dir.rglob('*') if _.is_file())
        print(f"\n✅ 资源文件: {asset_count} 个")
    else:
        print("\n⚠️  没有assets目录")
    
    # 检查output
    output_dir = task_dir / "output"
    if output_dir.exists():
        output_files = list(output_dir.rglob('*'))
        print(f"\n📂 output目录: {len(output_files)} 个文件/目录")
    else:
        print("\n📂 output目录: 不存在 (将在首次生成时创建)")
    
    print("\n✅ 测试通过!")
    return True


def main():
    """运行所有测试"""
    print("="*60)
    print("截图还原工具 - 功能测试")
    print("="*60)
    
    tests = [
        ("Vue文件提取", test_extract_vue_files),
        ("项目结构解析", test_parse_project_structure),
        ("HTML转Vue组件", test_convert_html_to_vue),
        ("项目文件写入", test_write_project_files),
        ("完整流程检查", test_complete_flow),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, True, None))
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 打印测试总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for name, success, error in results:
        status = "✅ 通过" if success else f"❌ 失败: {error}"
        print(f"{status} - {name}")
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过!")
        print("\n下一步:")
        print("1. 设置OpenAI API Key: export OPENAI_API_KEY=sk-xxx")
        print("2. 启动后端: cd screenshot-to-code/backend && python main.py")
        print("3. 使用API或前端界面生成Vue3项目")
    else:
        print("\n⚠️  部分测试失败,请检查错误信息")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
