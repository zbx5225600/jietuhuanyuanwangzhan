"""
批量处理API
将截图批量转换为Vue3项目
"""
import json
import base64
import re
import shutil
import traceback
import os
from pathlib import Path
from typing import Dict, List, Tuple
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
    min_visual_similarity: float = 0.90
    max_restore_attempts: int = 5


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
    5. 验证并循环补齐缺失的页面组件、router和App.vue
    6. 写入output目录
    7. checkpoints中有几个页面，就需要生成几个路由，生成的output中的views中的组件数量也得有几个
    8. 从video.mp4中提取交互逻辑和对应地方的图片，从assets中找到对应的图片，将图片路径替换到对应的views中的vue组件的对应位置
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
        
        # 读取assets中的所有图片并转换为base64，供AI视觉识别
        assets_image_data_urls = []
        assets_image_filenames = []
        assets_images_dir = task_dir / "assets" / "images"
        if assets_images_dir.exists():
            print(f"Found {len(list(assets_images_dir.glob('*')))} assets images:")
            for img_file in assets_images_dir.iterdir():
                if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    try:
                        # 先检查图片尺寸，跳过太小的图片
                        try:
                            from PIL import Image
                            with Image.open(img_file) as img:
                                width, height = img.size
                                if width < 14 or height <  14:
                                    print(f"  - Skipping {img_file.name} (too small: {width}x{height})")
                                    continue
                        except ImportError:
                            # PIL 不可用，跳过尺寸检查
                            pass
                        except Exception:
                            # 无法读取图片尺寸，跳过
                            print(f"  - Skipping {img_file.name} (cannot read dimensions)")
                            continue
                        
                        # 读取并转换图片
                        with open(img_file, "rb") as f:
                            image_bytes = f.read()
                            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                            image_data_url = f"data:image/png;base64,{image_base64}"
                            assets_image_data_urls.append(image_data_url)
                            assets_image_filenames.append(img_file.name)
                            print(f"  - {img_file.name}")
                    except Exception as e:
                        print(f"  Warning: Failed to read {img_file.name}: {e}")
        
        # 2. 让AI分析截图，获取页面名称和路由
        print("\n" + "="*60)
        print("Step 1: Analyzing screenshots to determine page names and routes")
        print("="*60)
        page_analysis_messages = build_page_analysis_prompt(image_data_urls)
        page_analysis_response = await call_llm(
            messages=page_analysis_messages,
            api_key=request.api_key,
            model=request.model,
            provider=request.provider,
            secret_key=request.secret_key,
            base_url=request.base_url
        )
        print(f"Page analysis response: {page_analysis_response[:500]}...")
        
        screenshot_page_names, screenshot_page_paths = parse_page_analysis_response(page_analysis_response)
        
        if not screenshot_page_names or not screenshot_page_paths:
            print("Warning: Failed to parse page analysis response, using fallback page names")
            screenshot_page_names = [f"Page{i+1}" for i in range(len(image_data_urls))]
            screenshot_page_paths = [f"/page{i+1}" for i in range(len(image_data_urls))]
        
        print(f"Determined page names from screenshots: {screenshot_page_names}")
        print(f"Determined page paths from screenshots: {screenshot_page_paths}")
        
        # Home 页面 + 截图页面
        page_names = ["Home"] + screenshot_page_names
        page_paths = ["/"] + screenshot_page_paths
        num_pages = len(page_names)
        
        # 加载 manifest 映射和每个步骤的资源
        print("\n" + "="*60)
        print("Step 2: Loading manifest and step resources")
        print("="*60)
        url_to_local_path = load_manifest_mapping(task_dir)
        
        # 为每个截图步骤加载其资源
        step_resources = {}
        for i in range(len(checkpoint_files)):
            step_resources[i] = load_step_resources(task_dir, i)
        
        # 建立 page_name -&gt; step_index 的映射 (Home 页面对应 None)
        page_to_step_index = {}
        for i, page_name in enumerate(screenshot_page_names):
            page_to_step_index[page_name] = i
        
        print(f"Page to step index mapping: {page_to_step_index}")
        
        # 构建 prompt 字符串
        page_components_str, page_routes_str, pages_description_str = build_vue3_prompt_from_page_info(
            screenshot_page_names, 
            screenshot_page_paths
        )
        
        # 3. 构建Prompt
        prompt_messages = build_vue3_prompt_messages(
            image_data_urls, 
            page_names, 
            page_paths, 
            page_components_str, 
            page_routes_str, 
            pages_description_str, 
            num_pages,
            assets_image_data_urls,
            assets_image_filenames,
            step_resources,
            url_to_local_path,
            page_to_step_index
        )
        
        # 存储所有生成的文件
        all_project_files = {}
        
        # 4. 循环生成和验证，直到所有页面都生成完成或达到最大重试次数
        min_visual_similarity = max(0.0, min(1.0, request.min_visual_similarity))
        max_retries = max(1, min(5, request.max_restore_attempts))
        for attempt in range(max_retries):
            print(f"\n{'='*60}")
            print(f"Generation Attempt {attempt + 1}/{max_retries}")
            print(f"{'='*60}")
            
            # 调用AI生成代码
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
            
            # 解析AI响应,提取文件
            new_project_files = parse_vue_project_structure(ai_response)
            
            # 【关键】对新生成的view文件进行图片替换，确保图片正确对应
            print(f"\nReplacing images in newly generated view files...")
            # 先复制assets到临时目录，让图片替换函数可以找到文件
            temp_assets_dir = output_dir / "src" / "assets"
            if not temp_assets_dir.exists():
                assets_dir = task_dir / "assets"
                if assets_dir.exists():
                    copy_assets(assets_dir, temp_assets_dir)
            
            for file_path, content in new_project_files.items():
                # 只处理view文件
                if file_path.startswith("src/views/") and file_path.endswith(".vue"):
                    page_name = Path(file_path).stem
                    print(f"  Processing: {file_path} (page: {page_name})")
                    
                    # 找到对应的step_index
                    if page_name in page_to_step_index:
                        step_index = page_to_step_index[page_name]
                        step_image_urls = step_resources.get(step_index, [])
                        print(f"    Using step_{step_index:02d} resources: {len(step_image_urls)} images")
                        
                        # 替换图片
                        content = replace_images_with_manifest_mapping(
                            content, 
                            step_image_urls, 
                            url_to_local_path, 
                            output_dir
                        )
                        
                        # 更新文件内容
                        new_project_files[file_path] = content
                        print(f"    Updated: {file_path}")
                    else:
                        print(f"    Skipping (not a screenshot page): {page_name}")
            
            # 合并到总文件字典中
            all_project_files.update(new_project_files)
            
            # 检查是否所有必要文件都生成了
            missing_pages = []
            for page_name in page_names:
                expected_file = f"src/views/{page_name}.vue"
                if expected_file not in all_project_files:
                    missing_pages.append(page_name)
            
            # 检查必要的核心文件
            missing_core_files = []
            required_core_files = [
                "src/router/index.ts",
                "src/App.vue",
                "src/main.ts"
            ]
            for core_file in required_core_files:
                if core_file not in all_project_files:
                    missing_core_files.append(core_file)
            
            # 验证 router 文件内容
            router_valid = True
            router_missing_imports = []
            router_wrong_paths = []
            router_wrong_components = []
            if "src/router/index.ts" in all_project_files:
                router_content = all_project_files["src/router/index.ts"]
                for page_name in page_names:
                    import_line = f"import {page_name} from '../views/{page_name}.vue'"
                    if import_line not in router_content:
                        router_missing_imports.append(page_name)
                        router_valid = False
                
                # 检查路由的 path 和 component 是否正确
                for i, page_name in enumerate(page_names):
                    expected_path = page_paths[i]
                    expected_component = page_name
                    # 检查 path
                    path_pattern = rf'path:\s*[\'"]({expected_path})[\'"]'
                    import re
                    if not re.search(path_pattern, router_content):
                        router_wrong_paths.append(f"{page_name} should have path: {expected_path}")
                        router_valid = False
                    # 检查 component
                    component_pattern = rf'component:\s*{expected_component}'
                    if not re.search(component_pattern, router_content):
                        router_wrong_components.append(f"{page_name} should have component: {expected_component}")
                        router_valid = False
            
            # 验证 App.vue 是否有 router-view
            app_valid = True
            if "src/App.vue" in all_project_files:
                app_content = all_project_files["src/App.vue"]
                if "<router-view />" not in app_content and "<router-view/>" not in app_content:
                    app_valid = False
            
            # 验证 main.ts 是否正确配置了 router
            main_valid = True
            if "src/main.ts" in all_project_files:
                main_content = all_project_files["src/main.ts"]
                if "import router from './router'" not in main_content and "import router from './router'" not in main_content:
                    main_valid = False
                if ".use(router)" not in main_content:
                    main_valid = False
            
            # 验证 package.json 是否有正确的依赖
            package_valid = True
            missing_dependencies = []
            if "package.json" in all_project_files:
                try:
                    import json
                    package_content = json.loads(all_project_files["package.json"])
                    required_deps = {
                        "vue": "^3.4.0",
                        "vue-router": "^4.2.0"
                    }
                    required_dev_deps = {
                        "@vitejs/plugin-vue": "^5.0.0",
                        "typescript": "~5.4.5",
                        "vite": "^5.0.0",
                        "vue-tsc": "^2.0.29"
                    }
                    
                    # 检查必需的顶级字段
                    required_fields = ["name", "private", "version", "type", "scripts"]
                    for field in required_fields:
                        if field not in package_content:
                            package_valid = False
                            missing_dependencies.append(f"Missing required field: {field}")
                    
                    # 检查 scripts
                    if "scripts" in package_content:
                        required_scripts = ["dev", "build", "preview"]
                        for script in required_scripts:
                            if script not in package_content["scripts"]:
                                package_valid = False
                                missing_dependencies.append(f"Missing script: {script}")
                    
                    if "dependencies" not in package_content:
                        package_valid = False
                        missing_dependencies.extend(required_deps.keys())
                    else:
                        for dep, version in required_deps.items():
                            if dep not in package_content["dependencies"]:
                                package_valid = False
                                missing_dependencies.append(dep)
                    
                    if "devDependencies" not in package_content:
                        package_valid = False
                        missing_dependencies.extend(required_dev_deps.keys())
                    else:
                        for dep, version in required_dev_deps.items():
                            if dep not in package_content["devDependencies"]:
                                package_valid = False
                                missing_dependencies.append(dep)
                except Exception as e:
                    package_valid = False
                    missing_dependencies.append(f"Invalid package.json format: {e}")
            else:
                package_valid = False
                missing_dependencies.append("package.json missing")

            # Validate screenshot pages actually contain images (not placeholders only)
            missing_image_pages = []
            low_image_count_pages = []
            for page_name in screenshot_page_names:
                view_file = f"src/views/{page_name}.vue"
                if view_file not in all_project_files:
                    continue
                step_index = page_to_step_index.get(page_name)
                step_imgs = step_resources.get(step_index, []) if step_index is not None else []
                if step_imgs and not view_has_image_reference(all_project_files[view_file]):
                    missing_image_pages.append(page_name)
                    continue
                if step_imgs:
                    actual_refs = count_view_image_references(all_project_files[view_file])
                    required_refs = get_min_required_image_refs_for_step(len(step_imgs))
                    if actual_refs < required_refs:
                        low_image_count_pages.append(f"{page_name} ({actual_refs}/{required_refs})")

            # Validate header proportion is not severely drifted
            header_style_issues = []
            header_route_issues = []
            header_typography_issues = []
            header_file = "src/components/Header.vue"
            if header_file in all_project_files:
                header_style_issues = detect_header_fidelity_issues(all_project_files[header_file])
                header_route_issues = detect_header_route_issues(all_project_files[header_file], page_paths)
                header_typography_issues = detect_header_typography_issues(
                    all_project_files[header_file],
                    expected_nav_count=len(page_paths)
                )

            # Render compare screenshots for this attempt so visual similarity can be evaluated.
            try:
                write_project_files(
                    output_dir,
                    all_project_files,
                    output_dir,
                    url_to_local_path,
                    step_resources,
                    page_to_step_index
                )
                await generate_compare_screenshots(task_dir, output_dir, screenshot_page_paths)
            except Exception as render_err:
                print(f"Warning: compare screenshot generation failed: {render_err}")

            # Optional visual fidelity check: only active when compare/gen_step_*.png exists.
            low_visual_fidelity_pages, visual_similarity_scores = evaluate_visual_similarity(
                task_dir,
                screenshot_page_names,
                min_similarity_threshold=min_visual_similarity
            )
            if visual_similarity_scores:
                print(f"   - Visual similarity threshold: {min_visual_similarity:.0%}")
                print(f"   - Visual similarity scores: {visual_similarity_scores}")
            else:
                print("   - Visual similarity check skipped (missing compare/gen_step_*.png)")
            
            all_valid = (
                not missing_pages and 
                not missing_core_files and 
                router_valid and 
                app_valid and 
                main_valid and
                package_valid and
                not missing_image_pages and
                not low_image_count_pages and
                not header_style_issues and
                not header_route_issues and
                not header_typography_issues and
                not low_visual_fidelity_pages
            )
            
            if all_valid:
                print(f"✅ All {num_pages} page components and core files generated successfully!")
                break
            
            # 如果还有缺失，构建补齐prompt
            print(f"❌ Validation failed:")
            if missing_pages:
                print(f"   - Missing {len(missing_pages)} page components: {missing_pages}")
            if missing_core_files:
                print(f"   - Missing core files: {missing_core_files}")
            if not router_valid:
                print(f"   - Router file issues:")
                if router_missing_imports:
                    print(f"     - Missing imports: {router_missing_imports}")
                if router_wrong_paths:
                    for path_issue in router_wrong_paths:
                        print(f"     - {path_issue}")
                if router_wrong_components:
                    for comp_issue in router_wrong_components:
                        print(f"     - {comp_issue}")
            if not app_valid:
                print(f"   - App.vue is missing <router-view />")
            if not main_valid:
                print(f"   - main.ts is missing router setup")
            if not package_valid:
                print(f"   - package.json missing dependencies: {missing_dependencies}")
            if missing_image_pages:
                print(f"   - Pages missing actual image rendering: {missing_image_pages}")
            if low_image_count_pages:
                print(f"   - Pages with too few image references: {low_image_count_pages}")
            if header_style_issues:
                print(f"   - Header style drift issues: {header_style_issues}")
            if header_route_issues:
                print(f"   - Header route issues: {header_route_issues}")
            if header_typography_issues:
                print(f"   - Header typography issues: {header_typography_issues}")
            if low_visual_fidelity_pages:
                print(f"   - Low visual fidelity pages: {low_visual_fidelity_pages}")
            
            if attempt < max_retries - 1:
                print(f"Building correction prompt...")
                prompt_messages = build_correction_prompt(
                    image_data_urls,
                    page_names,
                    page_paths,
                    missing_pages,
                    missing_core_files,
                    router_valid,
                    app_valid,
                    main_valid,
                    package_valid,
                    missing_dependencies,
                    missing_image_pages,
                    low_image_count_pages,
                    header_style_issues,
                    header_route_issues,
                    header_typography_issues,
                    low_visual_fidelity_pages,
                    min_visual_similarity,
                    all_project_files,
                    num_pages
                )
        
        # 5. 先复制assets资源文件到output目录
        assets_dir = task_dir / "assets"
        if assets_dir.exists():
            print("Copying assets first...")
            copy_assets(assets_dir, output_dir / "src" / "assets")
        
        # 6. 写入output目录，并从output的assets中替换图片
        print(f"Writing {len(all_project_files)} files to output directory...")
        written_files = write_project_files(
            output_dir, 
            all_project_files, 
            output_dir,
            url_to_local_path,
            step_resources,
            page_to_step_index
        )

        # Remove stale view files from previous runs to avoid mixed route sets.
        remove_stale_view_files(output_dir, page_names)
        
        # 6.5 验证并修复 index.html，确保 script 标签有 src
        index_html_path = output_dir / "index.html"
        if index_html_path.exists():
            with open(index_html_path, 'r', encoding='utf-8') as f:
                index_html_content = f.read()
            
            # 检查 script 标签是否有 src
            if '<script type="module" ></script>' in index_html_content or '<script type="module"></script>' in index_html_content:
                print("  Fixing index.html: script tag missing src")
                # 修复 script 标签
                index_html_content = index_html_content.replace(
                    '<script type="module" ></script>',
                    '<script type="module" src="/src/main.ts"></script>'
                ).replace(
                    '<script type="module"></script>',
                    '<script type="module" src="/src/main.ts"></script>'
                )
                # 写回文件
                with open(index_html_path, 'w', encoding='utf-8') as f:
                    f.write(index_html_content)
                print("  Fixed index.html successfully")
        
        # 7. 验证生成的文件数量
        validate_generated_files(output_dir, num_pages, page_names, all_project_files)
        
        # 7.5 确保 Home 页面存在，如果需要的话生成空的 Home 页面
        ensure_home_page_exists(output_dir, all_project_files)
        
        # 8. 后处理Vue文件，修复常见的语法问题
        post_process_vue_files(output_dir)
        
        # 8.5 修复路由路径，确保所有路径都是小写的
        fix_router_paths(output_dir)
        
        # 8.6 最终修复图片：确保用每个页面实际使用的图片
        fix_vue_images_with_manifest(
            output_dir, 
            url_to_local_path, 
            step_resources, 
            page_to_step_index
        )
        
        # 9. 运行编译检查，确保没有语法错误和编译错误
        build_success = await run_build_check(output_dir)

        # Re-render compare screenshots from final output state.
        try:
            await generate_compare_screenshots(task_dir, output_dir, screenshot_page_paths)
        except Exception as render_err:
            print(f"Warning: final compare screenshot generation failed: {render_err}")
        
        # Final fidelity report (per-page + overall)
        _, final_visual_similarity_scores = evaluate_visual_similarity(
            task_dir,
            screenshot_page_names,
            min_similarity_threshold=min_visual_similarity
        )
        print_visual_fidelity_summary(
            screenshot_page_names,
            final_visual_similarity_scores,
            min_visual_similarity
        )
        
        return TaskProcessResponse(
            success=True,
            message=f"Successfully processed {task_dir.name} (multi-page app with {num_pages} pages)",
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


def load_manifest_mapping(task_dir: Path) -> Dict[str, str]:
    """
    加载 raw_manifest.json，建立 URL -> 本地文件路径的映射
    """
    manifest_file = task_dir / "assets" / "manifests" / "raw_manifest.json"
    url_to_local_path = {}
    
    if manifest_file.exists():
        try:
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            for item in manifest:
                url = item.get('url')
                local_path = item.get('local_path')
                if url and local_path:
                    url_to_local_path[url] = local_path
            
            print(f"Loaded {len(url_to_local_path)} URL -> local path mappings from raw_manifest.json")
        except Exception as e:
            print(f"Warning: Failed to load raw_manifest.json: {e}")
    
    return url_to_local_path


def remove_stale_view_files(output_dir: Path, page_names: List[str]) -> None:
    """
    Remove stale .vue files in src/views that are not part of current page_names.
    This prevents previous-run leftovers from polluting router regeneration.
    """
    views_dir = output_dir / "src" / "views"
    if not views_dir.exists():
        return

    keep = set(page_names)
    for vue_file in views_dir.glob("*.vue"):
        if vue_file.stem not in keep:
            try:
                vue_file.unlink()
                print(f"Removed stale view file: {vue_file.name}")
            except Exception as e:
                print(f"Warning: failed to remove stale view {vue_file.name}: {e}")


def load_step_resources(task_dir: Path, step_index: int) -> List[str]:
    """
    加载 dom_visible_resources_step_XX.json，获取该步骤（页面）使用的所有图片URL
    """
    resources_file = task_dir / "assets" / "manifests" / f"dom_visible_resources_step_{step_index:02d}.json"
    image_urls = []
    
    if resources_file.exists():
        try:
            with open(resources_file, 'r', encoding='utf-8') as f:
                resources = json.load(f)
            
            image_urls = resources.get('images', [])
            print(f"Loaded {len(image_urls)} images for step_{step_index:02d}")
        except Exception as e:
            print(f"Warning: Failed to load dom_visible_resources_step_{step_index:02d}.json: {e}")
    
    return image_urls


def _build_step_image_list(step_image_urls: List[str], url_to_local_path: Dict[str, str], images_dir: Path) -> List[str]:
    """
    从 step 的 URL 列表中，建立去重后的高质量本地图片文件名列表。
    同一张图的不同 format 变体（如 100w/300w/1500w）只保留最大的一个。
    过滤掉 logo/icon/favicon/cart/tracking 等装饰性图片。
    """
    exclude_keywords = ['logo', 'icon', 'favicon', 'cart', '.gif', 'tracking', 'p.gif']

    # base_name -> [(filename, size_hint)]
    candidates: Dict[str, List[tuple]] = {}

    for url in step_image_urls:
        if url not in url_to_local_path:
            continue
        filename = Path(url_to_local_path[url]).name

        # 过滤装饰性图片
        lower = filename.lower()
        if any(kw.lower() in lower for kw in exclude_keywords):
            continue

        # 检查本地文件是否存在
        if not (images_dir / filename).exists():
            continue

        # 提取 base name（去掉 _format_XXX 后缀）
        base_name = filename.split('_format_')[0] if '_format_' in filename else filename

        # 从 format 参数中提取尺寸数字作为排序依据
        size_hint = 0
        fmt_match = re.search(r'_format_(\d+)w', filename)
        if fmt_match:
            size_hint = int(fmt_match.group(1))
        else:
            # 无 format 后缀的原始文件，尺寸最大
            size_hint = 99999

        if base_name not in candidates:
            candidates[base_name] = []
        candidates[base_name].append((filename, size_hint))

    # 对每组选最大的
    result = []
    for base_name, variants in candidates.items():
        variants.sort(key=lambda x: x[1], reverse=True)
        result.append(variants[0][0])

    return result


def replace_images_with_manifest_mapping(content: str, step_image_urls: List[str], url_to_local_path: Dict[str, str], output_dir: Path) -> str:
    """
    使用 manifest 映射替换 content 中的图片。
    基于 _build_step_image_list 获取该页面去重后的高质量图片列表，
    然后按 DOM 顺序依次分配给各 img 标签。
    """
    images_dir = output_dir / "src" / "assets" / "images"
    if not images_dir.exists():
        return content

    step_local_images = _build_step_image_list(step_image_urls, url_to_local_path, images_dir)
    if not step_local_images:
        return content

    print(f"  Step images (deduped, best quality): {step_local_images}")

    # 验证这些文件确实存在
    valid_images = []
    for fname in step_local_images:
        if (images_dir / fname).exists():
            valid_images.append(fname)
        else:
            print(f"  Warning: image file not found on disk: {fname}")

    if not valid_images:
        return content

    # 用一个可变索引，按 DOM 顺序轮转分配图片
    img_idx = [0]

    img_pattern = r'src\s*=\s*(["\'])(.*?)\1'

    def fix_image_src(match):
        quote = match.group(1)
        img_path = match.group(2)

        # 路径已经是有效的本地图片，直接保留
        if img_path.startswith('/src/assets/images/'):
            filename = img_path.split('/')[-1]
            if (images_dir / filename).exists():
                return f'src={quote}{img_path}{quote}'

        # 分配该步骤的下一张图片
        selected = valid_images[img_idx[0] % len(valid_images)]
        img_idx[0] += 1
        new_path = f'/src/assets/images/{selected}'
        print(f"  Replaced: {img_path} -> {new_path}")
        return f'src={quote}{new_path}{quote}'

    modified_content, count = re.subn(img_pattern, fix_image_src, content)
    if count > 0:
        print(f"  Fixed {count} image sources using manifest mapping")

    return modified_content


def view_has_image_reference(content: str) -> bool:
    """
    Check whether a Vue page contains meaningful image usage.
    """
    if re.search(r'<img\b', content, re.IGNORECASE):
        return True
    if re.search(r'(?:src|:src|v-bind:src)\s*=\s*["\']', content):
        return True
    if re.search(r'background(?:-image)?\s*:\s*[^;]*url\(', content, re.IGNORECASE):
        return True
    if "/src/assets/images/" in content:
        return True
    return False


def count_view_image_references(content: str) -> int:
    """
    Count image references in a Vue page.
    """
    img_tag_count = len(re.findall(r'<img\b', content, re.IGNORECASE))
    bg_url_count = len(re.findall(r'background(?:-image)?\s*:\s*[^;]*url\(', content, re.IGNORECASE))
    src_ref_count = len(re.findall(r'(?:src|:src|v-bind:src)\s*=\s*["\']', content))
    return max(img_tag_count + bg_url_count, src_ref_count)


def get_min_required_image_refs_for_step(step_image_url_count: int) -> int:
    """
    Dynamic threshold based on screenshot step complexity.
    This avoids site-specific hardcoding and scales to different websites.
    """
    if step_image_url_count <= 0:
        return 0
    if step_image_url_count >= 80:
        return 3
    if step_image_url_count >= 20:
        return 2
    return 1


def detect_header_fidelity_issues(content: str) -> List[str]:
    """
    Detect severe header sizing/spacing choices that commonly cause large
    visual drift vs screenshot. Keep thresholds conservative and generic.
    """
    issues: List[str] = []

    css_blocks = re.findall(r'([^{}]+)\{([^{}]+)\}', content, flags=re.IGNORECASE)
    for raw_selector, decls in css_blocks:
        selector = raw_selector.lower()

        # Catastrophic width collapse for header wrappers.
        if "header" in selector:
            for m in re.finditer(r'max-width\s*:\s*(\d+(?:\.\d+)?)px', decls, flags=re.IGNORECASE):
                px = float(m.group(1))
                if px <= 240:
                    issues.append(f"Header max-width too small in selector '{raw_selector.strip()}': {px}px")
                    break

        # Severe fixed logo sizing (often causes oversized left logo).
        if "logo" in selector:
            for m in re.finditer(r'(?:width|height|max-width|max-height)\s*:\s*(\d+(?:\.\d+)?)px', decls, flags=re.IGNORECASE):
                px = float(m.group(1))
                if px >= 72:
                    issues.append(f"Logo fixed px too large in selector '{raw_selector.strip()}': {px}px")
                    break

        # Severe nav/header spacing drift.
        if "header-content" in selector or ".nav" in selector:
            for m in re.finditer(r'gap\s*:\s*(\d+(?:\.\d+)?)px', decls, flags=re.IGNORECASE):
                px = float(m.group(1))
                if px >= 40:
                    issues.append(f"Header/nav gap too large in selector '{raw_selector.strip()}': {px}px")
                    break

        # Oversized nav typography.
        if ".nav" in selector or "nav-link" in selector:
            for m in re.finditer(r'font-size\s*:\s*(\d+(?:\.\d+)?)px', decls, flags=re.IGNORECASE):
                px = float(m.group(1))
                if px >= 16:
                    issues.append(f"Nav font-size too large in selector '{raw_selector.strip()}': {px}px")
                    break

    # De-duplicate while preserving order.
    deduped: List[str] = []
    seen = set()
    for item in issues:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def detect_header_route_issues(content: str, allowed_paths: List[str]) -> List[str]:
    """
    Detect router-link targets in Header.vue that are outside the expected route set.
    """
    issues: List[str] = []
    allowed = set(allowed_paths)
    paths = re.findall(r'<(?:router-link|routerlink)\s+[^>]*to\s*=\s*["\']([^"\']+)["\']', content, flags=re.IGNORECASE)
    for path in paths:
        if path not in allowed:
            issues.append(f"Unexpected header route: {path}")
    if paths:
        duplicate_paths = [p for p in set(paths) if paths.count(p) > 1]
        if duplicate_paths:
            issues.append(f"Header has duplicate route targets: {sorted(duplicate_paths)}")

    # Disallow placeholder nav anchors like <a href="#" class="nav-link">...</a>
    fake_nav_links = re.findall(
        r'<a\s+[^>]*class\s*=\s*["\'][^"\']*\bnav-link\b[^"\']*["\'][^>]*href\s*=\s*["\']#?["\'][^>]*>',
        content,
        flags=re.IGNORECASE,
    )
    if fake_nav_links:
        issues.append(f"Header has {len(fake_nav_links)} placeholder nav <a> links; use router-link only for real routes")

    if not paths:
        issues.append("Header has no router-link navigation items")
    # de-duplicate
    return list(dict.fromkeys(issues))


def detect_header_typography_issues(content: str, expected_nav_count: int) -> List[str]:
    """
    Detect generic header typography/casing/spacing anomalies that usually lead to
    visible drift without hardcoding any site-specific style values.
    """
    issues: List[str] = []

    # Nav text extraction from router-link and plain anchors.
    nav_texts = re.findall(
        r'<(?:router-link|routerlink|a)\b[^>]*class\s*=\s*["\'][^"\']*\bnav-link\b[^"\']*["\'][^>]*>([\s\S]*?)</(?:router-link|routerlink|a)>',
        content,
        flags=re.IGNORECASE,
    )
    cleaned_texts: List[str] = []
    for text in nav_texts:
        plain = re.sub(r'<[^>]+>', '', text)
        plain = re.sub(r'\s+', ' ', plain).strip()
        if plain:
            cleaned_texts.append(plain)

    if cleaned_texts:
        duplicate_labels = [t for t in set(cleaned_texts) if cleaned_texts.count(t) > 1]
        if duplicate_labels:
            issues.append(f"Header has duplicate nav labels: {sorted(duplicate_labels)}")

        # Allow additional utility links (e.g. blog/events) as long as count is not extreme.
        if expected_nav_count > 0 and len(cleaned_texts) > expected_nav_count + 4:
            issues.append(f"Header nav item count too high: {len(cleaned_texts)} > expected {expected_nav_count}")

    css_blocks = re.findall(r'([^{}]+)\{([^{}]+)\}', content, flags=re.IGNORECASE)
    for raw_selector, decls in css_blocks:
        selector = raw_selector.lower()
        if "nav" not in selector and "header" not in selector:
            continue

        for m in re.finditer(r'letter-spacing\s*:\s*(-?\d+(?:\.\d+)?)px', decls, flags=re.IGNORECASE):
            px = float(m.group(1))
            if px >= 1.6:
                issues.append(f"Header letter-spacing too large in selector '{raw_selector.strip()}': {px}px")
                break

    return list(dict.fromkeys(issues))


async def _ensure_output_dependencies_for_preview(output_dir: Path) -> bool:
    """
    Ensure frontend deps exist for preview screenshots.
    """
    node_modules_dir = output_dir / "node_modules"
    if node_modules_dir.exists():
        return True

    import asyncio

    install_variants = [
        ["corepack", "pnpm", "install"],
        [r"C:\Program Files\nodejs\corepack.cmd", "pnpm", "install"],
        ["npm", "install"],
    ]

    for cmd in install_variants:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(output_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await proc.communicate()
            if proc.returncode == 0:
                return True
            msg = (err or out).decode("utf-8", errors="ignore").strip()
            if msg:
                print(f"Preview install failed ({' '.join(cmd)}): {msg[:300]}")
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"Preview install exception ({' '.join(cmd)}): {e}")
    return False


def _candidate_browser_paths() -> List[str]:
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    return [p for p in candidates if Path(p).exists()]


async def generate_compare_screenshots(
    task_dir: Path,
    output_dir: Path,
    screenshot_page_paths: List[str],
    host: str = "127.0.0.1",
    port: int = 4173,
) -> int:
    """
    Generate compare/gen_step_XX.png by launching the generated app and
    taking headless browser screenshots for each screenshot route.
    """
    import asyncio
    import socket

    if not screenshot_page_paths:
        return 0

    compare_dir = task_dir / "compare"
    compare_dir.mkdir(exist_ok=True)
    for old in compare_dir.glob("gen_step_*.png"):
        try:
            old.unlink()
        except Exception:
            pass

    browser_paths = _candidate_browser_paths()
    if not browser_paths:
        print("Compare screenshot skipped: no Edge/Chrome executable found.")
        return 0

    deps_ok = await _ensure_output_dependencies_for_preview(output_dir)
    if not deps_ok:
        print("Compare screenshot skipped: frontend dependencies are unavailable.")
        return 0

    dev_commands = [
        [r"C:\Program Files\nodejs\corepack.cmd", "pnpm", "exec", "vite", "--host", host, "--port", str(port)],
        ["corepack", "pnpm", "exec", "vite", "--host", host, "--port", str(port)],
        ["npm", "run", "dev", "--", "--host", host, "--port", str(port)],
    ]

    server_proc = None
    active_dev_cmd = None
    for cmd in dev_commands:
        try:
            p = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(output_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            server_proc = p
            active_dev_cmd = cmd
            break
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"Failed to start dev server command {' '.join(cmd)}: {e}")

    if server_proc is None:
        print("Compare screenshot skipped: failed to start dev server.")
        return 0

    async def wait_port_ready(timeout_sec: float = 40.0) -> bool:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_sec
        while loop.time() < deadline:
            if server_proc and server_proc.returncode is not None:
                return False
            sock = socket.socket()
            sock.settimeout(1.0)
            try:
                sock.connect((host, port))
                sock.close()
                return True
            except Exception:
                await asyncio.sleep(0.5)
            finally:
                try:
                    sock.close()
                except Exception:
                    pass
        return False

    try:
        ready = await wait_port_ready()
        if not ready:
            detail = ""
            if server_proc and server_proc.returncode is not None:
                try:
                    out, err = await server_proc.communicate()
                    text = (err or out).decode("utf-8", errors="ignore").strip()
                    if text:
                        detail = f" | {text[:300]}"
                except Exception:
                    pass
            print(f"Compare screenshot skipped: dev server not ready ({' '.join(active_dev_cmd or [])}){detail}.")
            return 0

        generated = 0
        browser_args_prefix = [
            "--headless",
            "--disable-gpu",
            "--hide-scrollbars",
            "--window-size=1920,1080",
            "--virtual-time-budget=4000",
        ]

        for idx, route_path in enumerate(screenshot_page_paths):
            route = route_path if route_path.startswith("/") else f"/{route_path}"
            url = f"http://{host}:{port}{route}"
            target = compare_dir / f"gen_step_{idx:02d}.png"

            ok = False
            for browser in browser_paths:
                cmd = [browser, *browser_args_prefix, f"--screenshot={str(target)}", url]
                try:
                    shot = await asyncio.create_subprocess_exec(
                        *cmd,
                        cwd=str(output_dir),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    _, _ = await shot.communicate()
                    if shot.returncode == 0 and target.exists():
                        ok = True
                        generated += 1
                        break
                except Exception:
                    continue

            if not ok:
                print(f"Failed to generate compare screenshot for route: {route}")

        print(f"Generated {generated}/{len(screenshot_page_paths)} compare screenshots.")
        return generated
    finally:
        if server_proc and server_proc.returncode is None:
            try:
                server_proc.terminate()
                await asyncio.wait_for(server_proc.wait(), timeout=8)
            except Exception:
                try:
                    server_proc.kill()
                except Exception:
                    pass
        if server_proc:
            try:
                await asyncio.wait_for(server_proc.communicate(), timeout=2)
            except Exception:
                pass


def evaluate_visual_similarity(
    task_dir: Path,
    screenshot_page_names: List[str],
    min_similarity_threshold: float = 0.90,
) -> Tuple[List[str], Dict[str, float]]:
    """
    Compare generated screenshots under task_dir/compare/gen_step_*.png with
    checkpoints/step_*.png. Returns low-similarity pages and raw page scores.
    This is optional and only runs when compare images already exist.
    """
    compare_dir = task_dir / "compare"
    checkpoints_dir = task_dir / "checkpoints"
    if not compare_dir.exists() or not checkpoints_dir.exists():
        return [], {}

    try:
        from PIL import Image, ImageChops, ImageStat  # type: ignore
    except Exception:
        return [], {}

    page_scores: Dict[str, float] = {}
    low_pages: List[str] = []

    for idx, page_name in enumerate(screenshot_page_names):
        ref_path = checkpoints_dir / f"step_{idx:02d}.png"
        gen_path = compare_dir / f"gen_step_{idx:02d}.png"
        if not ref_path.exists() or not gen_path.exists():
            continue
        try:
            with Image.open(ref_path) as ref_img, Image.open(gen_path) as gen_img:
                ref_rgb = ref_img.convert("RGB")
                gen_rgb = gen_img.convert("RGB").resize(ref_rgb.size)
                diff_img = ImageChops.difference(ref_rgb, gen_rgb)
                diff = ImageStat.Stat(diff_img)
                # Use per-channel mean absolute distance proxy (0~255), then map to similarity 0~1.
                # Keep it simple and dependency-free.
                mean_abs = sum(diff.mean) / max(len(diff.mean), 1)
                similarity = max(0.0, min(1.0, 1.0 - (mean_abs / 255.0)))
                page_scores[page_name] = similarity
                if similarity < min_similarity_threshold:
                    low_pages.append(f"{page_name} ({similarity:.3f})")
        except Exception:
            continue

    return low_pages, page_scores


def print_visual_fidelity_summary(
    screenshot_page_names: List[str],
    page_scores: Dict[str, float],
    min_similarity_threshold: float,
) -> None:
    """
    Print per-page and overall visual fidelity summary.
    """
    print("\n" + "=" * 60)
    print("Visual Fidelity Summary")
    print("=" * 60)
    print(f"Target threshold: {min_similarity_threshold:.0%}")

    available_scores: List[float] = []
    for page_name in screenshot_page_names:
        if page_name in page_scores:
            score = page_scores[page_name]
            available_scores.append(score)
            status = "PASS" if score >= min_similarity_threshold else "FAIL"
            print(f"  - {page_name}: {score:.2%} [{status}]")
        else:
            print(f"  - {page_name}: N/A (missing compare image)")

    if available_scores:
        overall = sum(available_scores) / len(available_scores)
        status = "PASS" if overall >= min_similarity_threshold else "FAIL"
        print(f"Overall fidelity: {overall:.2%} [{status}]")
    else:
        print("Overall fidelity: N/A (no visual comparison data)")


def _inject_missing_page_images(content: str, step_local_images: List[str]) -> str:
    """
    Inject fallback <img> tags for pages that only contain placeholders.
    """
    if not step_local_images:
        return content

    idx = [0]

    def next_img() -> str:
        img = step_local_images[idx[0] % len(step_local_images)]
        idx[0] += 1
        return f"/src/assets/images/{img}"

    modified = content

    # Contact-like placeholder
    modified = re.sub(
        r'<div class="placeholder-image">\s*(?:<!--[\s\S]*?-->\s*)?</div>',
        lambda _: f'<img class="placeholder-image" src="{next_img()}" alt="Contact image" />',
        modified,
        flags=re.IGNORECASE,
    )

    # Prints main cover area
    def replace_book_cover(match):
        inner = match.group(1)
        if re.search(r'<img\b', inner, re.IGNORECASE):
            return match.group(0)
        return f'<div class="book-cover">{inner}\n          <img class="book-cover-img" src="{next_img()}" alt="Book cover" />\n        </div>'

    modified = re.sub(
        r'<div class="book-cover">\s*([\s\S]*?)\s*</div>',
        replace_book_cover,
        modified,
        flags=re.IGNORECASE,
    )

    # Prints preview placeholders
    modified = re.sub(
        r'<div class="preview-img"></div>',
        lambda _: f'<img class="preview-img" src="{next_img()}" alt="Preview image" />',
        modified,
        flags=re.IGNORECASE,
    )
    modified = re.sub(
        r'<div class="preview-large"></div>',
        lambda _: f'<img class="preview-large" src="{next_img()}" alt="Preview image" />',
        modified,
        flags=re.IGNORECASE,
    )

    # Lightroom-like right panel without image
    def replace_image_section(match):
        inner = match.group(1)
        if re.search(r'<img\b', inner, re.IGNORECASE):
            return match.group(0)
        injected = f'<img class="section-image" src="{next_img()}" alt="Section image" />'
        return f'<div class="image-section">\n        {injected}\n{inner}\n      </div>'

    modified = re.sub(
        r'<div class="image-section">\s*([\s\S]*?)\s*</div>',
        replace_image_section,
        modified,
        flags=re.IGNORECASE,
    )

    # Fallback: no image tag at all, insert one near the top of template content
    if not view_has_image_reference(modified):
        modified = re.sub(
            r'(<template>\s*<div[^>]*>)',
            lambda m: m.group(1) + f'\n    <img class="auto-filled-image" src="{next_img()}" alt="Page image" />',
            modified,
            count=1,
            flags=re.IGNORECASE,
        )

    return modified


def build_page_analysis_prompt(image_data_urls):
    """构建让AI分析截图并返回页面名称和路由的提示词"""
    num_screenshots = len(image_data_urls)
    
    system_prompt = "You are an expert frontend developer and UI/UX analyst.\n\n"
    system_prompt += "Your task is to analyze the provided screenshots and determine the page names and routes for a multi-page website.\n\n"
    system_prompt += "# IMPORTANT GUIDELINES:\n\n"
    system_prompt += "1. Look at each screenshot carefully and identify what page it represents (e.g., Home, Gallery, About, Contact, etc.)\n"
    system_prompt += "2. The page names should be descriptive but concise, using PascalCase (e.g., PhotoGallery, AboutUs, ContactForm)\n"
    system_prompt += "3. CRITICAL: Extract the EXACT route paths from the navigation menu in the screenshots! Look for router-link to=\"...\" or href=\"...\" attributes - use those EXACT paths as routePath!\n"
    system_prompt += "4. Home page (path '/') is ALWAYS an empty page - it does NOT correspond to any screenshot!\n"
    system_prompt += "5. Each screenshot corresponds to ONE additional page\n"
    system_prompt += "6. Look at navigation menus, page titles, content, and any text in the screenshots to determine the page names\n"
    system_prompt += "7. If you can't determine a clear page name, use a generic name like Page1, Page2, etc.\n"
    system_prompt += "8. ABSOLUTELY CRITICAL: The routePath MUST MATCH EXACTLY what's in the navigation menu links! This is the most important rule!\n\n"
    system_prompt += "# OUTPUT FORMAT - MUST FOLLOW EXACTLY!\n\n"
    system_prompt += "You MUST output a valid JSON object in the following format:\n\n"
    system_prompt += "{\n"
    system_prompt += "  \"pages\": [\n"
    system_prompt += "    {\n"
    system_prompt += "      \"pageName\": \"PageName\",\n"
    system_prompt += "      \"routePath\": \"/page-path\"\n"
    system_prompt += "    }\n"
    system_prompt += "  ]\n"
    system_prompt += "}\n\n"
    system_prompt += "# EXAMPLE OUTPUT:\n\n"
    system_prompt += "{\n"
    system_prompt += "  \"pages\": [\n"
    system_prompt += "    {\n"
    system_prompt += "      \"pageName\": \"PhotoGallery\",\n"
    system_prompt += "      \"routePath\": \"/photo-gallery\"\n"
    system_prompt += "    },\n"
    system_prompt += "    {\n"
    system_prompt += "      \"pageName\": \"AboutUs\",\n"
    system_prompt += "      \"routePath\": \"/about-us\"\n"
    system_prompt += "    }\n"
    system_prompt += "  ]\n"
    system_prompt += "}\n\n"
    system_prompt += "# CRITICAL RULES:\n"
    system_prompt += "- ONLY output JSON - NO other text or explanations\n"
    system_prompt += "- The JSON MUST be valid\n"
    system_prompt += "- Do NOT include Home page in the pages array - Home is always '/' and is handled separately\n"
    system_prompt += f"- You MUST include EXACTLY {num_screenshots} pages in the pages array\n"
    system_prompt += "- The order of pages MUST match the order of the screenshots\n"
    
    user_prompt = f"Please analyze these {num_screenshots} screenshots and determine the page names and routes.\n\n"
    user_prompt += "Home page (path '/') is always empty and does NOT correspond to any screenshot.\n"
    user_prompt += "Each screenshot corresponds to one additional page.\n\n"
    user_prompt += "Output ONLY JSON as specified."
    
    content = []
    for i in range(len(image_data_urls)):
        content.append({
            "type": "text",
            "text": f"Screenshot {i+1}:"
        })
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


def parse_page_analysis_response(ai_response):
    """解析AI的页面分析响应，提取页面名称和路由"""
    import re
    import json
    
    try:
        json_match = re.search(r'\{[\s\S]*\}', ai_response)
        if json_match:
            json_str = json_match.group(0)
            data = json.loads(json_str)
            
            page_names = []
            page_paths = []
            
            for page in data.get("pages", []):
                page_names.append(page.get("pageName", f"Page{len(page_names)+1}"))
                page_paths.append(page.get("routePath", f"/page{len(page_paths)+1}"))
            
            return page_names, page_paths
    except Exception as e:
        print(f"Error parsing page analysis response: {e}")
    
    return [], []


def build_vue3_prompt_from_page_info(page_names, page_paths):
    """从AI返回的页面信息构建prompt所需的字符串"""
    num_pages = len(page_names)
    
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
    
    return page_components_str, page_routes_str, pages_description_str


def build_vue3_prompt_messages(image_data_urls, page_names, page_paths, page_components_str, page_routes_str, pages_description_str, num_pages, assets_image_data_urls=None, assets_image_filenames=None, step_resources=None, url_to_local_path=None, page_to_step_index=None):
    
    # 使用已经确定的页面名称和路由（page_names和page_paths已经包含了Home）
    num_screenshots = len(image_data_urls)
    
    # 从 page_names 和 page_paths 中分离出 Home 和截图页面
    screenshot_page_names = page_names[1:]  # 除了Home之外的页面
    screenshot_page_paths = page_paths[1:]
    
    # 构建完整的页面组件列表和路由列表
    full_page_components_list = ["- src/views/Home.vue"]
    for pn in screenshot_page_names:
        full_page_components_list.append(f"- src/views/{pn}.vue")
    full_page_components_str = "\n".join(full_page_components_list)
    
    full_page_routes_list = ["- / -> Home"]
    for i in range(len(screenshot_page_names)):
        full_page_routes_list.append(f"- {screenshot_page_paths[i]} -> {screenshot_page_names[i]}")
    full_page_routes_str = "\n".join(full_page_routes_list)
    
    system_prompt = "You are an expert frontend developer specializing in Vue 3 and Vite.\n\n"
    system_prompt += "Your task is to recreate a website from multiple screenshots as a Vue 3 + Vite project with Vue Router.\n\n"
    system_prompt += "# Multi-Page App - IMPORTANT!\n\n"
    system_prompt += f"- There are {num_screenshots} screenshots, each representing a different page of the website\n"
    system_prompt += f"- Use Vue Router to implement page navigation between these {num_pages} pages\n"
    system_prompt += f"- Page names and routes have been determined from the screenshots:\n"
    system_prompt += pages_description_str + "\n\n"
    system_prompt += "# Output Format\n\n"
    system_prompt += "You MUST output multiple files using the following format:\n\n"
    system_prompt += "<file path=\"index.html\">\n<!DOCTYPE html>\n<html lang=\"en\">\n  <head>\n    <meta charset=\"UTF-8\" />\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n    <title>App</title>\n  </head>\n  <body>\n    <div id=\"app\"></div>\n    <script type=\"module\" src=\"/src/main.ts\"></script>\n  </body>\n</html>\n</file>\n\n"
    system_prompt += "<file path=\"package.json\">\n{\n  \"name\": \"vue3-app\",\n  \"private\": true,\n  \"version\": \"0.0.0\",\n  \"type\": \"module\",\n  \"scripts\": {\n    \"dev\": \"vite\",\n    \"build\": \"vue-tsc && vite build\",\n    \"preview\": \"vite preview\"\n  },\n  \"dependencies\": {\n    \"vue\": \"^3.4.0\",\n    \"vue-router\": \"^4.2.0\"\n  },\n  \"devDependencies\": {\n    \"@vitejs/plugin-vue\": \"^5.0.0\",\n    \"typescript\": \"~5.4.5\",\n    \"vite\": \"^5.0.0\",\n    \"vue-tsc\": \"^2.0.29\"\n  }\n}\n</file>\n\n"
    system_prompt += "<file path=\"vite.config.ts\">\nimport { defineConfig } from 'vite'\nimport vue from '@vitejs/plugin-vue'\n\nexport default defineConfig({\n  plugins: [vue()],\n})\n</file>\n\n"
    system_prompt += "<file path=\"tsconfig.json\">\n{\n  \"compilerOptions\": {\n    \"target\": \"ES2020\",\n    \"useDefineForClassFields\": true,\n    \"module\": \"ESNext\",\n    \"lib\": [\"ES2020\", \"DOM\", \"DOM.Iterable\"],\n    \"skipLibCheck\": true,\n    \"moduleResolution\": \"bundler\",\n    \"allowImportingTsExtensions\": true,\n    \"resolveJsonModule\": true,\n    \"isolatedModules\": true,\n    \"noEmit\": true,\n    \"jsx\": \"preserve\",\n    \"strict\": true,\n    \"noUnusedLocals\": false,\n    \"noUnusedParameters\": false,\n    \"noFallthroughCasesInSwitch\": true\n  },\n  \"include\": [\"src/**/*.ts\", \"src/**/*.tsx\", \"src/**/*.vue\"],\n  \"references\": [{ \"path\": \"./tsconfig.node.json\" }]\n}\n</file>\n\n"
    system_prompt += "<file path=\"tsconfig.node.json\">\n{\n  \"compilerOptions\": {\n    \"composite\": true,\n    \"skipLibCheck\": true,\n    \"module\": \"ESNext\",\n    \"moduleResolution\": \"bundler\",\n    \"allowSyntheticDefaultImports\": true\n  },\n  \"include\": [\"vite.config.ts\"]\n}\n</file>\n\n"
    system_prompt += "<file path=\"src/main.ts\">\nimport { createApp } from 'vue'\nimport App from './App.vue'\nimport router from './router'\n\ncreateApp(App).use(router).mount('#app')\n</file>\n\n"
    system_prompt += "<file path=\"src/router/index.ts\">\nimport { createRouter, createWebHistory } from 'vue-router'\nimport Home from '../views/Home.vue'\n"
    for pn in screenshot_page_names:
        system_prompt += f"import {pn} from '../views/{pn}.vue'\n"
    system_prompt += "\nconst routes = [\n  {\n    path: '/',\n    name: 'Home',\n    component: Home\n  },\n"
    for i in range(len(screenshot_page_names)):
        system_prompt += "  {\n"
        system_prompt += f"    path: '{screenshot_page_paths[i]}',\n"
        system_prompt += f"    name: '{screenshot_page_names[i]}',\n"
        system_prompt += f"    component: {screenshot_page_names[i]}\n"
        system_prompt += "  },\n"
    system_prompt += "]\n\nconst router = createRouter({\n  history: createWebHistory(),\n  routes\n})\n\nexport default router\n</file>\n\n"
    system_prompt += "<file path=\"src/App.vue\">\n<script setup lang=\"ts\">\nimport Header from './components/Header.vue'\n</script>\n\n<template>\n  <div id=\"app\">\n    <Header />\n    <router-view />\n  </div>\n</template>\n\n<style>\n#app {\n  font-family: Avenir, Helvetica, Arial, sans-serif;\n  -webkit-font-smoothing: antialiased;\n  -moz-osx-font-smoothing: grayscale;\n}\n</style>\n</file>\n\n"
    # Home 页面是空的，预先生成
    system_prompt += "<file path=\"src/views/Home.vue\">\n<script setup lang=\"ts\">\n</script>\n\n<template>\n  <div class=\"home\">\n  </div>\n</template>\n\n<style scoped>\n</style>\n</file>\n\n"
    # 为每个截图生成一个空模板，AI 将填充内容
    for pn in screenshot_page_names:
        system_prompt += f"<file path=\"src/views/{pn}.vue\">\n<script setup lang=\"ts\">\n</script>\n\n<template>\n</template>\n\n<style scoped>\n</style>\n</file>\n\n"
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
    system_prompt += "10. Use relative paths for assets: /src/assets/image.png\n"
    system_prompt += "11. Extract interaction logic from video.mp4 and implement corresponding interactive behaviors\n"
    system_prompt += "12. Replace image paths in Vue components with corresponding images from assets directory\n"
    system_prompt += "13. IMPORTANT: Home page (path '/') MUST be an empty page with no content - it does NOT correspond to any screenshot!\n"
    system_prompt += "14. IMPORTANT: Screenshots do NOT include the Home page - Home is always empty!\n"
    system_prompt += "15. IMPORTANT: Each Vue file MUST have EXACTLY ONE <script setup lang=\"ts\"> tag - NEVER have multiple script tags in the same file!\n"
    system_prompt += "16. CRITICAL: In the Header navigation menu, ALL router-link to=\"...\" attributes MUST MATCH EXACTLY the route paths provided above! This is the most important rule!\n"
    system_prompt += "17. CRITICAL: When using v-for loops with images, ALWAYS bind :src=\"photo\" (or the correct variable name from the loop) to use the variable from the loop! NEVER hardcode a static src when looping through an image array - this will make all images the same!\n"
    system_prompt += "18. CRITICAL: NEVER create img tags without a src attribute! Every img tag MUST have a src attribute with a valid image path from the assets/images directory!\n"
    system_prompt += "19. CRITICAL: When using v-for loops, the :key attribute MUST be properly closed! It should look like :key=\"`xxx-${index}`\" with both backticks and quotes closed!\n"
    system_prompt += "20. CRITICAL: Match typography and spacing scale to screenshot (font-size, line-height, letter-spacing, paddings/margins, gaps). Do NOT normalize to arbitrary defaults.\n"
    system_prompt += "21. CRITICAL: Preserve logo-vs-nav visual proportion from screenshot. Do NOT inject fixed-width logo or fixed nav font/spacing unless screenshot clearly shows it.\n"
    system_prompt += "22. CRITICAL: Keep exact nav text casing/weight/spacing seen in screenshot; avoid blanket uppercase transformation unless it is explicitly visible.\n\n"
    system_prompt += f"# YOU MUST CREATE THESE {num_pages} PAGE COMPONENTS:\n"
    system_prompt += full_page_components_str + "\n\n"
    system_prompt += f"# AND YOU MUST CONFIGURE THESE {num_pages} ROUTES IN src/router/index.ts:\n"
    system_prompt += full_page_routes_str + "\n\n"
    system_prompt += "# ABSOLUTELY CRITICAL - DO NOT SKIP!\n\n"
    system_prompt += f"- The number of page components in src/views/ MUST EXACTLY match the total number of pages ({num_pages})\n"
    system_prompt += f"- You MUST create ALL {num_pages} page components, NOT just some of them\n"
    system_prompt += f"- Each screenshot corresponds to EXACTLY one page component\n"
    system_prompt += "- Do NOT comment out any imports in router/index.ts\n"
    system_prompt += "- Do NOT skip any page components\n"
    system_prompt += f"- You MUST create ALL {num_pages} .vue files in src/views/\n"
    system_prompt += f"- YOU MUST CREATE: {full_page_components_str}\n\n"
    system_prompt += "# IMAGE HANDLING - ABSOLUTELY CRITICAL - DO NOT IGNORE!\n\n"
    system_prompt += "- DO NOT use visual recognition to match images!\n"
    system_prompt += "- Use ONLY the EXACT list of images provided for each page (below)\n"
    system_prompt += "- Each page has a PRECISE list of images that should be used for that page\n"
    system_prompt += "- DO NOT make up any filenames, DO NOT guess, DO NOT do visual matching\n"
    system_prompt += "- ONLY use the filenames from the page-specific list provided below\n"
    system_prompt += "- Use relative paths like: /src/assets/images/filename.jpg\n"
    system_prompt += "- DO NOT use external image URLs - ALL images must come from local assets\n"
    system_prompt += "- CRITICAL: Keep the number of image slots per section/list consistent with the screenshot; do NOT add/remove gallery item count\n"
    
    if assets_image_filenames:
        system_prompt += "# ALL AVAILABLE ASSET IMAGES:\n"
        for idx, filename in enumerate(assets_image_filenames):
            system_prompt += f"- Asset Image {idx+1}: {filename}\n"
        system_prompt += "\n"
    
    if step_resources and url_to_local_path and page_to_step_index:
        system_prompt += "# PAGE-SPECIFIC IMAGE LISTS (USE THESE EXACTLY!):\n"
        # 复用 images_dir 路径（此时 output_dir 可能还不存在，用 task_dir 的 assets）
        # 但 _build_step_image_list 需要 images_dir 存在，这里我们只做去重和选质量，
        # 不检查文件存在性（因为 output 还没创建，但 assets 源目录是存在的）
        screenshot_page_names = page_names[1:]
        # 使用 task_dir 中的 assets/images 目录来验证
        prompt_images_dir = None
        # 尝试从 assets_image_filenames 推断路径
        # 这里简化处理：直接做去重和选质量，不验证文件存在
        for page_name in screenshot_page_names:
            if page_name in page_to_step_index:
                step_index = page_to_step_index[page_name]
                step_image_urls = step_resources.get(step_index, [])
                # 去重 + 选最高质量
                exclude_keywords = ['logo', 'icon', 'favicon', 'cart', '.gif', 'tracking', 'p.gif']
                candidates: Dict[str, List[tuple]] = {}
                for url in step_image_urls:
                    if url not in url_to_local_path:
                        continue
                    filename = Path(url_to_local_path[url]).name
                    lower = filename.lower()
                    if any(kw.lower() in lower for kw in exclude_keywords):
                        continue
                    base_name = filename.split('_format_')[0] if '_format_' in filename else filename
                    size_hint = 0
                    fmt_match = re.search(r'_format_(\d+)w', filename)
                    if fmt_match:
                        size_hint = int(fmt_match.group(1))
                    else:
                        size_hint = 99999
                    if base_name not in candidates:
                        candidates[base_name] = []
                    candidates[base_name].append((filename, size_hint))
                step_local_images = []
                for base, variants in candidates.items():
                    variants.sort(key=lambda x: x[1], reverse=True)
                    step_local_images.append(variants[0][0])
                system_prompt += f"- {page_name} page images:\n"
                for img_file in step_local_images:
                    system_prompt += f"  - /src/assets/images/{img_file}\n"
        system_prompt += "\n"
    
    system_prompt += "# Important\n\n"
    system_prompt += "- Output ALL files using the <file path=\"...\"> format shown above\n"
    system_prompt += "- Each file must be wrapped in <file path=\"...\">...</file>\n"
    system_prompt += "- Do NOT use markdown code blocks\n"
    system_prompt += "- Make sure the recreated pages look identical to the screenshots\n"
    system_prompt += "- Home page (path '/') is ALWAYS empty - it does NOT come from any screenshot\n"
    system_prompt += "- Create additional page components in src/views/ for each screenshot\n"
    system_prompt += f"- DO NOT FORGET TO CREATE ALL {num_pages} PAGE COMPONENTS AND ROUTES!\n"
    system_prompt += f"- DO NOT FORGET TO USE LOCAL IMAGES FROM /src/assets/images/\n"

    user_prompt = f"You have been given {num_screenshots} screenshots, each representing a different page of the website.\n\n"
    user_prompt += "Home page (path '/') is ALWAYS empty - it does NOT come from any screenshot.\n"
    user_prompt += "Page names and routes have been determined from the screenshots - use the exact names and routes provided.\n\n"
    user_prompt += "Please recreate the ENTIRE website as a Vue 3 + Vite project with Vue Router.\n\n"
    user_prompt += "Make sure:\n"
    user_prompt += "1. Each screenshot becomes its own page component in src/views/\n"
    user_prompt += "2. Create a router configuration in src/router/index.ts\n"
    user_prompt += "3. Add a navigation menu to switch between pages\n"
    user_prompt += "4. Recreate each page EXACTLY as shown in its screenshot\n"
    user_prompt += "5. Use Vue Router for navigation\n"
    user_prompt += f"6. YOU MUST CREATE EXACTLY {num_pages} PAGE COMPONENTS IN src/views/ - {full_page_components_str}\n"
    user_prompt += "7. Extract interaction logic from video.mp4 and implement corresponding interactive behaviors\n"
    user_prompt += "8. REPLACE ALL IMAGES WITH LOCAL FILES FROM /src/assets/images/ - DO NOT USE EXTERNAL URLs!\n"

    content = []

    # GLM 限制图片数量，需要限制 assets 图片
    max_assets_images = 10  # GLM 限制
    assets_to_send = []

    # 首先添加所有 assets 图片供 AI 视觉识别（限制数量）
    if assets_image_data_urls and assets_image_filenames:
        # 选择前 N 张图片（优先选择尺寸大的）
        for idx, (img_data_url, filename) in enumerate(zip(assets_image_data_urls, assets_image_filenames)):
            if idx >= max_assets_images:
                break
            assets_to_send.append((filename, img_data_url))

        for filename, img_data_url in assets_to_send:
            content.append({
                "type": "text",
                "text": f"Asset Image: {filename}"
            })
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": img_data_url,
                    "detail": "high"
                }
            })

        remaining = len(assets_image_filenames) - max_assets_images
        if remaining > 0:
            content.append({
                "type": "text",
                "text": f"\n--- END OF ASSET IMAGES ({remaining} more images available) ---\n"
            })

        content.append({
            "type": "text",
            "text": "\n--- END OF ASSET IMAGES ---\n\nNow, here are the page screenshots to recreate:\n"
        })
    
    # 然后添加页面截图
    for i in range(len(image_data_urls)):
        content.append({
            "type": "text",
            "text": f"Page Screenshot {i+1}: {screenshot_page_names[i]} page"
        })
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


