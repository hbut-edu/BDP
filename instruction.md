# 《云计算与大数据处理》 现代流批一体数据湖 (Streaming Lakehouse) 综合实验手册

**实验环境特别说明：**
请严格遵循手册中的版本号进行操作，以避免底层组件的兼容性报错。

---

## 准备阶段、 课前环境基建：开发环境配置 (双方案可选)

在编写任何代码之前，我们需要准备好大数据的开发环境和底层通讯包。这里提供两种开发环境配置方案，**请任选其一**。

### 方案 A：传统本地开发模式 (依托宿主机 Java 环境)
这是最经典的开发模式，代码在本地编译，通过跨版本编译技术打包。
1. **安装环境：** 确保电脑已安装 JDK 17 和 Maven。
2. **VS Code 插件：** 在 VS Code 扩展商店安装 `Extension Pack for Java` 和 `Python` 插件。
3. *(由于 Java 17 的模块强封装限制，后续在本地运行 Flink 时需配置专门的反射逃逸参数，详见第三阶段)*。

### 方案 B：Dev Containers 云原生隔离模式 (工业方案，强烈推荐，彻底告别环境报错)
这是工业界目前最先进的“容器化开发”模式。您的本地电脑**不需要安装任何 JDK 和 Maven**，VS Code 会将核心引擎“注射”到一个纯净的 Java 11 容器中，实现开发环境与生产环境的 100% 统一。
1. **前置条件：** 电脑已安装 Docker Desktop 并正在运行。
2. **VS Code 插件：** 安装微软官方扩展 `Dev Containers`。
3. **开启魔法：**
   * 在您的项目根目录下，新建文件夹 `.devcontainer`。
   * 在该文件夹内新建文件 `devcontainer.json`，完整粘贴以下配置：
     ```json
     {
         "name": "BigData Java11 Env",
         "image": "[mcr.microsoft.com/devcontainers/java:11](https://mcr.microsoft.com/devcontainers/java:11)",
         "features": {
             "ghcr.io/devcontainers/features/maven:1": {
                 "version": "latest"
             }
         },
         "customizations": {
             "vscode": {
                 "extensions": [
                     "vscjava.vscode-java-pack",
                     "ms-python.python"
                 ]
             }
         }
     }
     ```
   * 在 VS Code 左下角点击绿色的 `><` 图标，选择 **“Reopen in Container (在容器中重新打开)”**。
   * *效果：VS Code 界面仍在本地，但终端、JDK 11、Maven 均已在容器内准备就绪！*

### 核心依赖共享夹准备 (双方案均需执行)
1. 在电脑任意位置新建一个主文件夹，命名为 `bigdata-lab`。**接下来的所有操作均在此文件夹内完成。**
2. 在 `bigdata-lab` 内部，新建一个名为 `flink-jars` 的文件夹。
3. 请通过浏览器或 Maven 仓库，下载以下 **3 个核心 Jar 包**，并放入 `flink-jars` 文件夹中（这些包将挂载给 Docker，让集群认识数据湖格式）：
    * `flink-sql-connector-kafka-3.0.1-1.18.jar`
    * `paimon-flink-1.18-0.8.0.jar`
    * `flink-s3-fs-hadoop-1.18.0.jar`

---

## 第一阶段：全局底层集群拉起 (Docker Compose)

在 `bigdata-lab` 根目录下新建文件 `compose.yaml`。本配置不仅拉起了流计算所需的基建，还额外引入了 **Spark 独立集群 (Standalone Cluster)**，让您在单机上体验分布式算力。

