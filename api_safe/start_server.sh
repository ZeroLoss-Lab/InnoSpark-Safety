#!/bin/bash

# 增强版拦截器API服务启动脚本
# 使用方法: ./start_server.sh [选项]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
API_HOST="0.0.0.0"
API_PORT="8001"
VLLM_API_BASE="http://localhost:8000"
RAG_SERVICE_URL="http://localhost:8000/retrieve"
API_KEY="your_api_key_here"

# 函数定义
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  增强版拦截器API服务启动脚本  ${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 检查Python环境
check_python() {
    print_info "检查Python环境..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 未安装"
        exit 1
    fi
    
    python_version=$(python3 --version 2>&1 | awk '{print $2}')
    print_success "Python版本: $python_version"
}

# 检查依赖包
check_dependencies() {
    print_info "检查Python依赖包..."
    
    required_packages=("fastapi" "uvicorn" "transformers" "torch" "aiohttp" "httpx")
    missing_packages=()
    
    for package in "${required_packages[@]}"; do
        if ! python3 -c "import $package" &> /dev/null; then
            missing_packages+=("$package")
        fi
    done
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        print_warning "缺少以下依赖包: ${missing_packages[*]}"
        echo "正在安装缺少的依赖包..."
        pip3 install "${missing_packages[@]}"
        print_success "依赖包安装完成"
    else
        print_success "所有依赖包已安装"
    fi
}

# 检查必要文件
check_files() {
    print_info "检查必要文件..."
    
    required_files=(
        "main.py"
        "config.py"
        "enhanced_interceptor.py"
        "rag_client.py"
        "rag_prompt_template.py"
    )
    
    missing_files=()
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        print_error "缺少以下必要文件: ${missing_files[*]}"
        exit 1
    fi
    
    print_success "所有必要文件存在"
}

# 创建演示数据
create_demo_data() {
    print_info "创建演示数据文件..."
    
    # 创建目录
    mkdir -p safe_api/data
    mkdir -p safe_api/models
    mkdir -p logs
    
    # 创建高敏感关键词文件
    if [ ! -f "safe_api/data/high_sensitive_keywords.json" ]; then
        cat > safe_api/data/high_sensitive_keywords.json << 'EOF'
{
  "keywords": [
    "placeholder_keyword_alpha",
    "placeholder_keyword_beta",
    "placeholder_keyword_gamma"
  ]
}
EOF
        print_success "创建高敏感关键词文件"
    fi
    
    # 创建次高敏感关键词文件
    if [ ! -f "safe_api/data/high_sensitive_keywords-2.json" ]; then
        cat > safe_api/data/high_sensitive_keywords-2.json << 'EOF'
{
  "keywords": [
    "placeholder_topic_alpha",
    "placeholder_topic_beta",
    "placeholder_topic_gamma"
  ]
}
EOF
        print_success "创建次高敏感关键词文件"
    fi
    
    # 创建1w黑名单文件
    if [ ! -f "safe_api/data/blacklist_1w.json" ]; then
        cat > safe_api/data/blacklist_1w.json << 'EOF'
{
  "keywords": [
    "placeholder_category_alpha",
    "placeholder_category_beta",
    "placeholder_category_gamma"
  ]
}
EOF
        print_success "创建1w黑名单文件"
    fi
    
    # 创建API密钥文件
    if [ ! -f "api_keys.json" ]; then
        cat > api_keys.json << EOF
{
  "$API_KEY": {
    "description": "默认API密钥",
    "created_at": "$(date -Iseconds)",
    "enabled": true,
    "usage_count": 0,
    "last_used": null
  }
}
EOF
        print_success "创建API密钥文件"
    fi
}

# 设置环境变量
setup_environment() {
    print_info "设置环境变量..."
    
    export VLLM_API_BASE="$VLLM_API_BASE"
    export HOST="$API_HOST"
    export PORT="$API_PORT"
    export API_KEY="$API_KEY"
    export ENABLE_MULTI_API_KEYS="true"
    
    # 启用拦截器
    export ENABLE_FRONT_INTERCEPT="true"
    export ENABLE_POST_INTERCEPT="true"
    export USE_LOCAL_INTERCEPT="true"
    
    # 启用RAG系统
    export ENABLE_RAG="true"
    export RAG_SERVICE_URL="$RAG_SERVICE_URL"
    export RAG_TOP_K="5"
    export RAG_TIMEOUT="10.0"
    
    # BERT双阈值配置
    export BERT_FRONT_HIGH_THRESHOLD="0.97"
    export BERT_FRONT_LOW_THRESHOLD="0.00002"
    export BERT_POST_THRESHOLD="0.5"
    
    # 数据文件路径
    export HIGH_SENSITIVE_KEYWORDS_PATH="./safe_api/data/high_sensitive_keywords.json"
    export MEDIUM_SENSITIVE_KEYWORDS_PATH="./safe_api/data/high_sensitive_keywords-2.json"
    export BLACKLIST_1W_PATH="./safe_api/data/blacklist_1w.json"
    
    # 超时配置
    export INTERCEPT_TIMEOUT="5.0"
    
    # 日志配置
    export LOG_LEVEL="INFO"
    export LOG_FILE="logs/api.log"
    export USER_LOG_FILE="logs/user_requests.log"
    
    print_success "环境变量设置完成"
}

# 检查服务状态
check_services() {
    print_info "检查相关服务状态..."
    
    # 检查vLLM服务
    if curl -s "$VLLM_API_BASE/v1/models" > /dev/null 2>&1; then
        print_success "vLLM服务运行正常 ($VLLM_API_BASE)"
    else
        print_warning "vLLM服务不可访问 ($VLLM_API_BASE)"
        print_info "请确保vLLM服务已启动"
    fi
    
    # 检查RAG服务
    if curl -s -X POST "$RAG_SERVICE_URL" -H "Content-Type: application/json" -d '{"query":"test","top_k":1}' > /dev/null 2>&1; then
        print_success "RAG服务运行正常 ($RAG_SERVICE_URL)"
    else
        print_warning "RAG服务不可访问 ($RAG_SERVICE_URL)"
        print_info "RAG服务不可用时将禁用RAG功能"
        export ENABLE_RAG="false"
    fi
}

# 启动API服务
start_api_server() {
    print_info "启动增强版拦截器API服务..."
    print_info "服务地址: http://$API_HOST:$API_PORT"
    print_info "API文档: http://$API_HOST:$API_PORT/docs"
    print_info "使用Ctrl+C停止服务"
    
    echo ""
    echo "📋 当前配置:"
    echo "  vLLM服务: $VLLM_API_BASE"
    echo "  前拦截: $ENABLE_FRONT_INTERCEPT"
    echo "  后拦截: $ENABLE_POST_INTERCEPT"
    echo "  RAG系统: $ENABLE_RAG"
    echo "  本地模式: $USE_LOCAL_INTERCEPT"
    echo ""
    
    # 启动服务
    python3 main.py
}

# 显示帮助信息
show_help() {
    echo "增强版拦截器API服务启动脚本"
    echo ""
    echo "使用方法:"
    echo "  $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help           显示帮助信息"
    echo "  -p, --port PORT      指定API服务端口 (默认: 8001)"
    echo "  -v, --vllm URL       指定vLLM服务地址 (默认: http://localhost:8000)"
    echo "  -r, --rag URL        指定RAG服务地址 (默认: http://localhost:8000/retrieve)"
    echo "  -k, --api-key KEY    指定API密钥 (默认: your_api_key_here)"
    echo "  --no-rag             禁用RAG系统"
    echo "  --no-front           禁用前拦截"
    echo "  --no-post            禁用后拦截"
    echo "  --check-only         仅检查环境，不启动服务"
    echo ""
    echo "示例:"
    echo "  $0                   # 使用默认配置启动"
    echo "  $0 -p 8002           # 在8002端口启动"
    echo "  $0 --no-rag          # 禁用RAG功能启动"
    echo "  $0 --check-only      # 仅检查环境"
}

# 解析命令行参数
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -p|--port)
                API_PORT="$2"
                shift 2
                ;;
            -v|--vllm)
                VLLM_API_BASE="$2"
                shift 2
                ;;
            -r|--rag)
                RAG_SERVICE_URL="$2"
                shift 2
                ;;
            -k|--api-key)
                API_KEY="$2"
                shift 2
                ;;
            --no-rag)
                ENABLE_RAG="false"
                shift
                ;;
            --no-front)
                ENABLE_FRONT_INTERCEPT="false"
                shift
                ;;
            --no-post)
                ENABLE_POST_INTERCEPT="false"
                shift
                ;;
            --check-only)
                CHECK_ONLY="true"
                shift
                ;;
            *)
                print_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# 主函数
main() {
    # 解析命令行参数
    parse_arguments "$@"
    
    # 显示标题
    print_header
    
    # 检查环境
    check_python
    check_dependencies
    check_files
    
    # 创建演示数据
    create_demo_data
    
    # 设置环境变量
    setup_environment
    
    # 检查服务状态
    check_services
    
    # 如果只是检查环境，则退出
    if [ "$CHECK_ONLY" = "true" ]; then
        print_success "环境检查完成，所有准备就绪！"
        exit 0
    fi
    
    # 启动API服务
    start_api_server
}

# 捕获中断信号
trap 'echo -e "\n${YELLOW}⏹️  服务已停止${NC}"; exit 0' INT

# 运行主函数
main "$@"
