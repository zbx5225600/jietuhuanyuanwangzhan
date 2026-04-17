#!/usr/bin/env python3
"""
修复版脚本：确保生成足够的路由
"""
import json
import base64
import shutil
from pathlib import Path
import sys
import asyncio

# 添加backend到Python路径
backend_path = Path(__file__).parent / "screenshot-to-code" / "backend"
sys.path.insert(0, str(backend_path))

from codegen.vue_extractor import parse_vue_project_structure
from llm_adapters import create_adapter


def build_vue3_prompt(image_data_urls):
    num_pages = len(image_data_urls)
    page_names = ["Home", "Photos", "About", "Lightroom", "Contact"][:num_pages]
    page_paths = ["/", "/photos", "/about", "/lightroom", "/contact"][:num_pages]
    
    pages_description = []
    for i in range(num_pages):
        pages_description.append("- Screenshot %d: %s page (%s)" % (i+1, page_names[i], page_paths[i]))
    pages_description_str = "\n".join(pages_description)
    
    page_components_list = []
    for i in range(num_pages):
        page_components_list.append("- src/views/%s.vue" % page_names[i])
    page_components_str = "\n".join(page_components_list)
    
    page_routes_list = []
    for i in range(num_pages):
        page_routes_list.append("- %s -&gt; %s" % (page_paths[i], page_names[i]))
    page_routes_str = "\n".join(page_routes_list)
    
    system_prompt = "You are an expert frontend developer specializing in Vue 3 and Vite.\n\n"
    system_prompt += "Your task is to recreate a website from multiple screenshots as a Vue 3 + Vite project with Vue Router.\n\n"
    system_prompt += "# Multi-Page App - IMPORTANT!\n\n"
    system_prompt += "- There are %d screenshots, each representing a different page of the website\n" % num_pages
    system_prompt += "- Use Vue Router to implement page navigation between these %d pages\n" % num_pages
    system_prompt += pages_description_str + "\n\n"
    system_prompt += "# Output Format\n\n"
    system_prompt += "You MUST output multiple files using the following format:\n\n"
    system_prompt += "&lt;file path=\"index.html\"&gt;\n&lt;!DOCTYPE html&gt;\n&lt;html lang=\"en\"&gt;\n  &lt;head&gt;\n    &lt;meta charset=\"UTF-8\" /&gt;\n    &lt;meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" /&gt;\n    &lt;title&gt;App&lt;/title&gt;\n  &lt;/head&gt;\n  &lt;body&gt;\n    &lt;div id=\"app\"&gt;&lt;/div&gt;\n    &lt;script type=\"module\" src=\"/src/main.ts\"&gt;&lt;/script&gt;\n  &lt;/body&gt;\n&lt;/html&gt;\n&lt;/file&gt;\n\n"
    system_prompt += "&lt;file path=\"package.json\"&gt;\n{\n  \"name\": \"vue3-app\",\n  \"private\": true,\n  \"version\": \"0.0.0\",\n  \"type\": \"module\",\n  \"scripts\": {\n    \"dev\": \"vite\",\n    \"build\": \"vue-tsc &amp;&amp; vite build\",\n    \"preview\": \"vite preview\"\n  },\n  \"dependencies\": {\n    \"vue\": \"^3.4.0\",\n    \"vue-router\": \"^4.2.0\"\n  },\n  \"devDependencies\": {\n    \"@vitejs/plugin-vue\": \"^5.0.0\",\n    \"typescript\": \"^5.2.0\",\n    \"vite\": \"^5.0.0\",\n    \"vue-tsc\": \"^1.8.0\"\n  }\n}\n&lt;/file&gt;\n\n"
    system_prompt += "&lt;file path=\"vite.config.ts\"&gt;\nimport { defineConfig } from 'vite'\nimport vue from '@vitejs/plugin-vue'\n\nexport default defineConfig({\n  plugins: [vue()],\n})\n&lt;/file&gt;\n\n"
    system_prompt += "&lt;file path=\"tsconfig.json\"&gt;\n{\n  \"compilerOptions\": {\n    \"target\": \"ES2020\",\n    \"useDefineForClassFields\": true,\n    \"module\": \"ESNext\",\n    \"lib\": [\"ES2020\", \"DOM\", \"DOM.Iterable\"],\n    \"skipLibCheck\": true,\n    \"moduleResolution\": \"bundler\",\n    \"allowImportingTsExtensions\": true,\n    \"resolveJsonModule\": true,\n    \"isolatedModules\": true,\n    \"noEmit\": true,\n    \"jsx\": \"preserve\",\n    \"strict\": true,\n    \"noUnusedLocals\": true,\n    \"noUnusedParameters\": true,\n    \"noFallthroughCasesInSwitch\": true\n  },\n  \"include\": [\"src/**/*.ts\", \"src/**/*.tsx\", \"src/**/*.vue\"],\n  \"references\": [{ \"path\": \"./tsconfig.node.json\" }]\n}\n&lt;/file&gt;\n\n"
    system_prompt += "&lt;file path=\"tsconfig.node.json\"&gt;\n{\n  \"compilerOptions\": {\n    \"composite\": true,\n    \"skipLibCheck\": true,\n    \"module\": \"ESNext\",\n    \"moduleResolution\": \"bundler\",\n    \"allowSyntheticDefaultImports\": true\n  },\n  \"include\": [\"vite.config.ts\"]\n}\n&lt;/file&gt;\n\n"
    system_prompt += "&lt;file path=\"src/main.ts\"&gt;\nimport { createApp } from 'vue'\nimport App from './App.vue'\nimport router from './router'\n\ncreateApp(App).use(router).mount('#app')\n&lt;/file&gt;\n\n"
    system_prompt += "&lt;file path=\"src/router/index.ts\"&gt;\nimport { createRouter, createWebHistory } from 'vue-router'\nimport Home from '../views/Home.vue'\n\nconst routes = [\n  {\n    path: '/',\n    name: 'Home',\n    component: Home\n  }\n]\n\nconst router = createRouter({\n  history: createWebHistory(),\n  routes\n})\n\nexport default router\n&lt;/file&gt;\n\n"
    system_prompt += "&lt;file path=\"src/App.vue\"&gt;\n&lt;script setup lang=\"ts\"&gt;\n&lt;/script&gt;\n\n&lt;template&gt;\n  &lt;div id=\"app\"&gt;\n    &lt;router-view /&gt;\n  &lt;/div&gt;\n&lt;/template&gt;\n\n&lt;style&gt;\n#app {\n  font-family: Avenir, Helvetica, Arial, sans-serif;\n  -webkit-font-smoothing: antialiased;\n  -moz-osx-font-smoothing: grayscale;\n}\n&lt;/style&gt;\n&lt;/file&gt;\n\n"
    system_prompt += "&lt;file path=\"src/views/Home.vue\"&gt;\n&lt;script setup lang=\"ts\"&gt;\n&lt;/script&gt;\n\n&lt;template&gt;\n&lt;/template&gt;\n\n&lt;style scoped&gt;\n&lt;/style&gt;\n&lt;/file&gt;\n\n"
    system_prompt += "# Important Guidelines - CRITICAL!\n\n"
    system_prompt += "1. Recreate EACH of the %d pages EXACTLY as shown in its corresponding screenshot\n" % num_pages
    system_prompt += "2. Pay attention to colors, fonts, spacing, layout, and all details on every page\n"
    system_prompt += "3. Write clean, modern Vue 3 code with Composition API\n"
    system_prompt += "4. Use TypeScript for type safety\n"
    system_prompt += "5. Use Vue Router for page navigation - YOU MUST CREATE %d ROUTES!\n" % num_pages
    system_prompt += "6. Create a src/views/ directory for page components - %d page components total!\n" % num_pages
    system_prompt += "7. Create a navigation menu (header) to navigate between all %d pages\n" % num_pages
    system_prompt += "8. Split into multiple .vue components if the UI is complex\n"
    system_prompt += "9. All static assets should be in src/assets/\n"
    system_prompt += "10. Use relative paths for assets: /src/assets/image.png\n\n"
    system_prompt += "# YOU MUST CREATE THESE %d PAGE COMPONENTS:\n" % num_pages
    system_prompt += page_components_str + "\n\n"
    system_prompt += "# AND YOU MUST CONFIGURE THESE %d ROUTES IN src/router/index.ts:\n" % num_pages
    system_prompt += page_routes_str + "\n\n"
    system_prompt += "# Important\n\n"
    system_prompt += "- Output ALL files using the &lt;file path=\"...\"&gt; format shown above\n"
    system_prompt += "- Each file must be wrapped in &lt;file path=\"...\"&gt;...&lt;/file&gt;\n"
    system_prompt += "- Do NOT use markdown code blocks\n"
    system_prompt += "- Make sure the recreated pages look identical to the screenshots\n"
    system_prompt += "- The first screenshot is the Home page (/)\n"
    system_prompt += "- Create additional page components in src/views/ for the other screenshots\n"
    system_prompt += "- DO NOT FORGET TO CREATE ALL %d PAGE COMPONENTS AND ROUTES!\n" % num_pages

    user_prompt = "You have been given multiple screenshots, each representing a different page of the website.\n\n"
    user_prompt += "- Screenshot 1: Home page (/)\n"
    user_prompt += "- Screenshot 2: Second page (e.g., /about or /products)\n"
    user_prompt += "- Screenshot 3: Third page (e.g., /contact or /services)\n"
    user_prompt += "- etc.\n\n"
    user_prompt += "Please recreate the ENTIRE website as a Vue 3 + Vite project with Vue Router.\n\n"
    user_prompt += "Make sure:\n"
    user_prompt += "1. Each screenshot becomes its own page component in src/views/\n"
    user_prompt += "2. Create a router configuration in src/router/index.ts\n"
    user_prompt += "3. Add a navigation menu to switch between pages\n"
    user_prompt += "4. Recreate each page EXACTLY as shown in its screenshot\n"
    user_prompt += "5. Use Vue Router for navigation\n"

    content = []
    for i in range(len(image_data_urls)):
        content.append({
            "type": "image_url",
            "image_url": {
                "url": image_data_urls[i],
                "detail": "high"
            }
        })
    content.append({
        "type": "text",
        "text": user_prompt
    })

    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": content
        }
    ]
    
    return messages


