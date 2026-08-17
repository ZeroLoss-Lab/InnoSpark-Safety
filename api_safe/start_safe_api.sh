#!/bin/bash
# Safe API 启动脚本
# 负责启动前拦截和后拦截服务，配置BERT阈值

echo "🚀 启动 Safe API 服务..."

# 检查必要文件
check_file() {
    if [ ! -f "$1" ]; then
        echo "❌ 文件不存在: $1"
        exit 1
    fi
}

echo "📁 检查必要文件..."
check_file "safe_api/front_intercept_api.py"
check_file "safe_api/post_intercept_api.py"
check_file "safe_api/data/high_sensitive_keywords.json"
check_file "safe_api/data/blacklist_1w.json"

# 设置 Safe API 配置（拦截逻辑和阈值）
echo "⚙️  配置 Safe API 参数..."

# BERT 阈值配置
export BERT_FRONT_HIGH_THRESHOLD=0.97      # 前拦截高阈值
export BERT_FRONT_LOW_THRESHOLD=0.00002    # 前拦截低阈值  
export BERT_POST_THRESHOLD=0.5             # 后拦截阈值

# 模型路径配置
export MODEL_FRONT_PATH="./safe_api/models/front_model"
export MODEL_POST_PATH="./safe_api/models/post_model"

# 关键词库配置
export HIGH_SENSITIVE_KEYWORDS_PATH="./safe_api/data/high_sensitive_keywords.json"
export BLACKLIST_1W_PATH="./safe_api/data/blacklist_1w.json"

# 注意：Safe API 只负责拦截判断，不需要配置安全响应消息
# 安全响应消息由主 API 统一管理

echo "📊 Safe API 配置:"
echo "  前拦截高阈值: $BERT_FRONT_HIGH_THRESHOLD"
echo "  前拦截低阈值: $BERT_FRONT_LOW_THRESHOLD"
echo "  后拦截阈值: $BERT_POST_THRESHOLD"
echo "  前拦截模型: $MODEL_FRONT_PATH"
echo "  后拦截模型: $MODEL_POST_PATH"
echo "  职责: 拦截判断（安全响应消息由主API管理）"

# 创建日志目录
mkdir -p logs

# 启动前拦截服务 (端口 8001)
echo "🔄 启动前拦截服务 (端口 8001)..."
python safe_api/front_intercept_api.py > logs/front_intercept.log 2>&1 &
FRONT_PID=$!
echo "  前拦截服务 PID: $FRONT_PID"

# 等待前拦截服务启动
sleep 3

# 检查前拦截服务是否启动成功
if curl -s http://localhost:8001/health > /dev/null; then
    echo "✅ 前拦截服务启动成功"
else
    echo "❌ 前拦截服务启动失败"
    kill $FRONT_PID 2>/dev/null
    exit 1
fi

# 启动后拦截服务 (端口 8002)
echo "🔄 启动后拦截服务 (端口 8002)..."
python safe_api/post_intercept_api.py > logs/post_intercept.log 2>&1 &
POST_PID=$!
echo "  后拦截服务 PID: $POST_PID"

# 等待后拦截服务启动
sleep 3

# 检查后拦截服务是否启动成功
if curl -s http://localhost:8002/health > /dev/null; then
    echo "✅ 后拦截服务启动成功"
else
    echo "❌ 后拦截服务启动失败"
    kill $FRONT_PID $POST_PID 2>/dev/null
    exit 1
fi

# 保存 PID 到文件
echo $FRONT_PID > logs/front_intercept.pid
echo $POST_PID > logs/post_intercept.pid

echo ""
echo "🎉 Safe API 服务启动完成!"
echo "📍 服务地址:"
echo "  前拦截: http://localhost:8001"
echo "  后拦截: http://localhost:8002"
echo "📝 日志文件:"
echo "  前拦截: logs/front_intercept.log"
echo "  后拦截: logs/post_intercept.log"
echo ""
echo "🛑 停止服务: ./stop_safe_api.sh"
echo "📊 测试服务: ./test_safe_api.sh"

# 保持脚本运行，监控服务状态
echo "⏳ 监控服务状态 (Ctrl+C 停止)..."
trap "echo ''; echo '🛑 停止 Safe API 服务...'; kill $FRONT_PID $POST_PID 2>/dev/null; exit 0" INT

while true; do
    sleep 10
    
    # 检查服务状态
    if ! kill -0 $FRONT_PID 2>/dev/null; then
        echo "⚠️  前拦截服务已停止"
        break
    fi
    
    if ! kill -0 $POST_PID 2>/dev/null; then
        echo "⚠️  后拦截服务已停止"  
        break
    fi
    
    # 每分钟显示一次状态
    if [ $(($(date +%s) % 60)) -eq 0 ]; then
        echo "✅ Safe API 服务运行正常 ($(date))"
    fi
done

echo "🛑 Safe API 服务已停止"