def build_vue3_prompt(image_data_url: str):
    """
    Backward-compatible wrapper for legacy single-screenshot callers.

    The newer pipeline is multi-page and requires precomputed page info.
    For legacy usage we keep a single screenshot page called Page1.
    """
    screenshot_page_names = ["Page1"]
    screenshot_page_paths = ["/page1"]
    page_components_str, page_routes_str, pages_description_str = build_vue3_prompt_from_page_info(
        screenshot_page_names,
        screenshot_page_paths
    )
    page_names = ["Home"] + screenshot_page_names
    page_paths = ["/"] + screenshot_page_paths

    return build_vue3_prompt_messages(
        image_data_urls=[image_data_url],
        page_names=page_names,
        page_paths=page_paths,
        page_components_str=page_components_str,
        page_routes_str=page_routes_str,
        pages_description_str=pages_description_str,
        num_pages=len(page_names)
    )


def build_correction_prompt(image_data_urls, page_names, page_paths, missing_pages, missing_core_files, router_valid, app_valid, main_valid, package_valid, missing_dependencies, missing_image_pages, low_image_count_pages, header_style_issues, header_route_issues, header_typography_issues, low_visual_fidelity_pages, min_visual_similarity, existing_files, num_pages):
    """构建补齐缺失页面的提示词"""
    
    system_prompt = "You are an expert frontend developer specializing in Vue 3 and Vite.\n\n"
    system_prompt += "Your task is to COMPLETE or FIX the missing/corrupted files for a Vue 3 + Vite project.\n\n"
    system_prompt += "# IMPORTANT - YOU MUST GENERATE/REPAIR ONLY WHAT'S MISSING!\n\n"
    
    issues = []
    if missing_pages:
        issues.append(f"- {len(missing_pages)} page components are missing: {missing_pages}")
    if missing_core_files:
        issues.append(f"- Missing core files: {missing_core_files}")
    if not router_valid:
        issues.append("- Router file is incomplete or missing imports")
    if not app_valid:
        issues.append("- App.vue is missing <router-view />")
    if not main_valid:
        issues.append("- main.ts is missing router setup (needs to import and use router)")
    if not package_valid:
        issues.append(f"- package.json missing dependencies: {missing_dependencies}")
    if missing_image_pages:
        issues.append(f"- These pages have placeholder content and are missing actual images: {missing_image_pages}")
    if low_image_count_pages:
        issues.append(f"- These pages have too few image references: {low_image_count_pages}")
    if header_style_issues:
        issues.append(f"- Header styling is visually drifted from screenshot: {header_style_issues}")
    if header_route_issues:
        issues.append(f"- Header contains invalid route links not in page set: {header_route_issues}")
    if header_typography_issues:
        issues.append(f"- Header typography/casing/spacing has visual drift: {header_typography_issues}")
    if low_visual_fidelity_pages:
        issues.append(
            f"- These pages are below visual similarity threshold ({min_visual_similarity:.0%}): {low_visual_fidelity_pages}"
        )
    
    for issue in issues:
        system_prompt += issue + "\n"
    system_prompt += "\n"
    
    system_prompt += "# Files already generated:\n"
    for file_path in sorted(existing_files.keys()):
        system_prompt += f"- {file_path}\n"
    system_prompt += "\n"
    
    system_prompt += "# FILES YOU MUST GENERATE/REPAIR:\n"
    repair_pages = []
    for page_name in missing_pages + missing_image_pages:
        if page_name not in repair_pages:
            repair_pages.append(page_name)
    for page_stat in low_image_count_pages:
        page_name = page_stat.split(" (")[0]
        if page_name not in repair_pages:
            repair_pages.append(page_name)
    for page_stat in low_visual_fidelity_pages:
        page_name = page_stat.split(" (")[0]
        if page_name not in repair_pages:
            repair_pages.append(page_name)

    for page_name in repair_pages:
        system_prompt += f"- src/views/{page_name}.vue\n"
    for core_file in missing_core_files:
        system_prompt += f"- {core_file}\n"
    if not router_valid:
        system_prompt += "- src/router/index.ts (complete or fix it)\n"
    if not app_valid:
        system_prompt += "- src/App.vue (add <router-view />)\n"
    if not main_valid:
        system_prompt += "- src/main.ts (fix router setup)\n"
    if not package_valid:
        system_prompt += "- package.json (add missing dependencies)\n"
    if header_style_issues:
        system_prompt += "- src/components/Header.vue (fix logo/nav typography/spacing proportion to match screenshot)\n"
    if header_route_issues:
        system_prompt += "- src/components/Header.vue (remove/fix invalid nav routes; keep only expected route set)\n"
    if header_typography_issues:
        system_prompt += "- src/components/Header.vue (fix nav text casing/letter-spacing/item count to match screenshot)\n"
    system_prompt += "\n"
    
    if not main_valid:
        system_prompt += "# CORRECT main.ts EXAMPLE:\n\n"
        system_prompt += "<file path=\"src/main.ts\">\nimport { createApp } from 'vue'\nimport App from './App.vue'\nimport router from './router'\n\ncreateApp(App).use(router).mount('#app')\n</file>\n\n"
    
    if not package_valid:
        system_prompt += "# COMPLETE package.json EXAMPLE:\n\n"
    system_prompt += "<file path=\"package.json\">\n{\n  \"name\": \"vue3-app\",\n  \"private\": true,\n  \"version\": \"0.0.0\",\n  \"type\": \"module\",\n  \"scripts\": {\n    \"dev\": \"vite\",\n    \"build\": \"vue-tsc && vite build\",\n    \"preview\": \"vite preview\"\n  },\n  \"dependencies\": {\n    \"vue\": \"^3.4.0\",\n    \"vue-router\": \"^4.2.0\"\n  },\n  \"devDependencies\": {\n    \"@vitejs/plugin-vue\": \"^5.0.0\",\n    \"typescript\": \"~5.4.5\",\n    \"vite\": \"^5.0.0\",\n    \"vue-tsc\": \"^2.0.29\"\n  }\n}\n</file>\n\n"
    
    system_prompt += "# Output Format\n\n"
    system_prompt += "You MUST output the files using the following format:\n\n"
    system_prompt += "<file path=\"src/views/PageName.vue\">\n<script setup lang=\"ts\">\n</script>\n\n<template>\n</template>\n\n<style scoped>\n</style>\n</file>\n\n"
    
    system_prompt += "# Important Guidelines - CRITICAL!\n\n"
    system_prompt += "1. ONLY generate/repair the files listed above\n"
    system_prompt += "2. DO NOT regenerate files that are already correct\n"
    system_prompt += f"3. For each missing page, recreate it EXACTLY as shown in its corresponding screenshot\n"
    system_prompt += "4. Make sure App.vue has <router-view />\n"
    system_prompt += "5. Make sure router/index.ts imports ALL page components\n"
    system_prompt += "6. Pay attention to colors, fonts, spacing, layout, and all details\n"
    system_prompt += "7. Write clean, modern Vue 3 code with Composition API\n"
    system_prompt += "8. Use TypeScript for type safety\n"
    system_prompt += "9. All static assets should be in src/assets/\n"
    system_prompt += "10. Use relative paths for assets: /src/assets/image.png\n"
    system_prompt += "11. Replace image paths with corresponding images from /src/assets/images/\n"
    system_prompt += "12. DO NOT use external image URLs - ALL images must come from local assets\n"
    system_prompt += "13. CRITICAL: NEVER output placeholder-only blocks for image areas. Every visual image area must render a real <img> from /src/assets/images/\n"
    system_prompt += "14. CRITICAL: Ensure page image count is sufficient for the screenshot complexity (do not output only 1 token image for image-heavy pages)\n"
    system_prompt += "15. CRITICAL: Keep image slot count stable per section/list (do NOT expand or shrink gallery arrays when repairing image paths)\n"
    system_prompt += "16. CRITICAL: Match typography and spacing to screenshot (font-size, line-height, letter-spacing, paddings/margins, gaps) instead of generic defaults.\n"
    system_prompt += "17. CRITICAL: Keep logo-vs-navigation proportion consistent with screenshot; avoid fixed logo/nav tuning that changes original balance.\n\n"
    system_prompt += "18. CRITICAL: Keep nav text casing and letter-spacing faithful to screenshot (match what is shown, do not normalize automatically).\n\n"
    
    user_prompt = f"Please generate/repair ONLY the missing/corrupted files:\n\n"
    for page_name in repair_pages:
        if page_name in page_names:
            idx = page_names.index(page_name)
            screenshot_no = idx if idx > 0 else 1
            user_prompt += f"- {page_name} page ({page_paths[idx]}) - corresponds to screenshot {screenshot_no}\n"
        else:
            user_prompt += f"- {page_name} page\n"
    for core_file in missing_core_files:
        user_prompt += f"- {core_file}\n"
    if not router_valid:
        user_prompt += "- Complete/fix src/router/index.ts\n"
    if not app_valid:
        user_prompt += "- Fix App.vue to include <router-view />\n"
    if not main_valid:
        user_prompt += "- Fix main.ts to properly setup router\n"
    if not package_valid:
        user_prompt += "- Fix package.json to add missing dependencies\n"
    if header_style_issues:
        user_prompt += "- Fix src/components/Header.vue to match screenshot logo/nav size and spacing proportions\n"
    if header_route_issues:
        user_prompt += f"- Fix src/components/Header.vue nav links; ONLY use these paths: {page_paths}\n"
    if header_typography_issues:
        user_prompt += "- Fix src/components/Header.vue nav casing/letter-spacing and remove duplicated nav labels\n"
    if low_visual_fidelity_pages:
        user_prompt += f"- Improve visual fidelity for these pages to >= {min_visual_similarity:.0%}: {low_visual_fidelity_pages}\n"
    user_prompt += "\nIMPORTANT:\n"
    user_prompt += "- ONLY generate/repair the files listed above\n"
    user_prompt += "- DO NOT regenerate any existing correct files\n"
    user_prompt += "- Use the <file path=\"...\"> format for each file\n"
    
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


async def call_openai(messages, api_key, model="gpt-4-vision-preview"):
    """Backward-compatible wrapper for legacy callers."""
    return await call_llm(
        messages=messages,
        api_key=api_key,
        model=model,
        provider="openai"
    )


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


def fix_invalid_image_sources(content: str, output_dir: Path, fallback_images: List[str] = None) -> str:
    """
    修复内容中无效的图片 src：
    1. 空 src -> 用 fallback 填充或删除属性
    2. 指向不存在本地文件的 src -> 用 fallback 替换
    3. 外部 URL -> 用 fallback 替换
    """
    images_dir = output_dir / "src" / "assets" / "images"
    if not images_dir.exists():
        return content

    img_pattern = r'src\s*=\s*(["\'])(.*?)\1'
    fb_idx = [0]

    def fix_src(match):
        quote = match.group(1)
        img_path = match.group(2)

        # 空 src
        if not img_path or not img_path.strip():
            if fallback_images:
                selected = fallback_images[fb_idx[0] % len(fallback_images)]
                fb_idx[0] += 1
                return f'src={quote}/src/assets/images/{selected}{quote}'
            return ''

        # 已是有效本地图片
        if img_path.startswith('/src/assets/images/'):
            filename = img_path.split('/')[-1]
            if (images_dir / filename).exists():
                return f'src={quote}{img_path}{quote}'

        # 无效路径：用 fallback 替换
        if fallback_images:
            selected = fallback_images[fb_idx[0] % len(fallback_images)]
            fb_idx[0] += 1
            new_path = f'/src/assets/images/{selected}'
            print(f"  Fixed invalid src: {img_path} -> {new_path}")
            return f'src={quote}{new_path}{quote}'

        # 无 fallback，删除 src
        return ''

    modified_content, count = re.subn(img_pattern, fix_src, content)
    if count > 0:
        print(f"  Fixed {count} invalid image sources")

    return modified_content


