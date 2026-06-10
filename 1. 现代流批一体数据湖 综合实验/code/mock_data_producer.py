import json
import time
import random
from faker import Faker
from kafka import KafkaProducer
from kafka.errors import KafkaError

# 初始化 Faker，生成中文测试数据
fake = Faker('zh_CN')

# Kafka 配置 (对应刚才 docker-compose 暴露的端口)
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
TOPIC_NAME = 'ecommerce_orders'


def create_kafka_producer():
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BOOTSTRAP_SERVERS],
            # 将字典序列化为 JSON 字符串并编码为 UTF-8
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            retries=3
        )
        return producer
    except Exception as e:
        print(f"连接 Kafka 失败，请检查端口: {e}")
        return None


def generate_mock_order():
    # 模拟商品池
    product_pool = ['机械键盘', '游戏鼠标', '27寸显示器', '降噪耳机', '智能手表', '显卡', 'ITX机箱']

    order_data = {
        "order_id": fake.uuid4(),
        "user_id": random.randint(10000, 99999),
        "user_name": fake.name(),
        "product_name": random.choice(product_pool),
        "amount": round(random.uniform(50.0, 8000.0), 2),
        "status": random.choice(['PAID', 'UNPAID', 'REFUNDED']),
        "create_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    }
    return order_data


def main():
    print(f"正在连接 Kafka: {KAFKA_BOOTSTRAP_SERVERS}...")
    producer = create_kafka_producer()

    if not producer:
        return

    print(f"连接成功！开始向 Topic '{TOPIC_NAME}' 发送数据...")
    print("按 Ctrl+C 可以停止发送。\n")

    try:
        while True:
            order = generate_mock_order()
            future = producer.send(TOPIC_NAME, value=order)

            # 等待确认发送结果
            try:
                record_metadata = future.get(timeout=10)
                print(
                    f"[成功发送] 分区: {record_metadata.partition}, 偏移量: {record_metadata.offset} | 数据: {order['product_name']} - {order['amount']}元")
            except KafkaError as e:
                print(f"[发送失败]: {e}")

            # 模拟现实订单产生的间隔，随机休眠 0.5 到 2 秒
            time.sleep(random.uniform(0.5, 2.0))

    except KeyboardInterrupt:
        print("\n停止发送数据...")
    finally:
        if producer:
            producer.flush()
            producer.close()


if __name__ == '__main__':
    main()