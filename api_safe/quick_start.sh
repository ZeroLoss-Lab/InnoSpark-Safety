#!/bin/bash
# 快速启动脚本 - 一键启动完整系统

echo "🚀 快速启动统一架构系统"
echo ""

# 检查必要文件
if [ ! -f "start_safe_api.sh" ] || [ ! -f "start_main_api.sh" ]; then
    echo "❌ 启动脚本不存在"
    exit 1
fi

echo "📋 启动选项:"
echo "  1. 完整功能 (前拦截 + 后拦截 + RAG)"
echo "  2. 基础拦截 (前拦截 + 后拦截，无RAG)"
echo "  3. 仅前拦截 + RAG"
echo "  4. 自定义配置"
echo "  5. 仅启动 Safe API"
echo "  6. 仅启动主 API (需要 Safe API 已运行)"
echo ""

read -p "请选择启动模式 [1-6]: " choice

case $choice in
    1)
        echo "🎯 启动完整功能模式..."
        echo "📊 配置: 前拦截=ON, 后拦截=ON, RAG=ON"
        echo ""
        
        echo "🔄 步骤 1/2: 启动 Safe API 服务..."
        ./start_safe_api.sh &
        SAFE_PID=$!
        
        echo "⏳ 等待 Safe API 启动..."
        sleep 10
        
        echo "🔄 步骤 2/2: 启动主 API 服务..."
        ./start_main_api.sh
        ;;
        
    2)
        echo "🎯 启动基础拦截模式..."
        echo "📊 配置: 前拦截=ON, 后拦截=ON, RAG=OFF"
        echo ""
        
        echo "🔄 步骤 1/2: 启动 Safe API 服务..."
        ./start_safe_api.sh &
        SAFE_PID=$!
        
        echo "⏳ 等待 Safe API 启动..."
        sleep 10
        
        echo "🔄 步骤 2/2: 启动主 API 服务..."
        ./start_main_api.sh --no-rag
        ;;
        
    3)
        echo "🎯 启动前拦截+RAG模式..."
        echo "📊 配置: 前拦截=ON, 后拦截=OFF, RAG=ON"
        echo ""
        
        echo "🔄 步骤 1/2: 启动 Safe API 服务..."
        ./start_safe_api.sh &
        SAFE_PID=$!
        
        echo "⏳ 等待 Safe API 启动..."
        sleep 10
        
        echo "🔄 步骤 2/2: 启动主 API 服务..."
        ./start_main_api.sh --no-post
        ;;
        
    4)
        echo "🎯 自定义配置模式..."
        echo ""
        
        read -p "启用前拦截? [Y/n]: " front_choice
        read -p "启用后拦截? [Y/n]: " post_choice
        read -p "启用RAG系统? [Y/n]: " rag_choice
        read -p "vLLM服务地址 [http://localhost:8000]: " vllm_url
        read -p "主API端口 [8080]: " api_port
        read -p "自定义安全响应消息 [使用默认]: " custom_message
        
        # 设置默认值
        vllm_url=${vllm_url:-"http://localhost:8000"}
        api_port=${api_port:-8080}
        
        # 设置自定义安全响应消息
        if [ -n "$custom_message" ]; then
            export SAFETY_RESPONSE_MESSAGE="$custom_message"
        fi
        
        # 构建启动参数
        main_args=""
        if [[ $front_choice =~ ^[Nn] ]]; then
            main_args="$main_args --no-front"
        fi
        if [[ $post_choice =~ ^[Nn] ]]; then
            main_args="$main_args --no-post"
        fi
        if [[ $rag_choice =~ ^[Nn] ]]; then
            main_args="$main_args --no-rag"
        fi
        main_args="$main_args --vllm-url $vllm_url --port $api_port"
        
        echo ""
        echo "📊 自定义配置:"
        echo "  前拦截: $(if [[ ! $front_choice =~ ^[Nn] ]]; then echo 'ON'; else echo 'OFF'; fi)"
        echo "  后拦截: $(if [[ ! $post_choice =~ ^[Nn] ]]; then echo 'ON'; else echo 'OFF'; fi)"
        echo "  RAG系统: $(if [[ ! $rag_choice =~ ^[Nn] ]]; then echo 'ON'; else echo 'OFF'; fi)"
        echo "  vLLM地址: $vllm_url"
        echo "  主API端口: $api_port"
        if [ -n "$custom_message" ]; then
            echo "  安全响应消息: $custom_message"
        else
            echo "  安全响应消息: 使用默认"
        fi
        echo ""
        
        if [[ ! $front_choice =~ ^[Nn] ]] || [[ ! $post_choice =~ ^[Nn] ]]; then
            echo "🔄 步骤 1/2: 启动 Safe API 服务..."
            ./start_safe_api.sh &
            SAFE_PID=$!
            
            echo "⏳ 等待 Safe API 启动..."
            sleep 10
        fi
        
        echo "🔄 步骤 2/2: 启动主 API 服务..."
        ./start_main_api.sh $main_args
        ;;
        
    5)
        echo "🎯 仅启动 Safe API 服务..."
        ./start_safe_api.sh
        ;;
        
    6)
        echo "🎯 仅启动主 API 服务..."
        echo "⚠️  请确保 Safe API 服务已在运行"
        sleep 2
        ./start_main_api.sh
        ;;
        
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac
