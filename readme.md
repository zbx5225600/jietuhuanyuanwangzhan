# 截图还原工具 - Screenshot to Vue3

## 项目简介

基于 [screenshot-to-code](https://github.com/abi/screenshot-to-code) 开源项目进行二次开发，实现从用户操作截图自动还原成 **Vue3 + Vite** 项目的功能。

用户在网页上操作点击，每点击一次都会产生一张截图。本工具可以从这些截图自动生成可运行的Vue3项目，实现页面还原。

## 功能特性

✅ **截图还原**: 从用户操作截图自动生成Vue3+Vite项目  
✅ **完整项目**: 生成包含所有配置文件的完整项目结构  
✅ **资源处理**: 自动复制和处理静态资源文件  
✅ **批量处理**: 支持批量处理多个task目录  
✅ **API接口**: 提供RESTful API供前端调用  
✅ **多模型支持**: 支持OpenAI、通义千问、文心一言、智谱GLM等多种AI模型  
✅ **国产模型**: 完全支持国产AI模型，无需科学上网  

## 快速开始

### 1. 检查环境

```bash
python check_env.py
```

### 2. 安装依赖

```bash
pip install fastapi uvicorn openai python-dotenv aiofiles
```

### 3. 设置API Key

**方式1: 多模型配置向导 (支持国产模型) ⭐**

```bash
python setup_config_multi.py
# 支持: OpenAI、通义千问、文心一言、智谱GLM
```

**方式2: OpenAI快速配置**

```bash
python setup_config.py
# 仅配置OpenAI
```

**方式3: 手动配置文件**

```bash
copy config.example.json config.json
# 编辑config.json，填入你的API Key
```

**方式4: 环境变量**

```bash
$env:OPENAI_API_KEY="sk-your-api-key-here"
```

详细配置说明: [配置说明.md](配置说明.md) | [国产模型支持.md](国产模型支持.md)

### 4. 处理task

```bash
# 处理单个task
python process_single.py task_0001

# 或批量处理所有tasks
python process_task.py
```

### 5. 运行生成的项目

```bash
cd task_0001/output
npm install
npm run dev
```

访问 `http://localhost:5173` 查看还原的网页。

## 项目结构

```
jietuhuanyuanwangzhan/
├── screenshot-to-code/              # 开源项目(已改造)
│   └── backend/
│       ├── routes/
│       │   └── batch_process.py     # ✨ 批量处理API
│       └── codegen/
│           └── vue_extractor.py     # ✨ Vue文件提取器
├── task_0001/                       # 示例task
│   ├── checkpoints/                 # 截图文件
│   ├── assets/                      # 静态资源
│   ├── output/                      # ✨ 生成的Vue3项目
│   └── ground_truth/                # 参考答案
├── process_single.py                # ✨ 单任务处理脚本
├── process_task.py                  # ✨ 批量处理脚本
├── check_env.py                     # ✨ 环境检查脚本
├── 快速开始.md                      # 快速上手指南
├── 使用说明.md                      # 详细使用文档
└── 二次开发说明.md                  # 技术实现细节
```

## 输出结果

生成的Vue3项目结构：

```
task_0001/output/
├── index.html              # 入口HTML
├── package.json            # 项目配置
├── vite.config.ts          # Vite配置
├── tsconfig.json           # TypeScript配置
├── tsconfig.node.json      # Node TypeScript配置
└── src/
    ├── main.ts             # 入口文件
    ├── App.vue             # 主组件
    └── assets/             # 静态资源(自动复制)
```

## 文档导航

- 📖 [快速开始.md](快速开始.md) - 5分钟快速上手
- 📖 [国产模型支持.md](国产模型支持.md) - 通义千问、文心一言、智谱GLM配置 ⭐
- 📖 [配置说明.md](配置说明.md) - API Key配置详解
- 📖 [配置方式总结.md](配置方式总结.md) - 三种配置方式对比
- 📖 [使用说明.md](使用说明.md) - 详细使用文档
- 📖 [使用流程.md](使用流程.md) - 完整使用流程图
- 📖 [二次开发说明.md](二次开发说明.md) - 技术实现细节
- 📖 [文件清单.md](文件清单.md) - 所有文件说明
- 📖 [更新说明.md](更新说明.md) - 配置文件更新说明

## 技术栈

- **后端**: Python 3.10+, FastAPI, OpenAI API
- **生成目标**: Vue 3.4+, Vite 5.0+, TypeScript 5.2+
- **AI模型**: 
  - OpenAI: GPT-4 Vision Preview (国际)
  - 通义千问: Qwen-VL-Max (国产推荐)
  - 文心一言: ERNIE-Bot-4 (国产)
  - 智谱GLM: GLM-4V (国产)

## 原始需求

用户在任何一个网页上操作点击，然后每点击一次都会产生一张截图，需要开发一款通用的"页面还原工具"，这些截图把网站还原出来。文件夹中包含截图、资源包、视频文件等。文件夹中视频是用户操作参考视频，其中ground_truth/目录为"页面还原工具"生成后html页面文件目录。

## 许可证

基于原项目 [screenshot-to-code](https://github.com/abi/screenshot-to-code) 的许可证。
