#!/bin/bash
# 停止 Safe API 服务脚本

echo "🛑 停止 Safe API 服务..."

# 从 PID 文件停止服务
if [ -f "logs/front_intercept.pid" ]; then
    FRONT_PID=$(cat logs/front_intercept.pid)
    if kill -0 $FRONT_PID 2>/dev/null; then
        echo "🔄 停止前拦截服务 (PID: $FRONT_PID)..."
        kill $FRONT_PID
        echo "✅ 前拦截服务已停止"
    else
        echo "⚠️  前拦截服务已经停止"
    fi
    rm -f logs/front_intercept.pid
else
    echo "⚠️  未找到前拦截服务 PID 文件"
fi

if [ -f "logs/post_intercept.pid" ]; then
    POST_PID=$(cat logs/post_intercept.pid)
    if kill -0 $POST_PID 2>/dev/null; then
        echo "🔄 停止后拦截服务 (PID: $POST_PID)..."
        kill $POST_PID
        echo "✅ 后拦截服务已停止"
    else
        echo "⚠️  后拦截服务已经停止"
    fi
    rm -f logs/post_intercept.pid
else
    echo "⚠️  未找到后拦截服务 PID 文件"
fi

# 强制停止相关进程
echo "🔍 检查残留进程..."
pkill -f "front_intercept_api.py" 2>/dev/null && echo "✅ 清理前拦截残留进程"
pkill -f "post_intercept_api.py" 2>/dev/null && echo "✅ 清理后拦截残留进程"

echo "🎉 Safe API 服务停止完成!"
