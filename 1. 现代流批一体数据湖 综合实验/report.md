# 现代流批一体数据湖综合实验 实验报告要求

---

## ⚠️ 重要：学号埋点要求

为确保实验报告的原创性，**必须在以下所有命名中嵌入本人学号**（示例：假设学号为 `2021001234`）：

| 命名项 | 原名称 | 学号嵌入后示例 |
|--------|--------|----------------|
| Kafka Topic | `ecommerce_orders` | `ecommerce_orders_2021001234` |
| MinIO Bucket | `paimon-data` | `paimon-data-2021001234` |
| Paimon Catalog | `paimon_catalog` | `paimon_catalog_2021001234` |
| 数据表前缀 | `ods_orders` | `ods_orders_2021001234` |
| 订单 ID 前缀 | `ORD_` | `ORD_2021001234_` |
| Flink 任务名称 | 自定义 | `DualStreamJob_2021001234` |

**验收检查项：**
- [ ] 所有截图中可见的命名均包含学号
- [ ] 文字说明中明确标注了自己的学号
- [ ] 代码片段（如提供）中也体现了学号嵌入

---

## 一、实验环境准备验收

### 1.1 核心依赖准备
- [ ] 确认 `flink-jars` 文件夹存在，且包含以下 3 个核心 Jar 包：
  - `flink-sql-connector-kafka-3.0.1-1.18.jar`
  - `paimon-flink-1.18-0.8.0.jar`
  - `flink-s3-fs-hadoop-1.18.0.jar`

**文字说明要求：**
- 简述这 3 个 Jar 包的作用：
  - Kafka 连接器：用于 Flink 与 Kafka 消息队列的通信
  - Paimon 连接器：实现 Flink 与 Paimon 数据湖格式的集成
  - S3 文件系统：支持 Flink 读写 MinIO 对象存储
- 说明为什么需要将这些 Jar 包挂载到 Docker 容器中

**截图要求：** 展示 `flink-jars` 文件夹内容（截图 1）

---

## 二、集群启动验收

### 2.1 Docker Compose 集群状态
- [ ] 所有容器正常运行，无异常退出
- [ ] Docker 日志中无报错信息

**文字说明要求：**
- 列出所有运行中的容器名称及其作用（kafka、minio、jobmanager、taskmanager、dinky、spark-master、spark-worker）
- 说明 Docker Compose 中自定义网络 `bigdata-network` 的作用
- 简述 KRaft 模式相比传统 Zookeeper 模式的优势

**截图要求：** 执行 `docker ps` 命令，展示所有容器运行状态（截图 2）

### 2.2 Web UI 访问验证
- [ ] Flink Web UI 可正常访问：`http://localhost:8081`
- [ ] MinIO Web Console 可正常访问：`http://localhost:9001`
- [ ] Dinky Web UI 可正常访问：`http://localhost:8888`
- [ ] Spark Master Web UI 可正常访问：`http://localhost:8080`

**文字说明要求：**
- Flink Web UI：说明 JobManager 和 TaskManager 的角色分工
- MinIO Web Console：说明对象存储在数据湖架构中的作用
- Dinky Web UI：简述 Dinky 作为一站式 Flink SQL 开发平台的价值
- Spark Master Web UI：说明独立集群模式下 Master 和 Worker 的关系

**截图要求：** 
- Flink Web UI 首页（截图 3）
- MinIO Web Console 登录后首页（截图 4）
- Dinky Web UI 首页（截图 5）

---

## 三、数据生产验收

### 3.1 Python 数据生产者运行
- [ ] `mock_data_producer.py` 脚本正常运行
- [ ] 控制台持续输出订单数据，无报错

**学号埋点要求：**
- Kafka Topic 名称修改为 `ecommerce_orders_你的学号`
- 订单 ID 格式修改为 `ORD_你的学号_序号`（例如：`ORD_2021001234_1`）

**文字说明要求：**
- 说明 Kafka 生产者的配置参数（bootstrap_servers、value_serializer 等）
- 解释为什么使用 `localhost:9092` 连接 Kafka（外部监听端口）
- 说明订单数据的字段含义（order_id、product_name、amount、status、create_time）
- 简述消息队列在流式数据处理架构中的作用（解耦、缓冲、异步）
- 在说明中标注自己的学号

