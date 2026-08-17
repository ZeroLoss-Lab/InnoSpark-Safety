#!/bin/bash

# 安全拦截API系统环境变量设置脚本

echo "🔧 设置安全拦截API系统环境变量..."

# 前拦截API配置
export MODEL_FRONT_PATH="./models/front_model"
export BLACKLIST_1W_PATH="./data/blacklist_1w9_cut.json"
export HIGH_SENSITIVE_KEYWORDS_PATH="./data/high_sensitive_keywords9_cut.json"

# 后拦截API配置
export MODEL_POST_PATH="./models/post_model"

echo "✅ 环境变量设置完成"
echo ""
echo "📋 当前配置:"
echo "  MODEL_FRONT_PATH: $MODEL_FRONT_PATH"
echo "  MODEL_POST_PATH: $MODEL_POST_PATH"
echo "  BLACKLIST_1W_PATH: $BLACKLIST_1W_PATH"
echo "  HIGH_SENSITIVE_KEYWORDS_PATH: $HIGH_SENSITIVE_KEYWORDS_PATH"
echo ""
echo "💡 使用方法:"
echo "  source setup_env.sh"
echo "  python start_services.py"
