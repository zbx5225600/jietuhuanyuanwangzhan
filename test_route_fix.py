#!/usr/bin/env python3
"""
测试路由路径修复功能
"""
from pathlib import Path
import sys
import re

# 添加 backend 到 Python 路径
backend_path = Path(__file__).parent / "screenshot-to-code" / "backend"
sys.path.insert(0, str(backend_path))

# 模拟测试我们的修复逻辑
output_dir = Path(__file__).parent / "task_0001" / "output"

print("=" * 60)
print("Testing route path fix logic")
print("=" * 60)

# 模拟路由生成逻辑
views_dir = output_dir / "src" / "views"
if views_dir.exists():
    vue_files = list(views_dir.glob("*.vue"))
    page_names_from_files = [f.stem for f in vue_files]
    print(f"\nPage names from files: {page_names_from_files}")

# 从 Header.vue 中提取路由链接
header_path = output_dir / "src" / "components" / "Header.vue"
path_map = {}

if header_path.exists():
    print(f"\nReading Header.vue from: {header_path}")
    with open(header_path, 'r', encoding='utf-8') as f:
        header_content = f.read()
    
    # 提取所有 router-link 的 to 属性
    router_link_pattern = r'<router-link\s+[^>]*to\s*=\s*["\']([^"\']+)["\']'
    header_paths = re.findall(router_link_pattern, header_content)
    
    print(f"\nFound {len(header_paths)} router-link paths in Header.vue:")
    for path in header_paths:
        print(f"  - {path}")
    
    # 建立页面名称到路径的映射
    for path in header_paths:
        if path == '/':
            path_map['Home'] = '/'
        else:
            # 从路径推导页面名称（去掉 /，然后转成驼峰）
            path_without_slash = path[1:]
            # 转成驼峰命名
            words = path_without_slash.split('-')
            page_name_candidate = ''.join(word.capitalize() for word in words)
            # 检查这个候选名称是否在页面文件中
            if page_name_candidate in page_names_from_files:
                path_map[page_name_candidate] = path
                print(f"  Mapped: {page_name_candidate} -> {path}")
            else:
                # 如果不在，也可以尝试用首字母大写的单字
                single_word_name = path_without_slash.capitalize()
                if single_word_name in page_names_from_files:
                    path_map[single_word_name] = path
                    print(f"  Mapped: {single_word_name} -> {path}")

print(f"\nPath map: {path_map}")

# 测试驼峰到连字符的转换
print("\nTesting camelCase to hyphen conversion:")
test_cases = ["PrintsAndBooks", "Contact", "Lightroom", "Photos"]
for test in test_cases:
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', test)
    hyphenated = re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1).lower()
    print(f"  {test} -> {hyphenated}")

print("\n" + "=" * 60)
print("✅ Test completed successfully!")
print("=" * 60)