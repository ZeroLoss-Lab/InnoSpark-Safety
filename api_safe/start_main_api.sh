#!/bin/bash
# 主 API 启动脚本
# 负责启动主API服务，配置功能开关

echo "🚀 启动主 API 服务..."

# 检查 Safe API 服务是否运行
check_safe_api() {
    echo "🔍 检查 Safe API 服务状态..."
    
    if ! curl -s http://localhost:8001/health > /dev/null; then
        echo "❌ 前拦截服务 (8001) 未运行"
        echo "💡 请先运行: ./start_safe_api.sh"
        exit 1
    fi
    echo "✅ 前拦截服务正常"
    
    if ! curl -s http://localhost:8002/health > /dev/null; then
        echo "❌ 后拦截服务 (8002) 未运行"
        echo "💡 请先运行: ./start_safe_api.sh"
        exit 1
    fi
    echo "✅ 后拦截服务正常"
}

# 解析命令行参数
ENABLE_FRONT=true
ENABLE_POST=true
ENABLE_RAG=true
VLLM_BASE="http://localhost:8000"
RAG_URL="http://localhost:8000/retrieve"
API_PORT=8080

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-front)
            ENABLE_FRONT=false
            shift
            ;;
        --no-post)
            ENABLE_POST=false
            shift
            ;;
        --no-rag)
            ENABLE_RAG=false
            shift
            ;;
        --vllm-url)
            VLLM_BASE="$2"
            shift 2
            ;;
        --rag-url)
            RAG_URL="$2"
            shift 2
            ;;
        --port)
            API_PORT="$2"
            shift 2
            ;;
        --help)
            echo "主 API 启动脚本"
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --no-front     禁用前拦截"
            echo "  --no-post      禁用后拦截"
            echo "  --no-rag       禁用RAG系统"
            echo "  --vllm-url URL vLLM服务地址 (默认: http://localhost:8000)"
            echo "  --rag-url URL  RAG服务地址 (默认: http://localhost:8000/retrieve)"
            echo "  --port PORT    主API端口 (默认: 8080)"
            echo "  --help         显示帮助"
            echo ""
            echo "示例:"
            echo "  $0                    # 完整功能启动"
            echo "  $0 --no-rag          # 不使用RAG"
            echo "  $0 --no-post         # 只使用前拦截"
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            echo "使用 --help 查看帮助"
            exit 1
            ;;
    esac
done

# 根据功能开关检查服务
if [ "$ENABLE_FRONT" = "true" ] || [ "$ENABLE_POST" = "true" ]; then
    check_safe_api
fi

# 设置主 API 配置（功能开关）
echo "⚙️  配置主 API 参数..."

# 功能开关配置
export ENABLE_FRONT_INTERCEPT=$ENABLE_FRONT
export ENABLE_POST_INTERCEPT=$ENABLE_POST
export ENABLE_RAG=$ENABLE_RAG

# Safe API 服务地址配置
export USE_LOCAL_INTERCEPT=false
export FRONT_INTERCEPT_URL="http://localhost:8001/intercept"
export POST_INTERCEPT_URL="http://localhost:8002/intercept"
export INTERCEPT_TIMEOUT=10.0

# RAG 系统配置
export RAG_SERVICE_URL=$RAG_URL
export RAG_TOP_K=5
export RAG_TIMEOUT=10.0

# vLLM 配置
export VLLM_API_BASE=$VLLM_BASE

# 主API 服务配置
export HOST=0.0.0.0
export PORT=$API_PORT
export LOG_LEVEL=INFO

# API 密钥配置
export ENABLE_MULTI_API_KEYS=true
export API_KEYS_FILE=api_keys.json

# 统一安全响应消息配置
export SAFETY_RESPONSE_MESSAGE="根据相关法律法规以及道德伦理规范，我无法提供关于这个问题的回答，建议换一个话题。"

echo "📊 主 API 配置:"
echo "  前拦截: $ENABLE_FRONT_INTERCEPT"
echo "  后拦截: $ENABLE_POST_INTERCEPT"
echo "  RAG系统: $ENABLE_RAG"
echo "  vLLM地址: $VLLM_API_BASE"
echo "  RAG地址: $RAG_SERVICE_URL"
echo "  主API端口: $PORT"
echo "  安全响应消息: $SAFETY_RESPONSE_MESSAGE"

# 检查必要文件
if [ ! -f "main.py" ]; then
    echo "❌ 文件不存在: main.py"
    exit 1
fi

if [ "$ENABLE_MULTI_API_KEYS" = "true" ] && [ ! -f "$API_KEYS_FILE" ]; then
    echo "⚠️  API密钥文件不存在: $API_KEYS_FILE"
    echo "💡 将使用默认配置"
fi

# 检查 vLLM 服务
echo "🔍 检查 vLLM 服务..."
if ! curl -s "$VLLM_API_BASE/health" > /dev/null 2>&1; then
    echo "⚠️  vLLM 服务可能未运行: $VLLM_API_BASE"
    echo "💡 请确保 vLLM 服务正常运行"
fi

# 检查 RAG 服务 (如果启用)
if [ "$ENABLE_RAG" = "true" ]; then
    echo "🔍 检查 RAG 服务..."
    if ! curl -s "$RAG_SERVICE_URL" > /dev/null 2>&1; then
        echo "⚠️  RAG 服务可能未运行: $RAG_SERVICE_URL"
        echo "💡 如果不需要RAG，请使用 --no-rag 参数"
    fi
fi

# 创建日志目录
mkdir -p logs

echo ""
echo "🔄 启动主 API 服务..."
echo "📍 服务地址: http://localhost:$PORT"
echo "📝 日志文件: logs/main_api.log"
echo ""

# 启动主API服务
python main.py 2>&1 | tee logs/main_api.log

echo "🛑 主 API 服务已停止"