```yaml
# 新版 Docker Compose 已全面废弃顶层 version 字段，直接从 services 开始定义即可
services: 

  # ==========================================
  # 1. 消息中间件：Apache Kafka (官方原版，完美兼容 Apple M 系列芯片)
  # ==========================================
  kafka:
    image: apache/kafka:3.7.0 # 使用官方纯正镜像，杜绝第三方魔改引发的兼容性故障
    container_name: bigdata-kafka # 固定容器名称，方便后期使用 docker logs 查看运行日志
    ports:
      - "9092:9092" # 端口映射：将容器内的 9092 暴露给 Mac 宿主机的 9092 端口
    environment:
      - KAFKA_NODE_ID=1 # 集群节点唯一标识，单机实验模式设为 1
      - KAFKA_PROCESS_ROLES=broker,controller # 核心机制：启用 KRaft 模式，让该节点既做数据存储(broker)又做集群调度(controller)，彻底抛弃笨重的 Zookeeper
      
      # 【核心网络隔离配置：定义三扇监听门】
      # 29092：面向 Docker 内部局域网的后门，供 Flink/Dinky 等内部容器通信
      # 9093： 面向集群内部控制器选举的专用通道
      # 9092： 面向外部 Mac 宿主机的正门，供 Python 模拟数据脚本接入
      - KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:29092,CONTROLLER://0.0.0.0:9093,EXTERNAL://0.0.0.0:9092
      
      # 【核心网络穿透配置：告诉客户端该用什么地址连进来】
      # 如果是 Docker 内的兄弟组件，请通过 kafka:29092 连我；如果是外面的电脑，请通过 localhost:9092 连我
      - KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:29092,EXTERNAL://localhost:9092
      - KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,EXTERNAL:PLAINTEXT # 协议映射：全部使用明文不加密传输
      - KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER # 指定控制器的通信通道名称
      - KAFKA_CONTROLLER_QUORUM_VOTERS=1@localhost:9093 # 选举配置：单机模式下投票节点只有自己
      
      # 【容错与副本配置：单机模式防报错补丁】
      - KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 # 强制将偏移量主题的副本数降为 1（否则默认需 3 台机器）
      - KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR=1 # 强制将事务日志副本降为 1
      - KAFKA_TRANSACTION_STATE_LOG_MIN_ISR=1 # 最小同步副本数降为 1
      - KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS=0 # 消费者组启动无延迟，立刻开始分配数据
    networks:
      - bigdata-network # 加入自定义的虚拟局域网

  # ==========================================
  # 2. 对象存储：MinIO (数据湖的物理底座，AWS S3 协议的开源平替)
  # ==========================================
  minio:
    image: minio/minio:latest # 始终拉取最新的 MinIO 镜像
    container_name: bigdata-minio
    ports:
      - "9000:9000" # API 通信端口：Flink 写文件、Spark 读文件，全部走这个端口
      - "9001:9001" # Web UI 端口：我们在浏览器查看湖仓里的目录结构，走这个端口
    environment:
      - MINIO_ROOT_USER=admin # 初始化 MinIO 超级管理员账号
      - MINIO_ROOT_PASSWORD=password123 # 初始化 MinIO 超级管理员密码
    command: server /data --console-address ":9001" # 启动命令：作为服务端运行，数据存放在容器的 /data 目录，Web控制台绑在 9001
    networks:
      - bigdata-network

  # ==========================================
  # 3. 实时计算：Flink 集群 (JobManager 核心大脑 / 包工头)
  # ==========================================
  jobmanager:
    image: flink:1.18.0-scala_2.12-java11 # 生产环境强推 Java 11 镜像，避免 JDK 17+ 的强封装反射报错
    container_name: bigdata-flink-jm
    ports:
      - "8081:8081" # 映射 Flink 极其漂亮的 Web 监控大屏
    command: jobmanager # 指定该容器作为调度节点运行
    volumes:
      # 【极其关键的插件挂载】：将宿主机的 flink-jars 目录挂载到容器的类加载路径中，让 Flink 动态认识 Kafka 和 Paimon
      - ./flink-jars:/opt/flink/lib/ext_jars 
    networks:
      - bigdata-network

  # ==========================================
  # 4. 实时计算：Flink 集群 (TaskManager 干活的工人)
  # ==========================================
  taskmanager:
    image: flink:1.18.0-scala_2.12-java11
    container_name: bigdata-flink-tm
    depends_on:
      - jobmanager # 依赖控制：必须等大脑(JobManager)启动后，工人才启动，防止失联报错
    command: taskmanager # 指定该容器作为计算执行节点运行
    volumes:
      # 工人同样需要加载这些 Jar 包才能真正执行读写操作
      - ./flink-jars:/opt/flink/lib/ext_jars 
    networks:
      - bigdata-network

  # ==========================================
  # 5. 敏捷数据平台：Dinky (企业级一站式 Flink SQL 网页开发中台)
  # ==========================================
  dinky:
    image: dinkydocker/dinky-standalone:1.0.3 # 独立版镜像自带轻量级 H2 数据库，免去额外部署 MySQL 的麻烦，极度适合教学
    container_name: bigdata-dinky
    ports:
      - "8888:8888" # Dinky 网页端的对外访问端口
    depends_on:
      - jobmanager # 依赖 Flink 集群就绪
    volumes:
      # Dinky 在你敲击键盘做 SQL 语法检查时，也需要读取这些外部依赖包进行校验
      - ./flink-jars:/opt/dinky/custom_jars
    networks:
      - bigdata-network

  # ==========================================
  # 6. 离线分析：Spark 独立集群 (Master 资源大管家)
  # ==========================================
  spark-master:
    image: apache/spark:3.3.2 # 锁死 3.3.2 版本，这是与 Paimon 0.8.0 配合最稳定、无冲突的黄金版本
    container_name: bigdata-spark-master
    # 启动官方的 Master 守护进程，并明确指定主机名和绑定的两个核心端口
    command: /opt/spark/bin/spark-class org.apache.spark.deploy.master.Master --host spark-master --port 7077 --webui-port 8080
    ports:
      - "8080:8080" # Spark 集群 Web 大屏（您可以直观看到有几个 Worker 在待命）
      - "7077:7077" # 内部 RPC 调度端口（包工头接单的专属电话号码）
    volumes:
      # 【突破 NAT 隔离墙的挂载】：将宿主机当前的实验目录挂载到容器内，方便后续我们直接用 docker exec 在内部提交脚本
      - ./:/opt/spark-apps 
    networks:
      - bigdata-network

  # ==========================================
  # 7. 离线分析：Spark 独立集群 (Worker 节点/打工人)
  # ==========================================
  spark-worker:
    image: apache/spark:3.3.2
    depends_on:
      - spark-master
    # 启动 Worker 进程，并告诉它大管家的通信地址 (向 spark-master 的 7077 端口报到)
    command: /opt/spark/bin/spark-class org.apache.spark.deploy.worker.Worker spark://spark-master:7077
    environment:
      - SPARK_WORKER_CORES=2 # 资源隔离：限制每个工人最多只能提供 2 个 CPU 核心
      - SPARK_WORKER_MEMORY=2G # 资源隔离：限制每个工人最多只能使用 2G 内存
    networks:
      - bigdata-network

# 统一声明网络拓扑
networks: 
  bigdata-network:
    driver: bridge # 创建桥接网络，让上述 7 个容器能在内部通过服务名(如 kafka, minio)互相 Ping 通
```
**启动与扩容魔法：** 在终端执行以下命令拉起所有服务，并**动态申请 3 个 Spark Worker (模拟 3 台分布式计算节点)**：
```bash
docker compose up -d --scale spark-worker=3
```

