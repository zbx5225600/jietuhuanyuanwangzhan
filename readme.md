# 截图还原工具（整理版）

本项目基于 `screenshot-to-code` 做二次开发，用于根据截图还原可运行的 Vue3 + Vite 页面。

## 项目结构

```text
jietuhuanyuanwangzhan/
├─ screenshot-to-code/   # 上游项目与后端/前端核心代码
├─ task_0001/            # 示例任务数据
├─ tests/                # 测试脚本
├─ docs/                 # 项目文档
├─ process_single.py
├─ process_task.py
├─ check_env.py
└─ setup_config_multi.py
```

## 快速使用

```bash
python check_env.py
python setup_config_multi.py
python process_single.py task_0001
```

## 文档入口

- 使用与运行: `docs/用户手册.md`
- 配置与模型: `docs/配置与模型.md`
- 开发与改造: `docs/开发说明.md`
- 文件结构说明: `docs/文件结构.md`
- 更新记录: `docs/变更记录.md`

## 测试入口

- `tests/test_batch_process.py`
- `tests/test_extraction.py`
- `tests/test_route_fix.py`
- `tests/test_checkpoint_routes.py`
