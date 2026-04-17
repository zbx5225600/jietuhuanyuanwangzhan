# 截图还原工具 - 快速设置脚本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "截图还原工具 - 快速设置" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检查Python
Write-Host "1. 检查Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✓ $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "   ✗ Python未安装" -ForegroundColor Red
    exit 1
}

# 2. 安装依赖
Write-Host ""
Write-Host "2. 安装Python依赖..." -ForegroundColor Yellow
pip install fastapi uvicorn openai python-dotenv aiofiles
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✓ 依赖安装成功" -ForegroundColor Green
} else {
    Write-Host "   ✗ 依赖安装失败" -ForegroundColor Red
    exit 1
}

# 3. 设置API Key
Write-Host ""
Write-Host "3. 设置OpenAI API Key..." -ForegroundColor Yellow
$apiKey = Read-Host "请输入你的OpenAI API Key (sk-...)"
if ($apiKey) {
    $env:OPENAI_API_KEY = $apiKey
    Write-Host "   ✓ API Key已设置" -ForegroundColor Green
    Write-Host "   注意: 此设置仅在当前会话有效" -ForegroundColor Yellow
    Write-Host "   如需永久设置，请添加到系统环境变量" -ForegroundColor Yellow
} else {
    Write-Host "   ✗ 未输入API Key" -ForegroundColor Red
}

# 4. 运行环境检查
Write-Host ""
Write-Host "4. 运行环境检查..." -ForegroundColor Yellow
python check_env.py

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "设置完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步:" -ForegroundColor Yellow
Write-Host "  python process_single.py task_0001" -ForegroundColor White
Write-Host ""