---

## 第二阶段：源头活水 (Python 模拟电商订单流入)

在 `bigdata-lab` 目录下新建 `mock_data_producer.py`。
*(执行前，请在终端执行 `pip install kafka-python`)*

```python
import json 
import time 
import random 
from kafka import KafkaProducer 
from datetime import datetime 

# 1. 初始化 Kafka 生产者实例
producer = KafkaProducer(
    # 宿主机连接 Kafka 暴露的 9092 外网大门
    bootstrap_servers=['localhost:9092'], 
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

products = ["iPhone 15", "MacBook Pro", "iPad Air", "AirPods"]
statuses = ["UNPAID", "PAID", "SHIPPED"]

print("🚀 业务系统上线，开始向 Kafka 发送实时订单...")
order_id_counter = 1 

# 2. 开启死循环产生数据
while True:
    data = {
        "order_id": f"ORD_{order_id_counter}", 
        "product_name": random.choice(products), 
        "amount": round(random.uniform(100.0, 20000.0), 2), 
        "status": random.choice(statuses), 
        "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
    }
    producer.send('ecommerce_orders', value=data)
    print(f"发送成功: {data}") 
    order_id_counter += 1 
    time.sleep(1) # 休眠1秒，稳定输出水流
```
**开始供水：** 运行 `python mock_data_producer.py`，保持终端开启。