**截图要求：** Python 生产者控制台输出（截图 6，需清晰显示带学号的 Topic 和订单 ID）

---

## 四、流式入湖验收

### 4.1 Flink 任务运行（任选一种方式）

**方式 A：Java 工程化方式**
- [ ] Flink 应用成功启动并运行
- [ ] Checkpoint 正常触发
- [ ] 无异常报错

**方式 B：Dinky GUI 方式**
- [ ] Dinky 中 Flink SQL 任务成功提交
- [ ] 任务状态为 RUNNING
- [ ] 数据正常处理

**学号埋点要求：**
- Paimon Catalog 名称：`paimon_catalog_你的学号`
- MinIO Bucket：`paimon-data-你的学号`
- 数据表名称：`ods_orders_你的学号`、`dws_product_sales_你的学号`
- Flink 任务名称包含学号

**文字说明要求：**
- 说明 Flink Checkpoint 机制的作用及其在 Paimon 事务写盘中的重要性
- 解释两个数据表的设计目的：
  - `ods_orders_你的学号`：原始订单明细层（ODS 层）
  - `dws_product_sales_你的学号`：产品销售汇总层（DWS 层）
- 说明 Paimon Catalog 的配置参数（warehouse、s3.endpoint、access-key 等）
- 简述流批一体架构的优势（统一存储、统一计算、实时离线一体化）
- 在说明中标注自己的学号

**截图要求：** 
- Flink Web UI 中任务运行详情页（截图 7，需显示带学号的任务名和 Catalog）
- Dinky 任务运行状态页（如使用 Dinky 方式，需显示带学号的 SQL）

### 4.2 数据湖数据验证
- [ ] MinIO 中 `paimon-data-你的学号` bucket 已创建
- [ ] `warehouse` 目录下存在数据表文件
- [ ] 数据持续写入，文件大小不断增长

**文字说明要求：**
- 说明 Paimon 数据湖格式的存储结构（manifest 文件、data 文件、schema 文件等）
- 解释为什么选择对象存储作为数据湖的物理存储底座
- 简述数据湖相比传统数仓的优势（弹性扩展、低成本、支持多格式等）
- 在说明中标注自己的学号

**截图要求：** MinIO 中 Paimon 数据目录结构（截图 8，需清晰显示带学号的 Bucket 名称和表名）

---

## 五、数据查询验收（可选加分项）

### 5.1 Spark 批处理查询
- [ ] 成功通过 Spark 读取 Paimon 表数据
- [ ] 查询结果正确显示

**文字说明要求：**
- 说明 Spark 与 Paimon 集成的配置要点
- 解释流批一体在查询层面的体现（同一套数据既支持实时流处理，也支持离线批处理）
- 简述在实际业务场景中，实时流处理和离线批处理的应用场景差异

**截图要求：** Spark 查询结果（截图 9，可选）

---

## 六、综合验收截图汇总

| 序号 | 截图内容 | 是否必须 |
|------|----------|----------|
| 1 | flink-jars 文件夹内容 | ✅ 必须 |
| 2 | docker ps 容器状态 | ✅ 必须 |
| 3 | Flink Web UI 首页 | ✅ 必须 |
| 4 | MinIO Web Console 首页 | ✅ 必须 |
| 5 | Dinky Web UI 首页 | ✅ 必须 |
| 6 | Python 生产者控制台输出 | ✅ 必须 |
| 7 | Flink 任务运行详情 | ✅ 必须 |
| 8 | MinIO Paimon 数据目录 | ✅ 必须 |
| 9 | Spark 查询结果 | ⭐ 可选 |

**总计：8 张必填截图，1 张可选加分截图**

---

## 验收标准

- **合格：** 完成所有 8 项必填截图，无明显错误
- **良好：** 完成所有必填截图 + 1 项可选截图
- **优秀：** 完成所有截图，且数据处理流畅，无任何报错

---

**注意事项：**
1. 所有截图需清晰可见，关键信息完整
2. 截图需包含时间戳或任务 ID 等唯一标识
3. 如遇报错，需附错误截图及解决说明
4. **⚠️ 学号埋点为硬性要求，未按要求嵌入学号的实验报告将视为抄袭处理**