def normalize_tsconfig_content(content: str) -> str:
    """
    Normalize generated tsconfig to avoid build failures caused by strict unused checks.
    """
    try:
        data = json.loads(content)
    except Exception:
        return content

    compiler_options = data.get("compilerOptions")
    if not isinstance(compiler_options, dict):
        return content

    changed = False
    if compiler_options.get("noUnusedLocals") is not False:
        compiler_options["noUnusedLocals"] = False
        changed = True
    if compiler_options.get("noUnusedParameters") is not False:
        compiler_options["noUnusedParameters"] = False
        changed = True

    if not changed:
        return content

    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def enforce_header_logo_image(content: str, output_dir: Path) -> str:
    """
    Force Header.vue logo area to use a real local logo image instead of a drawn placeholder/SVG.
    """
    images_dir = output_dir / "src" / "assets" / "images"
    if not images_dir.exists():
        return content

    image_files = [
        p for p in images_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".svg"}
    ]
    if not image_files:
        return content

    def score_logo_candidate(path: Path) -> int:
        name = path.name.lower()
        score = 0
        if "logo" in name:
            score += 100
        if "brand" in name:
            score += 50
        if "icon" in name:
            score += 15
        if "favicon" in name:
            score -= 20
        if "tracking" in name or "p.gif" in name:
            score -= 100
        return score

    best_logo = sorted(image_files, key=lambda p: score_logo_candidate(p), reverse=True)[0]
    if score_logo_candidate(best_logo) < 30:
        # No high-confidence logo candidate, skip to avoid wrong hard replacement.
        return content

    logo_path = f"/src/assets/images/{best_logo.name}"
    modified = content

    has_logo_container = bool(re.search(r'class="[^"]*(?:logo|brand)[^"]*"', modified, re.IGNORECASE))
    if not has_logo_container:
        return content

    # Fix existing logo-like <img> tags that are missing src.
    def fix_logo_img_without_src(match):
        attrs = match.group(1)
        lower_attrs = attrs.lower()
        is_logo_img = ("logo" in lower_attrs) or ("brand" in lower_attrs)
        has_src = bool(re.search(r'\bsrc\s*=', attrs, flags=re.IGNORECASE))
        if is_logo_img and not has_src:
            return f'<img src="{logo_path}" {attrs}>'
        return match.group(0)

    modified = re.sub(r'<img\s+([^>]*?)>', fix_logo_img_without_src, modified, flags=re.IGNORECASE)

    # If there is still an <img> without src in Header, patch the first one with logo path.
    modified = re.sub(
        r'<img(?![^>]*\bsrc\s*=)([^>]*?)>',
        lambda m: f'<img src="{logo_path}" {m.group(1)}>',
        modified,
        count=1,
        flags=re.IGNORECASE,
    )

    # If an <svg> exists in logo area, replace with img.
    # Keep this non-opinionated: no fixed width/gap/font overrides here.
    modified = re.sub(
        r'<svg[\s\S]*?</svg>',
        f'<img class="logo-image" src="{logo_path}" alt="Site logo" />',
        modified,
        count=1,
        flags=re.IGNORECASE,
    )

    # If still no logo img in template, inject one into common logo wrappers.
    if '/src/assets/images/' not in modified:
        modified = re.sub(
            r'(<(?:div|a|router-link)\s+[^>]*class="[^"]*\blogo[^"]*"[^>]*>\s*)',
            r'\1' + f'<img class="logo-image" src="{logo_path}" alt="Site logo" />',
            modified,
            count=1,
            flags=re.IGNORECASE,
        )

    # Remove synthesized text-logo blocks when image logo is used.
    # Keep this generic: remove common brand-text wrappers tied to logo area.
    modified = re.sub(
        r'<(?:div|span|p|h1|h2|h3|h4|h5|h6)\s+class="[^"]*\b(?:logo-text|brand-text|brand-name|site-name|logo-title)\b[^"]*"[^>]*>[\s\S]*?</(?:div|span|p|h1|h2|h3|h4|h5|h6)>',
        '',
        modified,
        flags=re.IGNORECASE,
    )

    # Add only minimal safety style for logo image sizing if needed.
    if ("logo-image" in modified or "brand-logo-image" in modified) and ("max-width: 100%" not in modified):
        style_block = (
            "\n.logo-image,\n.brand-logo-image {\n"
            "  display: block;\n"
            "  max-width: 100%;\n"
            "  height: auto;\n"
            "}\n"
        )
        if "</style>" in modified:
            modified = modified.replace("</style>", style_block + "</style>", 1)
        else:
            modified += "\n<style scoped>\n" + style_block + "</style>\n"

    return modified