---

## 第三阶段：流式入湖核心 (双轨并行的 Flink 实战)

### 轨道 A：VS Code 本地 Java 底层工程化实战

**1. 初始化 Maven 项目**
在 `bigdata-lab` 目录下，新建文件夹 `flink-java-project`。通过 VS Code 单独打开该文件夹。

**2. 编写带有交叉编译配置的 `pom.xml`**
在项目根目录新建 `pom.xml`，这是解决异构环境的核心密码：
```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="[http://maven.apache.org/POM/4.0.0](http://maven.apache.org/POM/4.0.0)"
         xmlns:xsi="[http://www.w3.org/2001/XMLSchema-instance](http://www.w3.org/2001/XMLSchema-instance)"
         xsi:schemaLocation="[http://maven.apache.org/POM/4.0.0](http://maven.apache.org/POM/4.0.0) [http://maven.apache.org/xsd/maven-4.0.0.xsd](http://maven.apache.org/xsd/maven-4.0.0.xsd)">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.edu.bigdata</groupId> 
    <artifactId>flink-java-project</artifactId> 
    <version>1.0-SNAPSHOT</version> 

    <properties>
        <maven.compiler.release>11</maven.compiler.release>
        <flink.version>1.18.0</flink.version> 
    </properties>

    <dependencies>
        <dependency><groupId>org.apache.flink</groupId><artifactId>flink-clients</artifactId><version>${flink.version}</version></dependency>
        <dependency><groupId>org.apache.flink</groupId><artifactId>flink-table-api-java-bridge</artifactId><version>${flink.version}</version></dependency>
        <dependency><groupId>org.apache.flink</groupId><artifactId>flink-table-planner-loader</artifactId><version>${flink.version}</version></dependency>
        <dependency><groupId>org.apache.flink</groupId><artifactId>flink-table-runtime</artifactId><version>${flink.version}</version></dependency>
        <dependency><groupId>org.apache.flink</groupId><artifactId>flink-sql-connector-kafka</artifactId><version>3.0.1-1.18</version></dependency>
        <dependency><groupId>org.apache.paimon</groupId><artifactId>paimon-flink-1.18</artifactId><version>0.8.0</version></dependency>
        <dependency><groupId>org.apache.flink</groupId><artifactId>flink-s3-fs-hadoop</artifactId><version>${flink.version}</version></dependency>
    </dependencies>
</project>
```

**3. 配置 Java 反射逃逸 (`.vscode/launch.json`)**
*(注：如果您采用的是 Dev Containers 方案 B，您已经在 Java 11 容器内，无需此配置)*。
如果使用宿主机 Java 17，新建 `.vscode/launch.json` 突破强封装限制：
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "type": "java",
            "name": "运行 Flink 双流应用",
            "request": "launch",
            "mainClass": "com.edu.bigdata.FlinkDualStream",
            "projectName": "flink-java-project",
            "vmArgs": "--add-opens java.base/java.lang=ALL-UNNAMED --add-opens java.base/java.util=ALL-UNNAMED --add-opens java.base/java.math=ALL-UNNAMED --add-opens java.base/java.time=ALL-UNNAMED --add-opens java.base/java.net=ALL-UNNAMED --add-opens java.base/java.nio=ALL-UNNAMED"
        }
    ]
}
```

**4. 编写流处理逻辑 `FlinkDualStream.java`**
新建 `src/main/java/com/edu/bigdata/FlinkDualStream.java`：
```java
package com.edu.bigdata;