def copy_assets(source_assets_dir, target_assets_dir):
    if not source_assets_dir.exists():
        print(f"Warning: Source assets directory not found: {source_assets_dir}")
        return
    
    try:
        target_assets_dir.mkdir(parents=True, exist_ok=True)
        print(f"Target assets directory created: {target_assets_dir}")
        
        for item in source_assets_dir.rglob('*'):
            if item.is_file():
                try:
                    print(f"Found asset file: {item}")
                    rel_path = item.relative_to(source_assets_dir)
                    
                    if len(str(target_assets_dir / rel_path)) &gt; 255:
                        import hashlib
                        hash_name = hashlib.md5(str(rel_path).encode()).hexdigest()
                        ext = item.name.split('.')[-1] if '.' in item.name else ''
                        short_name = "%s.%s" % (hash_name, ext) if ext else hash_name
                        print(f"File name too long, renaming to: {short_name}")
                        rel_path = Path(rel_path.parent / short_name)
                    
                    target_path = target_assets_dir / rel_path
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    print(f"Target path ready: {target_path}")
                    shutil.copy2(item, target_path)
                    print(f"Copied: {item} -&gt; {target_path}")
                    
                except Exception as e:
                    print(f"Failed to copy {item}: {e}")
                    continue
      
        print(f"Assets copied from {source_assets_dir} to {target_assets_dir}")
        
    except Exception as e:
        print(f"Error copying assets: {e}")
        import traceback
        traceback.print_exc()


