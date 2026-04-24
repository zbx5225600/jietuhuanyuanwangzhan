"""
Vue3+Vite多文件提取器
从AI响应中提取多个文件(Vue SFC格式)
"""
import re
from typing import Dict, List, Tuple


def extract_vue_files(text: str) -> Dict[str, str]:
    """
    从AI响应中提取多个文件
    支持格式: <file path="src/App.vue">...</file>
    
    Returns:
        Dict[file_path, file_content]
    """
    files = {}
    
    # 匹配 <file path="...">...</file> 格式
    file_pattern = r'<file\s+path="([^"]+)">\s*(.*?)\s*</file>'
    matches = re.finditer(file_pattern, text, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        file_path = match.group(1).strip()
        file_content = match.group(2).strip()
        # 全面反转义 HTML 实体（先处理双重转义）
        file_content = file_content.replace('&amp;lt;', '<').replace('&amp;gt;', '>')
        file_content = file_content.replace('&lt;', '<').replace('&gt;', '>')
        file_content = file_content.replace('&amp;', '&')
        files[file_path] = file_content
    
    # 如果没有找到file标签,尝试提取单个HTML文件
    if not files:
        html_match = re.search(
            r'(<html.*?>.*?</html>)',
            text,
            re.DOTALL | re.IGNORECASE
        )
        if html_match:
            files['index.html'] = html_match.group(1)
    
    return files


def extract_vue_sfc_components(text: str) -> Dict[str, str]:
    """
    提取Vue单文件组件(SFC)
    支持从markdown代码块中提取
    """
    components = {}
    
    # 匹配markdown代码块中的Vue组件
    vue_pattern = r'```vue\s*\n(.*?)\n```'
    matches = re.finditer(vue_pattern, text, re.DOTALL)
    
    for idx, match in enumerate(matches):
        component_content = match.group(1).strip()
        # 尝试从组件中提取name
        name_match = re.search(r'name:\s*[\'"]([^\'"]+)[\'"]', component_content)
        if name_match:
            component_name = name_match.group(1)
            components[f'src/components/{component_name}.vue'] = component_content
        else:
            components[f'src/components/Component{idx}.vue'] = component_content
    
    return components


def parse_vue_project_structure(
    ai_response: str,
    screenshot_base64: str = None
) -> Dict[str, str]:
    """
    解析AI响应,生成完整的Vue3+Vite项目结构
    
    Args:
        ai_response: AI的完整响应文本
        screenshot_base64: 截图的base64编码(可选)
    
    Returns:
        Dict[file_path, file_content] 完整的项目文件映射
    """
    project_files = {}
    
    # 1. 提取AI生成的文件
    extracted_files = extract_vue_files(ai_response)
    project_files.update(extracted_files)
    
    # 2. 如果没有提取到文件,生成默认结构
    if not project_files:
        project_files = generate_default_vue_project(ai_response)
    
    # 3. 确保包含必要的配置文件
    project_files = ensure_config_files(project_files)
    
    return project_files


def generate_default_vue_project(html_content: str) -> Dict[str, str]:
    """
    从HTML内容生成默认Vue3项目结构
    """
    files = {}
    
    # 生成index.html
    files['index.html'] = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Vue3 App</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
"""
    
    # 生成main.ts
    files['src/main.ts'] = """import { createApp } from 'vue'
import App from './App.vue'

createApp(App).mount('#app')
"""
    
    # 生成vite.config.ts
    files['vite.config.ts'] = """import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
})
"""
    
    # 生成tsconfig.json
    files['tsconfig.json'] = """{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src/**/*.ts", "src/**/*.d.ts", "src/**/*.tsx", "src/**/*.vue"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
"""
    
    files['tsconfig.node.json'] = """{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
"""
    
    # 生成package.json
    files['package.json'] = """{
  "name": "vue3-restored-app",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "typescript": "^5.2.0",
    "vite": "^5.0.0",
    "vue-tsc": "^1.8.0"
  }
}
"""
    
    # 生成App.vue (从HTML转换)
    app_vue = convert_html_to_vue(html_content)
    files['src/App.vue'] = app_vue
    
    return files


def convert_html_to_vue(html_content: str) -> str:
    """
    将HTML内容转换为Vue单文件组件
    """
    # 提取body内容
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL)
    body_content = body_match.group(1).strip() if body_match else html_content
    
    # 提取style标签
    style_match = re.search(r'<style[^>]*>(.*?)</style>', html_content, re.DOTALL)
    style_content = style_match.group(1).strip() if style_match else ''
    
    # 提取script标签
    script_match = re.search(r'<script[^>]*>(.*?)</script>', html_content, re.DOTALL)
    script_content = script_match.group(1).strip() if script_match else ''
    
    # 移除style和script从template中
    template_content = html_content
    if style_match:
        template_content = template_content.replace(style_match.group(0), '')
    if script_match:
        template_content = template_content.replace(script_match.group(0), '')
    
    # 清理HTML标签外的内容
    template_match = re.search(r'<html[^>]*>(.*?)</html>', template_content, re.DOTALL)
    if template_match:
        template_content = template_match.group(1)
    
    # 构建Vue SFC
    vue_sfc = '<template>\n'
    
    # 如果body内容包含在div中,直接使用
    if body_content.strip().startswith('<div'):
        vue_sfc += body_content.strip() + '\n'
    else:
        vue_sfc += '  <div>\n' + body_content.strip() + '\n  </div>\n'
    
    vue_sfc += '</template>\n\n'
    
    if script_content:
        vue_sfc += '<script setup lang="ts">\n' + script_content + '\n</script>\n\n'
    else:
        vue_sfc += '<script setup lang="ts">\n// Add your logic here\n</script>\n\n'
    
    if style_content:
        vue_sfc += '<style scoped>\n' + style_content + '\n</style>\n'
    else:
        vue_sfc += '<style scoped>\n/* Add your styles here */\n</style>\n'
    
    return vue_sfc


def ensure_config_files(files: Dict[str, str]) -> Dict[str, str]:
    """
    确保项目包含所有必要的配置文件
    """
    required_files = {
        'index.html': """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Vue3 App</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
""",
        'package.json': """{
  "name": "vue3-restored-app",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "typescript": "^5.2.0",
    "vite": "^5.0.0",
    "vue-tsc": "^1.8.0"
  }
}
""",
        'vite.config.ts': """import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
})
""",
        'tsconfig.json': """{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src/**/*.ts", "src/**/*.d.ts", "src/**/*.tsx", "src/**/*.vue"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
""",
        'tsconfig.node.json': """{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
""",
        'src/main.ts': """import { createApp } from 'vue'
import App from './App.vue'

createApp(App).mount('#app')
"""
    }
    
    # 只添加缺失的文件
    for file_path, content in required_files.items():
        if file_path not in files:
            files[file_path] = content
    
    return files