import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.table.api.EnvironmentSettings;
import org.apache.flink.table.api.StatementSet;
import org.apache.flink.table.api.TableEnvironment;
import org.apache.flink.table.api.bridge.java.StreamTableEnvironment;

public class FlinkDualStream {
    public static void main(String[] args) throws Exception {
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        env.setParallelism(1); 
        // 开启 Checkpoint，Paimon 依赖此机制实现事务写盘
        env.enableCheckpointing(10000); 
        
        TableEnvironment tEnv = StreamTableEnvironment.create(env, EnvironmentSettings.inStreamingMode());

        tEnv.executeSql(
            "CREATE TEMPORARY TABLE kafka_source (order_id STRING, product_name STRING, amount DOUBLE, status STRING, create_time STRING) " +
            // 注意：如果在宿主机运行，连接 localhost:9092；如果在 Dev Container 中运行，连接 kafka:29092
            "WITH ('connector' = 'kafka', 'topic' = 'ecommerce_orders', 'properties.bootstrap.servers' = 'localhost:9092', 'scan.startup.mode' = 'latest-offset', 'format' = 'json')"
        );
        
        tEnv.executeSql(
            "CREATE CATALOG paimon_catalog WITH (" +
            "  'type' = 'paimon', 'warehouse' = 's3://paimon-data/warehouse', " +
            // 注意：如果在宿主机运行，连接 localhost:9000；如果在 Dev Container 中运行，连接 minio:9000
            "  's3.endpoint' = 'http://localhost:9000', 's3.access-key' = 'admin', 's3.secret-key' = 'password123', 's3.path.style.access' = 'true'" +
            ")"
        );
        tEnv.executeSql("USE CATALOG paimon_catalog"); 

        tEnv.executeSql("CREATE TABLE IF NOT EXISTS ods_orders (order_id STRING PRIMARY KEY NOT ENFORCED, product_name STRING, amount DOUBLE, status STRING)");
        tEnv.executeSql("CREATE TABLE IF NOT EXISTS dws_product_sales (product_name STRING PRIMARY KEY NOT ENFORCED, total_amount DOUBLE)");

        StatementSet stmtSet = tEnv.createStatementSet();
        stmtSet.addInsertSql("INSERT INTO ods_orders SELECT order_id, product_name, amount, status FROM default_catalog.default_database.kafka_source");
        stmtSet.addInsertSql("INSERT INTO dws_product_sales SELECT product_name, SUM(amount) as total_amount FROM default_catalog.default_database.kafka_source WHERE status = 'PAID' GROUP BY product_name");
        
        System.out.println("🚀 Flink 引擎启动，开始源源不断向 MinIO Paimon 写入双流数据...");
        stmtSet.execute(); 
    }
}
```
**运行：** 运行 `main` 方法，控制台挂起即代表数据正在成功入湖。

### 轨道 B：Dinky 网页端 GUI 交互
1. 浏览器打开 `http://localhost:8888` (默认账号 admin, 密码 admin)。
2. 【集群中心】 -> 注册集群实例：名称 `LocalFlink`，地址 `jobmanager:8081`。
3. 【数据开发】 -> 新建 Flink SQL，粘贴以下代码并点击运行。*(注意：内网必须用服务名通信)*

