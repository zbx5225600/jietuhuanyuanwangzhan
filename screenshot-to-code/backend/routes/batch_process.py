"""
批量处理API
将截图批量转换为Vue3项目
"""
import json
import base64
import shutil
import traceback
from pathlib import Path
from typing import Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from codegen.vue_extractor import parse_vue_project_structure

router = APIRouter()


class TaskProcessRequest(BaseModel):
    """单个task处理请求"""
    task_dir: str
    api_key: str
    model: str = "gpt-4-vision-preview"
    provider: str = "openai"
    secret_key: str = ""
    base_url: str = ""


class TaskProcessResponse(BaseModel):
    """批量处理响应"""
    success: bool
    message: str
    output_dir: str = ""
    files_generated: List[str] = []


@router.post("/api/batch-process")
async def batch_process_task(request: TaskProcessRequest):
    """
    处理单个task目录,从截图生成Vue3+Vite项目
    
    流程:
    1. 读取checkpoints中的所有截图 (每个截图是一个页面)
    2. 读取assets资源文件
    3. 调用AI生成带路由的多页面Vue3应用
    4. 解析多文件输出
    5. 写入output目录
    """
    try:
        task_dir = Path(request.task_dir)
        
        # 验证目录存在
        if not task_dir.exists():
            raise HTTPException(status_code=404, detail=f"Task directory not found: {task_dir}")
        
        # 创建output目录
        output_dir = task_dir / "output"
        output_dir.mkdir(exist_ok=True)
        
        # 1. 读取所有checkpoints截图 (每个截图是一个页面)
        checkpoints_dir = task_dir / "checkpoints"
        if not checkpoints_dir.exists():
            raise HTTPException(status_code=400, detail="No checkpoints directory found")
        
        checkpoint_files = sorted(checkpoints_dir.glob("step_*.png"))
        if not checkpoint_files:
            raise HTTPException(status_code=400, detail="No checkpoint images found")
        
        print(f"Found {len(checkpoint_files)} checkpoints (each is a page):")
        for cp in checkpoint_files:
            print(f"  - {cp.name}")
        
        # 将所有截图转换为base64
        image_data_urls = []
        for checkpoint_file in checkpoint_files:
            with open(checkpoint_file, "rb") as f:
                image_bytes = f.read()
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                image_data_url = f"data:image/png;base64,{image_base64}"
                image_data_urls.append(image_data_url)
        
        # 2. 构建Prompt (使用Vue3+Vite配置，带路由支持)
        prompt_messages = build_vue3_prompt(image_data_urls)
        
        # 3. 调用AI生成代码
        print(f"Calling {request.provider} AI to generate multi-page Vue3 app...")
        ai_response = await call_llm(
            messages=prompt_messages,
            api_key=request.api_key,
            model=request.model,
            provider=request.provider,
            secret_key=request.secret_key,
            base_url=request.base_url
        )
        
        print(f"AI response length: {len(ai_response)}")
        
        # 4. 解析AI响应,提取文件
        project_files = parse_vue_project_structure(ai_response)
        
        # 5. 复制assets资源文件
        assets_dir = task_dir / "assets"
        if assets_dir.exists():
            print("Copying assets...")
            copy_assets(assets_dir, output_dir / "src" / "assets")
        
        # 6. 写入output目录
        print(f"Writing {len(project_files)} files to output directory...")
        written_files = write_project_files(output_dir, project_files)
        
        return TaskProcessResponse(
            success=True,
            message=f"Successfully processed {task_dir.name} (multi-page app with {len(checkpoint_files)} pages)",
            output_dir=str(output_dir),
            files_generated=written_files
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing task: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def build_vue3_prompt(image_data_urls):
    num_pages = len(image_data_urls)
    page_names = ["Home", "Photos", "About", "Lightroom", "Contact"][:num_pages]
    page_paths = ["/", "/photos", "/about", "/lightroom", "/contact"][:num_pages]
    
    pages_description = []
    for i in range(num_pages):
        pages_description.append(f"- Screenshot {i+1}: {page_names[i]} page ({page_paths[i]})")
    pages_description_str = "\n".join(pages_description)
    
    page_components_list = []
    for i in range(num_pages):
        page_components_list.append(f"- src/views/{page_names[i]}.vue")
    page_components_str = "\n".join(page_components_list)
    
    page_routes_list = []
    for i in range(num_pages):
        page_routes_list.append(f"- {page_paths[i]} -> {page_names[i]}")
    page_routes_str = "\n".join(page_routes_list)
    
    system_prompt = "You are an expert frontend developer specializing in Vue 3 and Vite.\n\n"
    system_prompt += "Your task is to recreate a website from multiple screenshots as a Vue 3 + Vite project with Vue Router.\n\n"
    system_prompt += "# Multi-Page App - IMPORTANT!\n\n"
    system_prompt += f"- There are {num_pages} screenshots, each representing a different page of the website\n"
    system_prompt += f"- Use Vue Router to implement page navigation between these {num_pages} pages\n"
    system_prompt += pages_description_str + "\n\n"
    system_prompt += "# Output Format\n\n"
    system_prompt += "You MUST output multiple files using the following format:\n\n"
    system_prompt += "<file path=\"index.html\">\n<!DOCTYPE html>\n<html lang=\"en\">\n  <head>\n    <meta charset=\"UTF-8\" />\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n    <title>App</title>\n  </head>\n  <body>\n    <div id=\"app\"></div>\n    <script type=\"module\" src=\"/src/main.ts\"></script>\n  </body>\n</html>\n</file>\n\n"
    system_prompt += "<file path=\"package.json\">\n{\n  \"name\": \"vue3-app\",\n  \"private\": true,\n  \"version\": \"0.0.0\",\n  \"type\": \"module\",\n  \"scripts\": {\n    \"dev\": \"vite\",\n    \"build\": \"vue-tsc && vite build\",\n    \"preview\": \"vite preview\"\n  },\n  \"dependencies\": {\n    \"vue\": \"^3.4.0\",\n    \"vue-router\": \"^4.2.0\"\n  },\n  \"devDependencies\": {\n    \"@vitejs/plugin-vue\": \"^5.0.0\",\n    \"typescript\": \"^5.2.0\",\n    \"vite\": \"^5.0.0\",\n    \"vue-tsc\": \"^1.8.0\"\n  }\n}\n</file>\n\n"
    system_prompt += "<file path=\"vite.config.ts\">\nimport { defineConfig } from 'vite'\nimport vue from '@vitejs/plugin-vue'\n\nexport default defineConfig({\n  plugins: [vue()],\n})\n</file>\n\n"
    system_prompt += "<file path=\"tsconfig.json\">\n{\n  \"compilerOptions\": {\n    \"target\": \"ES2020\",\n    \"useDefineForClassFields\": true,\n    \"module\": \"ESNext\",\n    \"lib\": [\"ES2020\", \"DOM\", \"DOM.Iterable\"],\n    \"skipLibCheck\": true,\n    \"moduleResolution\": \"bundler\",\n    \"allowImportingTsExtensions\": true,\n    \"resolveJsonModule\": true,\n    \"isolatedModules\": true,\n    \"noEmit\": true,\n    \"jsx\": \"preserve\",\n    \"strict\": true,\n    \"noUnusedLocals\": true,\n    \"noUnusedParameters\": true,\n    \"noFallthroughCasesInSwitch\": true\n  },\n  \"include\": [\"src/**/*.ts\", \"src/**/*.tsx\", \"src/**/*.vue\"],\n  \"references\": [{ \"path\": \"./tsconfig.node.json\" }]\n}\n</file>\n\n"
    system_prompt += "<file path=\"tsconfig.node.json\">\n{\n  \"compilerOptions\": {\n    \"composite\": true,\n    \"skipLibCheck\": true,\n    \"module\": \"ESNext\",\n    \"moduleResolution\": \"bundler\",\n    \"allowSyntheticDefaultImports\": true\n  },\n  \"include\": [\"vite.config.ts\"]\n}\n</file>\n\n"
    system_prompt += "<file path=\"src/main.ts\">\nimport { createApp } from 'vue'\nimport App from './App.vue'\nimport router from './router'\n\ncreateApp(App).use(router).mount('#app')\n</file>\n\n"
    system_prompt += "<file path=\"src/router/index.ts\">\nimport { createRouter, createWebHistory } from 'vue-router'\nimport Home from '../views/Home.vue'\n\nconst routes = [\n  {\n    path: '/',\n    name: 'Home',\n    component: Home\n  }\n]\n\nconst router = createRouter({\n  history: createWebHistory(),\n  routes\n})\n\nexport default router\n</file>\n\n"
    system_prompt += "<file path=\"src/App.vue\">\n<script setup lang=\"ts\">\n</script>\n\n<template>\n  <div id=\"app\">\n    <router-view />\n  </div>\n</template>\n\n<style>\n#app {\n  font-family: Avenir, Helvetica, Arial, sans-serif;\n  -webkit-font-smoothing: antialiased;\n  -moz-osx-font-smoothing: grayscale;\n}\n</style>\n</file>\n\n"
    system_prompt += "<file path=\"src/views/Home.vue\">\n<script setup lang=\"ts\">\n</script>\n\n<template>\n</template>\n\n<style scoped>\n</style>\n</file>\n\n"
    system_prompt += "# Important Guidelines - CRITICAL!\n\n"
    system_prompt += f"1. Recreate EACH of the {num_pages} pages EXACTLY as shown in its corresponding screenshot\n"
    system_prompt += "2. Pay attention to colors, fonts, spacing, layout, and all details on every page\n"
    system_prompt += "3. Write clean, modern Vue 3 code with Composition API\n"
    system_prompt += "4. Use TypeScript for type safety\n"
    system_prompt += f"5. Use Vue Router for page navigation - YOU MUST CREATE {num_pages} ROUTES!\n"
    system_prompt += f"6. Create a src/views/ directory for page components - {num_pages} page components total!\n"
    system_prompt += f"7. Create a navigation menu (header) to navigate between all {num_pages} pages\n"
    system_prompt += "8. Split into multiple .vue components if the UI is complex\n"
    system_prompt += "9. All static assets should be in src/assets/\n"
    system_prompt += "10. Use relative paths for assets: /src/assets/image.png\n\n"
    system_prompt += f"# YOU MUST CREATE THESE {num_pages} PAGE COMPONENTS:\n"
    system_prompt += page_components_str + "\n\n"
    system_prompt += f"# AND YOU MUST CONFIGURE THESE {num_pages} ROUTES IN src/router/index.ts:\n"
    system_prompt += page_routes_str + "\n\n"
    system_prompt += "# Important\n\n"
    system_prompt += "- Output ALL files using the <file path=\"...\"> format shown above\n"
    system_prompt += "- Each file must be wrapped in <file path=\"...\">...</file>\n"
    system_prompt += "- Do NOT use markdown code blocks\n"
    system_prompt += "- Make sure the recreated pages look identical to the screenshots\n"
    system_prompt += "- The first screenshot is the Home page (/)\n"
    system_prompt += "- Create additional page components in src/views/ for the other screenshots\n"
    system_prompt += f"- DO NOT FORGET TO CREATE ALL {num_pages} PAGE COMPONENTS AND ROUTES!\n"

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


async def call_llm(
    messages,
    api_key,
    model="gpt-4-vision-preview",
    provider="openai",
    secret_key="",
    base_url=""
):
    import sys
    from pathlib import Path
    backend_path = Path(__file__).parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    from llm_adapters import create_adapter
    
    adapter_kwargs = {}
    if (provider == "openai" or provider == "doubao") and base_url:
        adapter_kwargs["base_url"] = base_url
    elif provider == "ernie":
        adapter_kwargs["secret_key"] = secret_key
    
    adapter = create_adapter(
        provider=provider,
        api_key=api_key,
        model=model,
        **adapter_kwargs
    )
    
    return await adapter.generate(messages=messages)


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
                    
                    if len(str(target_assets_dir / rel_path)) > 255:
                        import hashlib
                        hash_name = hashlib.md5(str(rel_path).encode()).hexdigest()
                        ext = item.name.split('.')[-1] if '.' in item.name else ''
                        short_name = f"{hash_name}.{ext}" if ext else hash_name
                        print(f"File name too long, renaming to: {short_name}")
                        rel_path = Path(rel_path.parent / short_name)
                    
                    target_path = target_assets_dir / rel_path
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    print(f"Target path ready: {target_path}")
                    shutil.copy2(item, target_path)
                    print(f"Copied: {item} -> {target_path}")
                    
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
