# 短视频流智能审核发布 Demo

本工程实现一个单机可运行的短视频内容平台流水线：

1. 短视频进入本地媒体区或 Kafka 主题。
2. OpenCV 做关键帧、场景切分、运动峰值采样和音频轨抽取。
3. 可选的多模态 VLM 对关键帧、时间戳、技术指标和 ASR/OCR 上下文做结构化理解。
4. 审核策略根据 VLM 风险、视觉信号和标题风险词给出 `published`、`review`、`rejected`。
5. FastAPI 提供 API 和 Demo 网站，展示视频、标签、摘要、审核理由、模型选择和流处理事件。

## 快速运行

建议使用 Python 3.11 或 3.12。Python 3.14 生态里部分科学计算依赖可能没有稳定 wheel。

```bash
cd "4. 实时短视频流智能审核与发布 综合实验/code/short-video-stream-lab"
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/download_ollama_models.py --model qwen3-vl-4b-ollama
python scripts/verify_demo.py
python -m app.server
```

Windows PowerShell 使用：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts\download_ollama_models.py --model qwen3-vl-4b-ollama
python scripts\verify_demo.py
python -m app.server
```

打开：

```text
http://127.0.0.1:5050
```

默认后台模型是 `Qwen3-VL 4B (Ollama)`。所有主要候选都通过 Ollama 下载到学生本机，Windows、Linux、macOS 使用同一套本地 API。`scripts/verify_demo.py` 会严格检查真实本地 VLM 是否被调用；若只想在课堂上保底演示，也可以在网站后台选择 `local-baseline`。

## 模型候选

后台页面可选择以下候选：

| ID | 模型 | 适用场景 |
| --- | --- | --- |
| `qwen3-vl-4b-ollama` | Qwen3-VL 4B | 16GB 默认工业路线 |
| `qwen3-vl-2b-ollama` | Qwen3-VL 2B | 16GB 低配兜底 |
| `qwen2_5-vl-3b-ollama` | Qwen2.5-VL 3B | 16GB 成熟稳定备选 |
| `gemma3-4b-ollama` | Gemma 3 4B | 16GB 跨平台对照 |
| `qwen3-vl-8b-ollama` | Qwen3-VL 8B | 32GB 增强档 |
| `qwen2_5-vl-7b-ollama` | Qwen2.5-VL 7B | 32GB 稳定增强档 |
| `gemma3-12b-ollama` | Gemma 3 12B | 32GB 多模态对照 |
| `minicpm-v-ollama` | MiniCPM-V | 32GB 短视频对照 |
| `local-baseline` | OpenCV Local Baseline | 无 GPU、无模型服务兜底 |

## 下载本地模型

先安装并启动 Ollama：https://ollama.com/download。Qwen3-VL 需要 Ollama 0.12.7 或更新版本，下载脚本会自动检查版本。

16GB 机器推荐只下载 16GB 档：

```bash
python scripts/download_ollama_models.py --tier 16gb
```

32GB 机器可下载增强档：

```bash
python scripts/download_ollama_models.py --tier 32gb
```

也可以只下载当前默认模型：

```bash
python scripts/download_ollama_models.py --model qwen3-vl-4b-ollama
```

教师机或 32GB 以上机器如果希望一次准备全部候选：

```bash
python scripts/download_ollama_models.py --tier all
```

网站和 Kafka 消费者会通过 `http://127.0.0.1:11434/api/chat` 调用本机 Ollama。

默认配置会给 Qwen3-VL 传 4 张代表性关键帧，并设置 `think: false`、`format: json`。16GB 机器建议保持默认；32GB 机器可以适当提高：

```bash
LOCAL_VLM_MAX_IMAGES=6 LOCAL_VLM_MAX_TOKENS=4500 python -m app.server
```

PowerShell：

```powershell
$env:LOCAL_VLM_MAX_IMAGES="6"
$env:LOCAL_VLM_MAX_TOKENS="4500"
python -m app.server
```

## Kafka 链路

Kafka 启动后，创建主题：

```bash
docker exec -it bigdata-kafka /opt/kafka/bin/kafka-topics.sh \
  --create --if-not-exists \
  --topic short_video_ingest \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1

docker exec -it bigdata-kafka /opt/kafka/bin/kafka-topics.sh \
  --create --if-not-exists \
  --topic short_video_result \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1
```

两个终端分别运行：

```bash
python scripts/kafka_ai_consumer.py
python scripts/kafka_video_producer.py
```