```sql
CREATE TEMPORARY TABLE kafka_source (order_id STRING, product_name STRING, amount DOUBLE, status STRING, create_time STRING) WITH ('connector' = 'kafka', 'topic' = 'ecommerce_orders', 'properties.bootstrap.servers' = 'kafka:29092', 'scan.startup.mode' = 'latest-offset', 'format' = 'json');
CREATE CATALOG paimon_catalog WITH ('type' = 'paimon', 'warehouse' = 's3://paimon-data/warehouse', 's3.endpoint' = 'http://minio:9000', 's3.access-key' = 'admin', 's3.secret-key' = 'password123', 's3.path.style.access' = 'true');
USE CATALOG paimon_catalog;
CREATE TABLE IF NOT EXISTS ods_orders (order_id STRING PRIMARY KEY NOT ENFORCED, product_name STRING, amount DOUBLE, status STRING);
CREATE TABLE IF NOT EXISTS dws_product_sales (product_name STRING PRIMARY KEY NOT ENFORCED, total_amount DOUBLE);
EXECUTE STATEMENT SET BEGIN
  INSERT INTO ods_orders SELECT order_id, product_name, amount, status FROM default_catalog.default_database.kafka_source;
  INSERT INTO dws_product_sales SELECT product_name, SUM(amount) as total_amount FROM default_catalog.default_database.kafka_source WHERE status = 'PAID' GROUP BY product_name;
END;
```

---

## 第四阶段：离线计算 (提交到 Spark 分布式集群)

**企业级网络破局：** 我们将 Python 脚本放在项目根目录（已被挂载进了容器），然后通过 `docker exec` 指挥容器内部的 Spark 大管家亲自执行该脚本，完美避开宿主机与内网 Worker 之间的 NAT 隔离墙。

在 `bigdata-lab` 目录下，新建 Python 文件 `spark_offline_analysis.py`：

```python
from pyspark.sql import SparkSession 

print("🚀 正在向集群提交任务，并动态下载依赖包 (首次运行需耐心等待)...")

# ==========================================
# 1. 声明分布式架构与环境初始化
# ==========================================
spark = SparkSession.builder \
    .appName("Paimon_Lakehouse_Offline_Analysis") \
    # 【核心架构】：抛弃 Local 单机模式，将任务指挥权交给 Spark 集群大管家
    .config("spark.master", "spark://spark-master:7077") \
    .config("spark.jars.packages", "org.apache.paimon:paimon-spark-3.3:0.8.0,org.apache.hadoop:hadoop-aws:3.3.2") \
    .config("spark.sql.catalog.paimon", "org.apache.paimon.spark.SparkCatalog") \
    .config("spark.sql.catalog.paimon.warehouse", "s3a://paimon-data/warehouse") \
    # 【网络配置】：代码将在 Docker 内部运行，访问 MinIO 必须写内网服务名
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "admin") \
    .config("spark.hadoop.fs.s3a.secret.key", "password123") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
    .getOrCreate() 

spark.sparkContext.setLogLevel("WARN")

print("\n=======================================================")
print("✅ 任务成功分配给 Worker 节点，开始全集群并行计算...")
print("=======================================================\n")

spark.sql("USE paimon")

# ==========================================
# 2. 执行离线 SQL 分析，产出最终商业报表
# ==========================================

print("📊 [报表 1] : ODS 层 - 最新入库的 5 条原始订单数据 (湖水探测)：")
ods_df = spark.sql("SELECT * FROM default.ods_orders ORDER BY order_id DESC LIMIT 5")
ods_df.show() 

print("📊 [报表 2] : 离线聚合 - 数据湖中各个状态的订单总数对比：")
agg_df = spark.sql("""
    SELECT status, COUNT(*) as order_count 
    FROM default.ods_orders 
    GROUP BY status
""")
agg_df.show()

print("📊 [报表 3] : DWS 层 - Flink 实时计算完毕的各商品已支付总销售额排行榜：")
dws_df = spark.sql("SELECT * FROM default.dws_product_sales ORDER BY total_amount DESC")
dws_df.show()

spark.stop()
```

**见证分布式：** 请在 Mac 本地的终端执行以下命令，直接向 Docker 内部的集群提交该任务：

```bash
docker exec -it bigdata-spark-master /opt/spark/bin/spark-submit /opt/spark-apps/spark_offline_analysis.py
```

*（在执行时，刷新浏览器的 Spark 大屏 `http://localhost:8080`，看到 3 个 Worker 节点正在满载运转，随后完美的离线分析报表将打印在控制台上，标志着全链路实验圆满成功！）*