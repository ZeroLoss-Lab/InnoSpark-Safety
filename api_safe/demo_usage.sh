#!/bin/bash
# 拦截功能演示脚本

echo "🚀 拦截功能演示脚本"
echo "====================================="

# 检查safe_api目录
if [ ! -d "safe_api" ]; then
    echo "❌ safe_api目录不存在"
    exit 1
fi

echo "📋 演示步骤："
echo "1. 查看帮助信息"
echo "2. 展示命令行参数"
echo "3. 模拟启动命令"
echo ""

# 1. 查看帮助信息
echo "📖 1. 查看run.py帮助信息："
echo "命令: python run.py --help"
echo "结果: ✅ 包含所有拦截参数"
echo ""

# 2. 展示主要的启动命令
echo "🔧 2. 主要启动命令示例："
echo ""

echo "🔹 开发环境（基础配置）："
echo "python run.py \\"
echo "  --vllm-api http://localhost:8000 \\"
echo "  --api-key \"dev-api-key\" \\"
echo "  --docs-no-auth \\"
echo "  --port 8003"
echo ""

echo "🔹 测试环境（带拦截）："
echo "python run.py \\"
echo "  --vllm-api http://localhost:8000 \\"
echo "  --enable-front-intercept \\"
echo "  --enable-post-intercept \\"
echo "  --api-key \"test-api-key\" \\"
echo "  --enable-multi-api-keys \\"
echo "  --api-keys-file api_keys.json \\"
echo "  --docs-require-auth \\"
echo "  --port 8003"
echo ""

echo "🔹 生产环境（完整安全配置）："
echo "python run.py \\"
echo "  --vllm-api http://localhost:8000 \\"
echo "  --enable-front-intercept \\"
echo "  --enable-post-intercept \\"
echo "  --api-key \"prod-api-key\" \\"
echo "  --enable-multi-api-keys \\"
echo "  --api-keys-file api_keys.json \\"
echo "  --disable-docs \\"
echo "  --workers 4 \\"
echo "  --max-connections 500 \\"
echo "  --max-keepalive-connections 200 \\"
echo "  --port 8003"
echo ""

# 3. 检查必要文件
echo "📁 3. 检查必要文件："

if [ -f "api_keys.json" ]; then
    echo "✅ api_keys.json 存在"
    api_key_count=$(cat api_keys.json | grep -o '"sk-[^"]*"' | wc -l)
    echo "   包含 $api_key_count 个API密钥"
else
    echo "❌ api_keys.json 不存在"
fi

if [ -f "safe_api/front_intercept_api.py" ]; then
    echo "✅ 前拦截服务文件存在"
else
    echo "❌ 前拦截服务文件不存在"
fi

if [ -f "safe_api/post_intercept_api.py" ]; then
    echo "✅ 后拦截服务文件存在"
else
    echo "❌ 后拦截服务文件不存在"
fi

if [ -f "safe_api/start_services.py" ]; then
    echo "✅ 拦截服务启动脚本存在"
else
    echo "❌ 拦截服务启动脚本不存在"
fi

echo ""

# 4. 端口规划建议
echo "🌐 4. 端口规划建议："
echo "   vLLM服务:    8000"
echo "   前拦截服务:  8001"
echo "   后拦截服务:  8002"
echo "   主API服务:   8003"
echo ""

# 5. 启动流程
echo "🚀 5. 完整启动流程："
echo ""
echo "步骤1: 启动safe_api拦截服务"
echo "   cd safe_api"
echo "   python start_services.py"
echo "   # 或分别启动："
echo "   # python front_intercept_api.py &"
echo "   # python post_intercept_api.py &"
echo ""
echo "步骤2: 验证拦截服务"
echo "   curl http://localhost:8001/health  # 前拦截"
echo "   curl http://localhost:8002/health  # 后拦截"
echo ""
echo "步骤3: 启动主API（选择一种配置）"
echo "   # 开发环境"
echo "   python run.py --vllm-api http://localhost:8000 --docs-no-auth --port 8003"
echo ""
echo "   # 带拦截的完整配置"
echo "   python run.py --vllm-api http://localhost:8000 \\"
echo "     --enable-front-intercept \\"
echo "     --enable-post-intercept \\"
echo "     --api-key \"your-api-key\" \\"
echo "     --enable-multi-api-keys \\"
echo "     --api-keys-file api_keys.json \\"
echo "     --docs-require-auth \\"
echo "     --port 8003"
echo ""
echo "步骤4: 测试功能"
echo "   python test_intercept.py http://localhost:8003 your-api-key"
echo ""

# 6. 检查依赖
echo "📦 6. 依赖检查："
echo "主API依赖（基础功能）:"
echo "  - fastapi"
echo "  - uvicorn"
echo "  - httpx"
echo "  - pydantic"
echo ""
echo "拦截功能依赖（可选）:"
echo "  - torch"
echo "  - transformers"
echo "  - aiohttp"
echo ""
echo "安装命令: pip install -r requirements.txt"
echo ""

# 7. 故障排查
echo "🔧 7. 故障排查："
echo "如果遇到 'No module named torch' 错误："
echo "  - 这是正常的，因为没有安装拦截依赖"
echo "  - 可以继续使用基础功能（无拦截）"
echo "  - 如需拦截功能，请安装: pip install torch transformers aiohttp"
echo ""
echo "如果端口被占用："
echo "  - 使用 --port 参数指定其他端口"
echo "  - 检查: lsof -i :8003"
echo ""

echo "✅ 演示完成！"
echo ""
echo "📖 更多信息请查看："
echo "  - INTERCEPT_USAGE_EXAMPLE.md"
echo "  - SECURITY_PARAMETERS_GUIDE.md"
echo "  - COMMAND_LINE_INTERCEPT_SUMMARY.md"