def write_project_files(output_dir, files):
    written_files = []
    
    for file_path, content in files.items():
        full_path = output_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        written_files.append(file_path)
        print(f"  Written: {file_path}")
    
    return written_files


async def process_task(task_dir, config):
    task_path = Path(task_dir)
    output_dir = task_path / "output"
    output_dir.mkdir(exist_ok=True)
    
    checkpoints_dir = task_path / "checkpoints"
    checkpoint_files = sorted(checkpoints_dir.glob("step_*.png"))
    
    print(f"Found {len(checkpoint_files)} checkpoints:")
    for cp in checkpoint_files:
        print(f"  - {cp.name}")
    
    image_data_urls = []
    for checkpoint_file in checkpoint_files:
        with open(checkpoint_file, "rb") as f:
            image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            image_data_url = "data:image/png;base64,%s" % image_base64
            image_data_urls.append(image_data_url)
    
    prompt_messages = build_vue3_prompt(image_data_urls)
    
    provider = config.get("provider", "doubao")
    api_key = config.get("doubao_api_key", "")
    model = config.get("model", "doubao-seed-2.0-code")
    base_url = config.get("doubao_base_url", "")
    
    print(f"Calling {provider} AI...")
    
    adapter_kwargs = {}
    if base_url:
        adapter_kwargs["base_url"] = base_url
    
    adapter = create_adapter(
        provider=provider,
        api_key=api_key,
        model=model,
        **adapter_kwargs
    )
    
    ai_response = await adapter.generate(messages=prompt_messages)
    print(f"AI response length: {len(ai_response)}")
    
    project_files = parse_vue_project_structure(ai_response)
    
    assets_dir = task_path / "assets"
    if assets_dir.exists():
        print("Copying assets...")
        copy_assets(assets_dir, output_dir / "src" / "assets")
    
    print(f"Writing {len(project_files)} files...")
    written_files = write_project_files(output_dir, project_files)
    
    print("\nSuccess! Output directory: %s" % output_dir)
    print("Generated %d files:" % len(written_files))
    for f in written_files:
        print(f"  - {f}")
    
    return True


def load_config():
    config_path = Path(__file__).parent / "config.json"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


if __name__ == "__main__":
    if len(sys.argv) &lt; 2:
        print("Usage: python fix_router.py task_0001")
        sys.exit(1)
    
    task_name = sys.argv[1]
    config = load_config()
    
    base_dir = Path(__file__).parent
    task_dir = str(base_dir / task_name)
    
    print("Processing: %s" % task_dir)
    
    try:
        asyncio.run(process_task(task_dir, config))
    except Exception as e:
        print("Error: %s" % e)
        import traceback
        traceback.print_exc()