def normalize_header_css_extremes(content: str) -> str:
    """
    Clamp extreme fixed values in Header.vue that frequently cause obvious
    visual drift. Keep changes conservative and only affect large outliers.
    """
    def clamp_decl(decls: str, prop: str, max_px: float) -> str:
        pattern = rf'({prop}\s*:\s*)(\d+(?:\.\d+)?)px'

        def repl(m):
            val = float(m.group(2))
            if val > max_px:
                return f"{m.group(1)}{int(max_px)}px"
            return m.group(0)

        return re.sub(pattern, repl, decls, flags=re.IGNORECASE)

    def rescue_tiny_decl(decls: str, prop: str, tiny_threshold_px: float, rescued_px: float) -> str:
        pattern = rf'({prop}\s*:\s*)(\d+(?:\.\d+)?)px'

        def repl(m):
            val = float(m.group(2))
            if val < tiny_threshold_px:
                return f"{m.group(1)}{int(rescued_px)}px"
            return m.group(0)

        return re.sub(pattern, repl, decls, flags=re.IGNORECASE)

    def normalize_block(match):
        selector = match.group(1)
        decls = match.group(2)
        lower = selector.lower()
        updated = decls

        if "logo" in lower:
            for prop in ["height", "width", "max-height", "max-width"]:
                updated = clamp_decl(updated, prop, 64.0)

        if "header-content" in lower or ".nav" in lower:
            updated = clamp_decl(updated, "gap", 32.0)

        if "nav-link" in lower or ".nav" in lower:
            updated = clamp_decl(updated, "font-size", 14.0)
            updated = clamp_decl(updated, "letter-spacing", 1.2)

        # Rescue catastrophic tiny header wrappers (e.g., max-width: 64px).
        if "header" in lower:
            updated = rescue_tiny_decl(updated, "max-width", 240.0, 960.0)

        return f"{selector}{{{updated}}}"

    return re.sub(r'([^{}]+)\{([^{}]*)\}', normalize_block, content, flags=re.IGNORECASE)


