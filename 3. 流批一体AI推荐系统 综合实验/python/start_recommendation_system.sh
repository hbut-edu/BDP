#!/bin/bash

echo "========================================="
echo "🚀 流批一体AI推荐系统启动脚本"
echo "========================================="

BASE_DIR=$(dirname "$0")
cd "$BASE_DIR"

echo ""
echo "📋 检查依赖..."
command -v python3 >/dev/null 2>&1 || { echo >&2 "❌ 需要安装Python3"; exit 1; }

echo ""
echo "📦 检查Kafka主题..."
if ! docker ps | grep -q bigdata-kafka; then
    echo "⚠️  Kafka容器未运行，请先启动docker-compose"
    echo "   命令: docker compose up -d"
    exit 1
fi

echo ""
echo "========================================="
echo "📖 使用说明"
echo "========================================="
echo "请在不同的终端中运行以下命令："
echo ""
echo "终端1 - 用户行为数据生成器:"
echo "  python user_behavior_producer.py"
echo ""
echo "终端2 - 实时推荐服务:"
echo "  python realtime_recommendation_service.py"
echo ""
echo "终端3 - 推荐结果监控:"
echo "  python advanced_recommendation_consumer.py"
echo ""
echo "终端4 - 推荐算法演示:"
echo "  python recommendation_algorithms.py"
echo ""
echo "========================================="
echo ""
echo "💡 提示：确保已安装 kafka-python"
echo "   pip install kafka-python"
echo ""