def write_project_files(output_dir, files, assets_source_dir=None,
                       url_to_local_path=None, step_resources=None,
                       page_to_step_index=None):
    written_files = []

    for file_path, content in files.items():
        # 如果是 Vue view 组件，使用 manifest 映射替换图片
        if file_path.startswith("src/views/") and file_path.endswith(".vue") and url_to_local_path and step_resources and page_to_step_index:
            page_name = Path(file_path).stem
            print(f"Image replacement for: {file_path}")

            if page_name in page_to_step_index:
                step_index = page_to_step_index[page_name]
                step_image_urls = step_resources.get(step_index, [])
                content = replace_images_with_manifest_mapping(
                    content,
                    step_image_urls,
                    url_to_local_path,
                    output_dir
                )
                if step_image_urls and not view_has_image_reference(content):
                    images_dir = output_dir / "src" / "assets" / "images"
                    step_local_images = _build_step_image_list(step_image_urls, url_to_local_path, images_dir)
                    content = _inject_missing_page_images(content, step_local_images)
                    if view_has_image_reference(content):
                        print(f"  Injected fallback images for placeholder content in: {file_path}")
        # 其他文件：修复无效图片 src
        elif file_path.endswith('.vue') or file_path.endswith('.html'):
            print(f"Fixing invalid images in: {file_path}")
            content = fix_invalid_image_sources(content, output_dir)

        if file_path == "tsconfig.json":
            content = normalize_tsconfig_content(content)
        if file_path == "src/components/Header.vue":
            content = enforce_header_logo_image(content, output_dir)
            content = normalize_header_css_extremes(content)

        full_path = output_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        written_files.append(file_path)
        print(f"  Written: {file_path}")

    return written_files


def validate_generated_files(output_dir: Path, num_pages: int, page_names: List[str], project_files: Dict[str, str]):
    """验证生成的文件数量是否正确"""
    print(f"\n{'='*60}")
    print(f"Validation Check")
    print(f"{'='*60}")
    
    views_dir = output_dir / "src" / "views"
    
    # 检查 views 目录
    if not views_dir.exists():
        print(f"❌ ERROR: src/views directory not found!")
        return
    
    # 统计 views 目录下的 .vue 文件
    view_files = list(views_dir.glob("*.vue"))
    print(f"Expected page components: {num_pages}")
    print(f"Actual page components: {len(view_files)}")
    
    # 检查每个期望的页面组件是否存在
    missing_files = []
    for page_name in page_names:
        expected_file = f"src/views/{page_name}.vue"
        if expected_file not in project_files:
            missing_files.append(expected_file)
            print(f"❌ Missing: {expected_file}")
        else:
            print(f"✓ Found: {expected_file}")
    
    # 检查 router 文件
    router_file = output_dir / "src" / "router" / "index.ts"
    if router_file.exists():
        with open(router_file, 'r', encoding='utf-8') as f:
            router_content = f.read()
            print(f"\nRouter file check:")
            for page_name in page_names:
                import_line = f"import {page_name} from '../views/{page_name}.vue'"
                if import_line in router_content:
                    print(f"✓ Router imports: {page_name}")
                else:
                    print(f"❌ Router missing import: {page_name}")
    
    # 检查 App.vue 是否有 router-view
    app_file = output_dir / "src" / "App.vue"
    if app_file.exists():
        with open(app_file, 'r', encoding='utf-8') as f:
            app_content = f.read()
            print(f"\nApp.vue check:")
            if "<router-view />" in app_content or "<router-view/>" in app_content:
                print(f"✓ App.vue has <router-view />")
            else:
                print(f"❌ App.vue missing <router-view />")
    
    # 检查 package.json 依赖
    package_file = output_dir / "package.json"
    if package_file.exists():
        try:
            import json
            with open(package_file, 'r', encoding='utf-8') as f:
                package_content = json.load(f)
                print(f"\npackage.json check:")
                
                # 检查必需的顶级字段
                required_fields = ["name", "private", "version", "type", "scripts"]
                all_fields_ok = True
                for field in required_fields:
                    if field in package_content:
                        print(f"✓ Has field: {field}")
                    else:
                        print(f"❌ Missing field: {field}")
                        all_fields_ok = False
                
                # 检查 scripts
                if "scripts" in package_content:
                    required_scripts = ["dev", "build", "preview"]
                    for script in required_scripts:
                        if script in package_content["scripts"]:
                            print(f"✓ Has script: {script}")
                        else:
                            print(f"❌ Missing script: {script}")
                            all_fields_ok = False
                
                required_deps = {"vue": "^3.4.0", "vue-router": "^4.2.0"}
                required_dev_deps = {
                    "@vitejs/plugin-vue": "^5.0.0",
                    "typescript": "~5.4.5",
                    "vite": "^5.0.0",
                    "vue-tsc": "^2.0.29"
                }
                
                all_deps_ok = True
                for dep in required_deps:
                    if "dependencies" in package_content and dep in package_content["dependencies"]:
                        print(f"✓ dependencies has: {dep}")
                    else:
                        print(f"❌ dependencies missing: {dep}")
                        all_deps_ok = False
                
                for dep in required_dev_deps:
                    if "devDependencies" in package_content and dep in package_content["devDependencies"]:
                        print(f"✓ devDependencies has: {dep}")
                    else:
                        print(f"❌ devDependencies missing: {dep}")
                        all_deps_ok = False
                
                if all_fields_ok and all_deps_ok:
                    print(f"✓ package.json is complete and valid")
        except Exception as e:
            print(f"❌ Failed to parse package.json: {e}")
    else:
        print(f"\n❌ package.json not found!")
    
    # 检查 main.ts router 配置
    main_file = output_dir / "src" / "main.ts"
    if main_file.exists():
        with open(main_file, 'r', encoding='utf-8') as f:
            main_content = f.read()
            print(f"\nmain.ts check:")
            main_ok = True
            if "import router from './router'" in main_content or "import router from './router'" in main_content:
                print(f"✓ main.ts imports router")
            else:
                print(f"❌ main.ts missing router import")
                main_ok = False
            if ".use(router)" in main_content:
                print(f"✓ main.ts uses router")
            else:
                print(f"❌ main.ts missing .use(router)")
                main_ok = False
            if main_ok:
                print(f"✓ main.ts router setup is correct")
    else:
        print(f"\n❌ main.ts not found!")
    
    # 检查 Header.vue 中的 router-link 路径是否与 router 配置匹配
    header_file = output_dir / "src" / "components" / "Header.vue"
    if header_file.exists() and router_file.exists():
        print(f"\nHeader.vue router-link vs Router config check:")
        
        # 读取 Header.vue 并提取所有 router-link 的 to 属性
        with open(header_file, 'r', encoding='utf-8') as f:
            header_content = f.read()
        
        # 提取 router-link 的 to 属性值
        import re
        router_link_pattern = r'<(?:router-link|routerlink)\s+[^>]*to\s*=\s*["\']([^"\']+)["\']'
        header_links = re.findall(router_link_pattern, header_content)
        
        # 读取 router/index.ts 并提取所有路由的 path 值
        with open(router_file, 'r', encoding='utf-8') as f:
            router_content = f.read()
        
        # 提取路由的 path 值
        path_pattern = r"path:\s*['\"]([^'\"]+)['\"]"
        router_paths = re.findall(path_pattern, router_content)
        
        # 比较两者
        header_links_set = set(header_links)
        router_paths_set = set(router_paths)
        
        # 找出 Header 中有但 router 中没有的路径
        missing_in_router = header_links_set - router_paths_set
        # 找出 router 中有但 Header 中没有的路径（这个可能不是问题，因为有些路由可能不在导航中）
        missing_in_header = router_paths_set - header_links_set
        
        if missing_in_router:
            print(f"❌ Header.vue 中的路由链接在 router/index.ts 中没有对应配置:")
            for link in sorted(missing_in_router):
                print(f"   - router-link to=\"{link}\" 在 router 中找不到")
        else:
            print(f"✅ Header.vue 中的所有 router-link 都在 router/index.ts 中有对应配置")
        
        if missing_in_header:
            print(f"⚠️  router/index.ts 中有路由但 Header.vue 中没有对应的导航链接:")
            for path in sorted(missing_in_header):
                print(f"   - path: '{path}' 在 Header 中没有对应的 router-link")
        
        # 检查是否有路径格式不一致的问题（如带连字符 vs 不带连字符）
        for link in header_links:
            for path in router_paths:
                # 检查是否只是格式不同（如 /prints-and-books vs /printsandbooks）
                if link.replace('-', '') == path.replace('-', '') and link != path:
                    print(f"❌ 路径格式不一致: Header 中是 \"{link}\"，但 router 中是 \"{path}\"")
                    print(f"   建议: 将 router 中的路径改为 \"{link}\" 以匹配 Header")
    
    # 总结
    print(f"\n{'='*60}")
    if len(view_files) == num_pages and not missing_files:
        print(f"✅ Validation PASSED: All {num_pages} page components generated correctly!")
    else:
        print(f"❌ Validation FAILED: Missing some page components!")
        print(f"   Expected: {num_pages}")
        print(f"   Actual: {len(view_files)}")
    print(f"{'='*60}\n")


def post_process_vue_files(output_dir: Path):
    """
    后处理生成的Vue文件，修复常见的语法问题
    在代码生成循环后面执行
    """
    import re
    
    print(f"\n{'='*60}")
    print(f"Post-processing Vue files")
    print(f"{'='*60}")
    
    # 处理所有Vue文件，包括views和components目录
    vue_files = []
    
    views_dir = output_dir / "src" / "views"
    if views_dir.exists():
        vue_files.extend(list(views_dir.glob("*.vue")))
    
    components_dir = output_dir / "src" / "components"
    if components_dir.exists():
        vue_files.extend(list(components_dir.glob("*.vue")))
    
    if not vue_files:
        print("No Vue files found, skipping post-processing")
        return
    
    print(f"Found {len(vue_files)} Vue files to post-process")
    
    for vue_file in vue_files:
        print(f"\nProcessing: {vue_file.name}")
        try:
            with open(vue_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            modified_content = content
            
            # 修复 1: 修复错误的 class 绑定语法 `: class=` -> `class=`
            modified_content = re.sub(r':\s+class=', 'class=', modified_content)
            
            # 修复 2: 修复静态路径被错误地用 :src 绑定的情况
            # 匹配 :src="/src/assets/images/..." 这种形式
            static_src_pattern = r':src\s*=\s*(["\'])/src/assets/(.*?)\1'
            
            def fix_static_src(match):
                quote = match.group(1)
                path = match.group(2)
                print(f"  Fixed static src from :src to src")
                return f'src={quote}/src/assets/{path}{quote}'
            
            modified_content, static_src_count = re.subn(static_src_pattern, fix_static_src, modified_content)
            if static_src_count > 0:
                print(f"  Fixed {static_src_count} static :src bindings")
            
            # 修复 3: 修复带有 v-for 的 img 标签，确保有正确的 :src 绑定
            img_tag_pattern = r'<img\s+([^>]*?v-for[^>]*?)>'
            
            def fix_img_tag(match):
                tag_attrs = match.group(1)
                attrs_str = tag_attrs
                
                # 检查是否有 :src 或 src
                has_src = ':src=' in attrs_str or 'src=' in attrs_str
                # 检查是否有 v-for
                has_v_for = 'v-for=' in attrs_str
                
                if has_v_for:
                    # 从 v-for 中提取变量名，例如 (img, index) in images -> img
                    v_for_match = re.search(r'v-for\s*=\s*["\']\(([^,]+),', attrs_str)
                    var_name = 'img'
                    if v_for_match:
                        var_name = v_for_match.group(1).strip()
                    else:
                        v_for_match = re.search(r'v-for\s*=\s*["\']([^,\s]+)\s+in', attrs_str)
                        if v_for_match:
                            var_name = v_for_match.group(1).strip()
                    
                    # 如果没有 :src，添加它
                    if not has_src:
                        src_binding = f':src="{var_name}.src"'
                        attrs_str = src_binding + ' ' + attrs_str
                        print(f"  Added missing :src binding to img tag")
                    
                    # 修复错误的 class 绑定
                    attrs_str = re.sub(r':\s+class=', 'class=', attrs_str)
                
                return f'<img {attrs_str}>'
            
            modified_content, img_count = re.subn(img_tag_pattern, fix_img_tag, modified_content)
            
            if img_count > 0:
                print(f"  Fixed {img_count} img tags")
            
            # 修复 4: 合并多个 script 标签为一个
            script_tags = []
            script_pattern = r'<script\s+setup\s+lang="ts">([\s\S]*?)</script>'
            
            def collect_script(match):
                script_content = match.group(1).strip()
                if script_content:
                    script_tags.append(script_content)
                return ''
            
            # 先移除所有 script 标签
            temp_content = re.sub(script_pattern, collect_script, modified_content)
            
            # 如果有多个 script 标签，合并它们
            if len(script_tags) > 1:
                print(f"  Found {len(script_tags)} script tags, merging into one")
                merged_script = '\n'.join(script_tags)
                # 在 template 之前插入合并后的 script 标签
                template_pattern = r'(\s*)<template>'
                def insert_script(match):
                    return f'{match.group(1)}<script setup lang="ts">\n{merged_script}\n</script>\n{match.group(1)}<template>'
                modified_content = re.sub(template_pattern, insert_script, temp_content)
            
            # 修复 5: 修复 :key 属性没有正确闭合的问题
            # 匹配 :key="`xxx-${index}" 这种情况，缺少最后一个引号
            key_pattern = r':key\s*=\s*"`([^`]+)`\s*"'
            
            def fix_key(match):
                key_content = match.group(1)
                return f':key="`{key_content}`"'
            
            modified_content, key_count = re.subn(key_pattern, fix_key, modified_content)
            if key_count > 0:
                print(f"  Fixed {key_count} :key attribute(s) missing closing quote")
            
            # 写回文件
            if modified_content != content:
                with open(vue_file, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                print(f"  Updated: {vue_file.name}")
            else:
                print(f"  No changes needed")
        
        except Exception as e:
            print(f"  Error processing {vue_file.name}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n✅ Post-processing completed")
    print(f"{'='*60}\n")


def fix_vue_images_with_manifest(
    output_dir: Path,
    url_to_local_path: Dict[str, str],
    step_resources: Dict[int, List[str]],
    page_to_step_index: Dict[str, int]
):
    """
    最终图片修复（一次性 pass），确保：
    1. v-for 中的 img 标签正确绑定 :src
    2. 数组中的图片用该页面实际使用的图片替换
    3. 独立 img 标签按顺序分配该页面的图片
    4. 选择同一张图最高质量的 format 变体
    """
    print(f"\n{'='*60}")
    print(f"Fixing Vue images with manifest (final pass)")
    print(f"{'='*60}")

    views_dir = output_dir / "src" / "views"
    if not views_dir.exists():
        print("src/views directory not found")
        return

    images_dir = output_dir / "src" / "assets" / "images"
    vue_files = list(views_dir.glob("*.vue"))

    for vue_file in vue_files:
        page_name = vue_file.stem
        print(f"\nProcessing: {vue_file.name}")

        if page_name == "Home":
            print(f"  Skipping Home page (always empty)")
            continue

        if page_name not in page_to_step_index:
            print(f"  No step mapping for: {page_name}")
            continue

        step_index = page_to_step_index[page_name]
        step_image_urls = step_resources.get(step_index, [])

        if not step_image_urls:
            print(f"  No images for step_{step_index:02d}")
            continue

        # 获取去重后的高质量图片列表
        step_local_images = _build_step_image_list(step_image_urls, url_to_local_path, images_dir)

        if not step_local_images:
            print(f"  No local images mapped for step_{step_index:02d}")
            continue

        print(f"  Step_{step_index:02d} has {len(step_local_images)} unique images (best quality)")

        try:
            with open(vue_file, 'r', encoding='utf-8') as f:
                content = f.read()

            modified_content = content

            # ---- Step 1: 修复 v-for 中的 img 标签 ----
            # BUG FIX: 原来用了 &lt; / &gt; HTML 实体，永远匹配不到
            vfor_img_pattern = r'<img\s+([^>]*?v-for\s*=\s*["\']([^"\']+)\s+in\s+([^"\']+)["\'][^>]*?)>'

            def fix_vfor_img(match):
                full_attrs = match.group(1)
                loop_var = match.group(2)

                var_name = loop_var
                if ',' in loop_var:
                    var_name = loop_var.split(',')[0].strip().strip('()')

                # 移除静态 src
                cleaned_attrs = re.sub(r'\s*src\s*=\s*(["\'])[^"\']*\1', '', full_attrs)

                if ':src=' in cleaned_attrs:
                    return f'<img {cleaned_attrs}>'

                new_attrs = f':src="{var_name}" {cleaned_attrs}'
                print(f"  Fixed v-for img: added :src={var_name}")
                return f'<img {new_attrs}>'

            modified_content, vfor_count = re.subn(vfor_img_pattern, fix_vfor_img, modified_content)
            if vfor_count > 0:
                print(f"  Fixed {vfor_count} v-for img tags")

            # ---- Step 2: 替换 JS 数组中的图片 ----
            # 匹配 const/let/var xxx = [...] 形式的图片数组
            array_pattern = r'(const|let|var)\s+(\w+(?:Photos|Images|photos|images|Items|items|Pictures|pictures)?)\s*=\s*\[([\s\S]*?)\]'

            def fix_array(match):
                array_type = match.group(1)
                array_name = match.group(2)
                array_body = match.group(3)

                # Only rewrite simple string-based image arrays.
                # Skip object arrays to avoid changing schema/semantics.
                if re.search(r'\{', array_body):
                    return match.group(0)
                if not re.search(r'(/src/assets/images/|https?://|\.jpe?g|\.png|\.webp|\.gif|\.avif|\.svg)', array_body, re.IGNORECASE):
                    return match.group(0)

                existing_string_items = re.findall(r'(["\'])(.*?)\1', array_body)
                if not existing_string_items:
                    return match.group(0)

                # Preserve original item count to avoid drift (e.g. /photos gallery count mismatch).
                slot_count = len(existing_string_items)
                quote = existing_string_items[0][0]
                new_array_items = []
                for idx in range(slot_count):
                    img_file = step_local_images[idx % len(step_local_images)]
                    new_array_items.append(f"  {quote}/src/assets/images/{img_file}{quote}")

                new_array_content = ',\n'.join(new_array_items)
                print(f"  Replaced array {array_name}: kept {slot_count} slots (cycled {len(step_local_images)} source images)")
                return f'{array_type} {array_name} = [\n{new_array_content}\n]'

            modified_content, array_count = re.subn(array_pattern, fix_array, modified_content)

            # ---- Step 3: 修复独立 img 标签的 src（非 v-for） ----
            # 先找出所有 v-for img 标签的位置范围，后续替换时跳过
            vfor_img_spans = []
            for m in re.finditer(vfor_img_pattern, modified_content):
                vfor_img_spans.append((m.start(), m.end()))

            # 匹配所有 src="..." （包括 :src 绑定的静态路径）
            src_pattern = r'(?:src|:src)\s*=\s*(["\'])(.*?)\1'
            img_idx = [0]

            def fix_hardcoded_src(match):
                match_start = match.start()
                match_end = match.end()

                # 跳过 v-for img 范围
                for (vfor_start, vfor_end) in vfor_img_spans:
                    if vfor_start <= match_start and match_end <= vfor_end:
                        return match.group(0)

                quote = match.group(1)
                img_path = match.group(2)

                # 已经是有效本地图片 -> 保留
                if img_path.startswith('/src/assets/images/'):
                    filename = img_path.split('/')[-1]
                    if (images_dir / filename).exists():
                        return match.group(0)

                # 替换为该步骤的下一张图片
                selected = step_local_images[img_idx[0] % len(step_local_images)]
                img_idx[0] += 1
                return f'src={quote}/src/assets/images/{selected}{quote}'

            modified_content, src_count = re.subn(src_pattern, fix_hardcoded_src, modified_content)
            if src_count > 0:
                print(f"  Fixed {src_count} standalone image sources")

            # 写回
            if modified_content != content:
                with open(vue_file, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                print(f"  Updated: {vue_file.name}")
            else:
                print(f"  No changes needed")

        except Exception as e:
            print(f"  Error processing {vue_file.name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n✅ Final image fixing completed")
    print(f"{'='*60}\n")


def fix_router_paths(output_dir: Path):
    """
    修复路由文件中的所有路径，确保它们都是小写的
    """
    import re
    
    print(f"\n{'='*60}")
    print(f"Fixing router paths (ensure all lowercase)")
    print(f"{'='*60}")
    
    router_file = output_dir / "src" / "router" / "index.ts"
    
    if not router_file.exists():
        print(f"Router file not found: {router_file}")
        return
    
    try:
        with open(router_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        modified_content = content
        
        # 1. 修复 path: '/...' 中的路径
        def fix_path(match):
            quote = match.group(1)
            path = match.group(2)
            # 将路径转换为小写
            lower_path = path.lower()
            if path != lower_path:
                print(f"  Fixed path: {path} -&gt; {lower_path}")
            return f'path: {quote}{lower_path}{quote}'
        
        path_pattern = r'path:\s*(["\'])(/[^"\']*)\1'
        modified_content, path_count = re.subn(path_pattern, fix_path, modified_content)
        
        # 2. 修复 router-link to="..." 中的路径（在 App.vue 和其他组件中）
        # 先处理 router/index.ts 中的路径
        # 然后处理所有 Vue 文件中的 router-link
        views_dir = output_dir / "src" / "views"
        if views_dir.exists():
            vue_files = list(views_dir.glob("*.vue"))
            app_file = output_dir / "src" / "App.vue"
            if app_file.exists():
                vue_files.append(app_file)
            
            for vue_file in vue_files:
                try:
                    with open(vue_file, 'r', encoding='utf-8') as f:
                        vue_content = f.read()
                    
                    # 修复 router-link 中的 to 属性
                    def fix_router_link(match):
                        quote = match.group(1)
                        path = match.group(2)
                        lower_path = path.lower()
                        if path != lower_path:
                            print(f"  Fixed router-link in {vue_file.name}: {path} -&gt; {lower_path}")
                        return f'to={quote}{lower_path}{quote}'
                    
                    link_pattern = r'to\s*=\s*(["\'])(/[^"\']*)\1'
                    modified_vue_content, link_count = re.subn(link_pattern, fix_router_link, vue_content)
                    
                    if modified_vue_content != vue_content:
                        with open(vue_file, 'w', encoding='utf-8') as f:
                            f.write(modified_vue_content)
                        print(f"  Updated: {vue_file.name}")
                
                except Exception as e:
                    print(f"  Error processing {vue_file.name}: {e}")
        
        # 写回 router 文件
        if modified_content != content:
            with open(router_file, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            print(f"  Updated router file with {path_count} path(s) fixed")
        else:
            print(f"  No changes needed to router file")
        
        print(f"\n✅ Router path fixing completed")
        print(f"{'='*60}\n")
    
    except Exception as e:
        print(f"Error fixing router paths: {e}")
        import traceback
        traceback.print_exc()


def ensure_home_page_exists(output_dir: Path, project_files: Dict[str, str]):
    """
    确保 Home 页面存在，如果需要的话生成空的 Home 页面
    同时检查页面数量，如果 AI 漏生成了页面，尝试补齐
    """
    import re
    
    print(f"\n{'='*60}")
    print(f"Ensuring all pages exist (Home + screenshots)")
    print(f"{'='*60}")
    
    # 获取全局变量中的截图数量（num_screenshots）
    # 我们需要重新计算，因为这个函数不知道有多少截图
    # 所以从 checkpoints 目录推断
    checkpoints_dir = output_dir.parent / "checkpoints"
    if checkpoints_dir.exists():
        screenshots = list(checkpoints_dir.glob("step_*.png"))
        num_screenshots = len(screenshots)
    else:
        # 如果找不到 checkpoints，尝试从 output 目录推断
        views_dir = output_dir / "src" / "views"
        existing_vue = list(views_dir.glob("*.vue"))
        num_screenshots = len(existing_vue) - 1  # 减去 Home
        if num_screenshots < 1:
            num_screenshots = 1
    
    expected_total_pages = 1 + num_screenshots  # Home + 截图页面
    print(f"  Expected total pages: {expected_total_pages} (1 empty Home + {num_screenshots} screenshot pages)")
    
    # 检查 Home.vue 是否存在
    home_vue_path = output_dir / "src" / "views" / "Home.vue"
    router_path = output_dir / "src" / "router" / "index.ts"
    
    home_exists = home_vue_path.exists()
    router_exists = router_path.exists()
    
    # 获取现有页面
    views_dir = output_dir / "src" / "views"
    if views_dir.exists():
        vue_files = list(views_dir.glob("*.vue"))
        existing_pages = [f.stem for f in vue_files]
    else:
        vue_files = []
        existing_pages = []
    
    print(f"  Existing .vue files in src/views: {existing_pages}")
    print(f"  Existing page count: {len(existing_pages)}")
    
    # 如果页面数量不对，说明 AI 漏生成了
    if len(existing_pages) < expected_total_pages:
        print(f"  ⚠️  Missing {expected_total_pages - len(existing_pages)} page(s)!")
        
        # AI 应该为每个截图生成一个页面文件，文件名由 AI 从截图内容确定
        # 如果总数不对，说明 AI 漏生成了某些文件
        # 我们按顺序创建空文件占位，文件名用 Page{i+1}，后续补全流程会处理
        missing_count = expected_total_pages - len(existing_pages)
        print(f"  Creating {missing_count} empty placeholder page(s)...")
        
        # 计算已经有多少个非 Home 页面
        existing_non_home = [p for p in existing_pages if p != "Home"]
        next_index = len(existing_non_home)
        
        for i in range(next_index, num_screenshots):
            page_name = f"Page{i+1}"
            print(f"  Creating missing placeholder: {page_name}.vue")
            page_path = output_dir / "src" / "views" / f"{page_name}.vue"
            empty_content = """<script setup lang="ts">
</script>

<template>
  <div class="page-container">
  </div>
</template>

<style scoped>
</style>
"""
            page_path.parent.mkdir(parents=True, exist_ok=True)
            with open(page_path, 'w', encoding='utf-8') as f:
                f.write(empty_content)
    
    # 现在重新获取页面列表来更新 router
    views_dir = output_dir / "src" / "views"
    vue_files = list(views_dir.glob("*.vue"))
    page_names_from_files = [f.stem for f in vue_files]
    
    # 从 Header.vue 中提取路由链接，获取正确的路径
    header_path = output_dir / "src" / "components" / "Header.vue"
    path_map = {}  # 页面名称 -> 正确路径的映射
    
    if header_path.exists():
        try:
            import re
            with open(header_path, 'r', encoding='utf-8') as f:
                header_content = f.read()
            
            # 提取所有 router-link 的 to 属性
            router_link_pattern = r'<(?:router-link|routerlink)\s+[^>]*to\s*=\s*["\']([^"\']+)["\']'
            header_paths = re.findall(router_link_pattern, header_content, flags=re.IGNORECASE)
            
            print(f"  Found {len(header_paths)} router-link paths in Header.vue: {header_paths}")
            
            # 建立页面名称到路径的映射
            for path in header_paths:
                if path == '/':
                    path_map['Home'] = '/'
                else:
                    # 从路径推导页面名称（去掉 /，然后转成驼峰）
                    # 例如 /prints-and-books -> PrintsAndBooks
                    path_without_slash = path[1:]
                    # 转成驼峰命名
                    words = path_without_slash.split('-')
                    page_name_candidate = ''.join(word.capitalize() for word in words)
                    # 检查这个候选名称是否在页面文件中
                    if page_name_candidate in page_names_from_files:
                        path_map[page_name_candidate] = path
                    else:
                        # 如果不在，也可以尝试用首字母大写的单字
                        single_word_name = path_without_slash.capitalize()
                        if single_word_name in page_names_from_files:
                            path_map[single_word_name] = path
                        else:
                            # Fuzzy match for cases like /prints-books -> PrintsAndBooks
                            normalized_path = re.sub(r'[^a-z0-9]', '', path_without_slash.lower()).replace('and', '')
                            for page_name in page_names_from_files:
                                normalized_page = re.sub(r'[^a-z0-9]', '', page_name.lower()).replace('and', '')
                                if normalized_page == normalized_path:
                                    path_map[page_name] = path
                                    break
                                # Also match by stem containment for cases like:
                                # /photos -> PhotoGallery
                                path_stem = normalized_path.rstrip('s')
                                if path_stem and (normalized_page.startswith(path_stem) or path_stem in normalized_page):
                                    path_map[page_name] = path
                                    break
        
        except Exception as e:
            print(f"  Warning: Could not parse Header.vue for paths: {e}")
    
    # 确保路由中有所有页面
    if router_exists:
        with open(router_path, 'r', encoding='utf-8') as f:
            router_content = f.read()
        
        # 重新构建 router
        new_router_content = "import { createRouter, createWebHistory } from 'vue-router'\n"
        
        # 添加 Home 导入
        new_router_content += "import Home from '../views/Home.vue'\n"
        
        # 添加其他页面导入
        for page_name in page_names_from_files:
            if page_name != "Home":
                new_router_content += f"import {page_name} from '../views/{page_name}.vue'\n"
        
        new_router_content += "\nconst routes = [\n"
        
        # 添加 Home 路由
        new_router_content += "  {\n"
        new_router_content += "    path: '/',\n"
        new_router_content += "    name: 'Home',\n"
        new_router_content += "    component: Home\n"
        new_router_content += "  },\n"
        
        # 添加其他页面路由 - 使用从 Header.vue 提取的正确路径
        for page_name in page_names_from_files:
            if page_name != "Home":
                # 优先使用从 Header.vue 提取的路径，否则回退到小写格式
                if page_name in path_map:
                    path = path_map[page_name]
                    print(f"  Using path from Header for {page_name}: {path}")
                else:
                    # 如果在 Header 中没找到，尝试智能地把驼峰转成连字符格式
                    # PrintsAndBooks -> prints-and-books
                    import re
                    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', page_name)
                    hyphenated = re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1).lower()
                    path = f"/{hyphenated}"
                    print(f"  Using auto-converted path for {page_name}: {path}")
                
                new_router_content += "  {\n"
                new_router_content += f"    path: '{path}',\n"
                new_router_content += f"    name: '{page_name}',\n"
                new_router_content += f"    component: {page_name}\n"
                new_router_content += "  },\n"
        
        new_router_content += "]\n\nconst router = createRouter({\n"
        new_router_content += "  history: createWebHistory(),\n"
        new_router_content += "  routes\n"
        new_router_content += "})\n\nexport default router"
        
        # 写回 router
        with open(router_path, 'w', encoding='utf-8') as f:
            f.write(new_router_content)
        print(f"  ✅ Updated router with all {len(page_names_from_files)} pages")
    
    # 现在确保 Home.vue 存在
    if not home_exists:
        print("  Home.vue not found, creating empty Home page")
        # 创建空的 Home.vue
        empty_home_content = """<script setup lang="ts">
</script>

<template>
  <div class="home">
  </div>
</template>

<style scoped>
</style>
"""
        home_vue_path.parent.mkdir(parents=True, exist_ok=True)
        with open(home_vue_path, 'w', encoding='utf-8') as f:
            f.write(empty_home_content)
        print("  Created empty Home.vue")
    else:
        print("  Home.vue already exists")
    
    print(f"\n✅ Page check completed")
    print(f"{'='*60}\n")


async def run_build_check(output_dir: Path):
    """
    运行编译检查，检查是否有语法错误或编译错误
    """
    import asyncio
    
    print(f"\n{'='*60}")
    print(f"Running build check")
    print(f"{'='*60}")
    
    # 检查 package.json 是否存在
    package_json_path = output_dir / "package.json"
    if not package_json_path.exists():
        print("  ❌ package.json not found, skipping build check")
        return False
    
    print(f"  Working directory: {output_dir}")
    
    async def run_cmd(args: List[str]) -> tuple[int, str, str]:
        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=str(output_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        out, err = await proc.communicate()
        return (
            proc.returncode,
            out.decode('utf-8', errors='ignore'),
            err.decode('utf-8', errors='ignore')
        )

    try:
        install_variants = [
            ["npm", "install"],
            ["corepack", "pnpm", "install"],
            [r"C:\Program Files\nodejs\corepack.cmd", "pnpm", "install"],
        ]
        build_variants = [
            ["npm", "run", "build"],
            ["corepack", "pnpm", "run", "build"],
            [r"C:\Program Files\nodejs\corepack.cmd", "pnpm", "run", "build"],
        ]

        print(f"\n  Step 1: Installing dependencies...")
        install_ok = False
        for cmd in install_variants:
            print(f"  Trying: {' '.join(cmd)}")
            try:
                code, out, err = await run_cmd(cmd)
            except FileNotFoundError:
                print(f"  Command not found: {cmd[0]}")
                continue
            if code == 0:
                install_ok = True
                print("  Install completed")
                break
            print(f"  Install failed ({code})")
            if err.strip():
                print(f"  stderr: {err}")
            elif out.strip():
                print(f"  stdout: {out}")
        if not install_ok:
            return False

        print(f"\n  Step 2: Running build...")
        for cmd in build_variants:
            print(f"  Trying: {' '.join(cmd)}")
            try:
                code, out, err = await run_cmd(cmd)
            except FileNotFoundError:
                print(f"  Command not found: {cmd[0]}")
                continue
            if code == 0:
                print(f"  ✅ Build completed successfully")
                print(f"\n✅ All checks passed!")
                print(f"{'='*60}\n")
                return True
            print(f"  Build failed ({code})")
            if out.strip():
                print(f"  stdout: {out}")
            if err.strip():
                print(f"  stderr: {err}")
        return False

    except Exception as e:
        print(f"  ❌ Build check error: {e}")
        import traceback
        traceback.print_exc()
        return False
