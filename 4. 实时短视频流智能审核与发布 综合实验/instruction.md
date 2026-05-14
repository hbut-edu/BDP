# 《云计算与大数据处理》实时短视频流智能审核与发布综合实验

## 实验主题

本实验面向一个短视频平台的真实业务链路：短视频进入平台后，系统需要把视频看作一条连续的数据流，对帧进行理解，完成内容审核、自动打标签，并把审核通过的内容发布到一个自建短视频 Demo 网站。

它承接前三章内容：

- 第一章的流批一体数据湖思想：视频原始文件、理解结果、审核日志都要形成可追溯数据资产。
- 第二章的流处理工程挑战：视频帧流天然存在吞吐、延迟、反压、失败恢复、热点内容等问题。
- 第三章的 AI 推荐系统经验：内容标签和理解结果可以继续作为推荐、搜索、画像和召回的上游特征。

本实验默认使用 `FastAPI + OpenCV + Kafka + Ollama 本地多模态模型 + SQLite`。其中 SQLite 是单机教学版的元数据存储，工业环境中可替换为 PostgreSQL、ElasticSearch、ClickHouse、Paimon 或湖仓表；视频文件可替换为 MinIO/S3；理解模型通过 Ollama 下载到学生本机，Windows、Linux、macOS 使用同一套本地 API，后台可在 Qwen、Gemma、MiniCPM 和本地 baseline 之间切换。

---

## 实验目标

完成实验后，同学们应能：

1. 理解短视频内容平台中“上传、流式处理、审核、打标、发布”的端到端数据链路。
2. 使用 OpenCV 对视频做关键帧采样、场景切分、运动峰值识别和音频轨抽取。
3. 将 Qwen3-VL、Qwen2.5-VL、Gemma 3、MiniCPM-V 等 Ollama 多模态模型作为可切换候选，默认使用 16GB 机器可运行的 Qwen3-VL 4B。
4. 设计一个结合 VLM 结构化理解、视觉技术指标和平台规则的审核策略，区分自动发布、人工复核和拒绝发布。
5. 使用 Kafka 将视频进入事件和审核结果解耦，理解消息队列在内容平台中的作用。
6. 使用 FastAPI 构建一个可运行的网站和 API，把审核结果发布到短视频信息流。
7. 形成可观测日志，能够解释每个视频为什么被发布、复核或拒绝。

---

## 课程概览

### 业务流程

```
短视频文件
   ↓
上传/生成/下载样本
   ↓
Kafka: short_video_ingest（可选）
   ↓
OpenCV 关键帧/场景切分/音频预处理
   ↓
后台选择模型：默认 Qwen3-VL 4B，可切换 16GB/32GB 档 Ollama 模型
   ↓
多模态理解：摘要、时间线、实体、动作、字幕、标签、模型风险
   ↓
内容审核：VLM 风险 + 平台规则 + 可解释证据
   ↓
元数据入库 + 媒体文件入媒体区
   ↓
FastAPI Demo 网站展示
   ↓
Kafka: short_video_result（可选）
```

### 工程目录

```text
4. 实时短视频流智能审核与发布 综合实验/
├── instruction.md
└── code/short-video-stream-lab/
    ├── app/
    │   ├── config.py                 # 路径、阈值、实验配置
    │   ├── demo_assets.py            # 生成本地短视频样本
    │   ├── ffmpeg_tools.py           # ffmpeg 元数据/封面辅助能力
    │   ├── model_registry.py         # 模型候选列表与后台选择状态
    │   ├── pipeline.py               # 上传、理解、审核、发布主流程
    │   ├── preprocessing.py          # 关键帧、场景切分、音频预处理
    │   ├── server.py                 # FastAPI 网站和 API
    │   ├── storage.py                # SQLite 元数据和事件日志
    │   ├── understanding_service.py  # 多模态理解编排层
    │   ├── ollama_vlm.py             # Ollama 本地多模态 HTTP 客户端
    │   └── video_understanding.py    # OpenCV 视频理解与审核策略
    ├── scripts/
    │   ├── create_demo_video.py      # 生成测试短视频
    │   ├── download_ollama_models.py # 按 16GB/32GB 档下载本地模型
    │   ├── download_sample_video.py  # 下载互联网 MP4 样本
    │   ├── kafka_ai_consumer.py      # Kafka 消费者：审核处理
    │   ├── kafka_video_producer.py   # Kafka 生产者：发送视频进入事件
    │   ├── run_pipeline_once.py      # 本地单次处理
    │   └── verify_demo.py            # 一键验收脚本
    ├── static/
    │   ├── app.js
    │   └── styles.css
    ├── templates/
    │   └── index.html
    └── requirements.txt
```

---

## 安全注意事项

1. 本实验会处理本地视频文件，同学们不要上传含有个人隐私、真实人脸敏感信息或未经授权传播的视频。
2. 实验审核策略是教学用可解释规则，不代表真实平台审核能力。真实业务应使用多模态审核模型、OCR、ASR、黑产规则、人工复核和申诉链路。
3. `download_sample_video.py` 会从互联网下载 MP4 样本，请确认网络环境允许访问外部资源。默认实验不依赖外网，会自动生成本地测试视频。
4. Kafka 脚本默认连接 `localhost:9092`，请只在本机教学环境运行，不要把未鉴权 Kafka 暴露到公网。
5. Demo 网站只监听 `127.0.0.1:5050`，默认不对外开放。

---

## 环境准备与验证

### 1. 安装系统依赖

本实验用 OpenCV 读取视频，用 ffmpeg 生成样本视频和抽取封面。

macOS 可执行：

```bash
brew install ffmpeg
```

Windows 或 Linux 同学请安装 ffmpeg，并确保命令行能执行：

```bash
ffmpeg -version
ffprobe -version
```

### 2. 创建 Python 虚拟环境

建议使用 Python 3.11 或 3.12。Python 3.14 目前部分科学计算依赖可能需要源码编译，不适合作为课堂默认环境。

进入工程目录：

```bash
cd "4. 实时短视频流智能审核与发布 综合实验/code/short-video-stream-lab"
```

创建并激活虚拟环境：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Windows PowerShell 使用：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

如果 PowerShell 提示脚本执行策略限制，可在当前窗口临时执行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

如果本机没有 `python3.12`，但 `python3 --version` 显示 3.11 或 3.12，也可以使用：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 3. 一键验证

先确认 Ollama 已启动，并至少下载默认模型：

```bash
python scripts/download_ollama_models.py --model qwen3-vl-4b-ollama
```

运行验收脚本：

```bash
python scripts/verify_demo.py
```

期望看到类似输出：

```text
verification passed
{'total': 3, 'published': 1, 'review': 2, 'rejected': 0}
```

这表示系统已经完成三个短视频样本的生成、抽帧理解、本地 Qwen3-VL 调用、审核打标、入库和事件记录。验收脚本会检查 `backend == local_ollama_vlm`，如果模型没有真正运行会失败。

---

## 分阶段实验步骤

## 第一阶段：准备短视频输入流

短视频平台的源头不是一行订单 JSON，而是一个媒体文件以及围绕它产生的一系列事件。为了让实验不依赖外部网络，本工程提供本地生成样本。

运行：

```bash
python scripts/create_demo_video.py
```

系统会生成三个竖屏短视频：

| 文件 | 业务含义 | 预期结果 |
| --- | --- | --- |
| `campus_sports.mp4` | 明亮、户外感、轻运动 | 自动发布 |
| `night_scene_review.mp4` | 低照度，理解置信度下降 | 人工复核 |
| `flashy_clip_review.mp4` | 强亮度跳变和高运动 | 人工复核 |

如果任课教师希望使用互联网样本，可运行：

```bash
python scripts/download_sample_video.py
```

默认下载地址为：

```text
https://filesamples.com/samples/video/mp4/sample_640x360.mp4
```

该脚本只负责下载样本，同学们仍需用后续流水线处理它。

---

## 第二阶段：用 OpenCV 做工业级视频预处理

核心代码在 `app/preprocessing.py` 和 `app/video_understanding.py`。真实短视频平台不会把整段视频每一帧都丢给大模型，这样成本太高、延迟太大。更常见的做法是先用 OpenCV/ffmpeg 做轻量预处理，抽取对理解最有价值的片段：

```python
while True:
    ok, frame = capture.read()
    if not ok:
        break
    diff = cv2.absdiff(gray, previous_gray)
    motion = float(np.mean(diff))
    scene_change = float(np.percentile(diff, 95))
```

本实验会生成三类输入给后续 VLM：

| 输入 | 说明 | 用途 |
| --- | --- | --- |
| 均匀关键帧 | 按时间覆盖整段视频 | 保证模型看到完整故事 |
| 场景切换帧 | 画面发生明显变化的帧 | 捕捉转场和新事件 |
| 运动峰值帧 | 相邻帧变化较大的帧 | 捕捉动作和风险瞬间 |
| 音频轨 | ffmpeg 抽取 16kHz 单声道 wav | 供 ASR/音频模型使用 |
| 视觉技术指标 | 亮度、运动、色彩、闪烁等 | 审核规则和兜底判断 |

本阶段的关键观察点：打开网站后，事件列表中会出现 `frame_sample` 和 `preprocess`。`preprocess` 会记录关键帧数量、音频轨是否存在、视频时长等信息。

---

## 第三阶段：下载并选择本地多模态理解模型

模型候选定义在 `app/model_registry.py`。后台默认模型是 `Qwen3-VL 4B (Ollama)`，这是为了保证 16GB 内存的 Windows、Linux、macOS 电脑都尽量能跑通本地多模态链路。

| ID | 模型 | 适用场景 |
| --- | --- | --- |
| `qwen3-vl-4b-ollama` | Qwen3-VL 4B | 16GB 默认工业路线，综合视频理解、OCR、结构化输出 |
| `qwen3-vl-2b-ollama` | Qwen3-VL 2B | 16GB 低配兜底 |
| `qwen2_5-vl-3b-ollama` | Qwen2.5-VL 3B | 16GB 成熟稳定备选 |
| `gemma3-4b-ollama` | Gemma 3 4B | 16GB 跨平台对照 |
| `qwen3-vl-8b-ollama` | Qwen3-VL 8B | 32GB 增强档 |
| `qwen2_5-vl-7b-ollama` | Qwen2.5-VL 7B | 32GB 稳定增强档 |
| `gemma3-12b-ollama` | Gemma 3 12B | 32GB 多模态对照 |
| `minicpm-v-ollama` | MiniCPM-V | 32GB 短视频理解对照 |
| `local-baseline` | OpenCV Local Baseline | 无 GPU 或无模型服务兜底 |

### 1. 安装 Ollama

Ollama 是本实验推荐的跨平台本地模型运行层：

- Windows：下载安装 https://ollama.com/download/windows，安装后重新打开 PowerShell。
- macOS：下载安装 https://ollama.com/download/mac，并启动 Ollama App。
- Linux：可执行 `curl -fsSL https://ollama.com/install.sh | sh`，然后运行 `ollama serve`。

Qwen3-VL 需要 Ollama 0.12.7 或更新版本，下载脚本会自动检查版本。

确认 Ollama 可用：

```bash
ollama --version
curl http://127.0.0.1:11434/api/version
```

### 2. 按内存档下载模型

16GB 机器建议下载 16GB 档：

```bash
python scripts/download_ollama_models.py --tier 16gb
```

32GB 机器可下载增强档：

```bash
python scripts/download_ollama_models.py --tier 32gb
```

只下载默认模型：

```bash
python scripts/download_ollama_models.py --model qwen3-vl-4b-ollama
```

教师机或 32GB 以上机器如果希望一次准备全部候选：

```bash
python scripts/download_ollama_models.py --tier all
```

如果 Ollama 没有启动或模型没有下载，系统会记录 `local_model_fallback` 事件并回退到本地 OpenCV baseline。这不是为了替代大模型，而是保证课堂环境不因为下载或显卡问题完全无法演示。

本实验默认向 Qwen3-VL 发送 4 张代表性关键帧，并在 Ollama 请求中设置 `think: false` 与 `format: json`。这样既能保留多帧理解能力，又能避免 Qwen3 系列把输出预算耗尽在 thinking 字段中。32GB 机器可以提高关键帧数量：

```bash
LOCAL_VLM_MAX_IMAGES=6 LOCAL_VLM_MAX_TOKENS=4500 python -m app.server
```

Windows PowerShell：

```powershell
$env:LOCAL_VLM_MAX_IMAGES="6"
$env:LOCAL_VLM_MAX_TOKENS="4500"
python -m app.server
```

---

## 第四阶段：视频理解、打标签与摘要生成

多模态理解编排层在 `app/understanding_service.py`。它把关键帧、时间戳、技术指标、音频/OCR 占位信息组织成模型输入，并要求模型返回严格 JSON：

```json
{
  "summary": "一段校园操场运动短视频，画面明亮，人物在跑道上移动。",
  "timeline": [
    {"start": 0, "end": 2, "event": "操场场景建立", "evidence": "绿色场地和跑道线"},
    {"start": 2, "end": 6, "event": "主体持续运动", "evidence": "关键帧中主体位置变化"}
  ],
  "visible_text": [],
  "audio_summary": "",
  "entities": ["操场", "跑道", "运动主体"],
  "actions": ["移动", "运动"],
  "tags": ["校园", "运动", "户外", "竖屏"],
  "risk": {
    "level": "pass",
    "score": 0,
    "categories": [],
    "evidence": []
  }
}
```

本实验保留 `VideoUnderstandingModel` 的本地可解释信号，是因为生产系统也需要低成本兜底特征：当模型超时、模型输出格式错误、显卡资源不足时，平台仍能根据基础风险策略做 fail-closed 处理。

---

## 第五阶段：内容审核策略

审核策略在 `moderate_analysis()` 中。它把理解结果转为平台发布决策：

| 状态 | 含义 |
| --- | --- |
| `published` | 自动发布到信息流 |
| `review` | 进入人工复核队列 |
| `rejected` | 直接拒绝发布 |

示例策略：

```python
if brightness < 25:
    score += 42
    reasons.append({
        "code": "too_dark",
        "level": "review",
        "message": "画面过暗，自动理解置信度下降，需要人工复核。",
        "evidence": brightness,
    })

if metrics["flash_ratio"] >= 0.15:
    score += 38
    reasons.append({
        "code": "flash_risk",
        "level": "review",
        "message": "检测到多次强亮度跳变，可能造成观看不适。",
        "evidence": metrics["flash_ratio"],
    })
```

同学们需要重点理解：审核系统不只输出一个布尔值，还必须输出可解释理由、证据值、模型来源和处理状态。否则平台无法做人工复核、申诉、审计和模型迭代。

---

## 第六阶段：发布到自建短视频 Demo 网站

启动网站：

```bash
python -m app.server
```

浏览器打开：

```text
http://127.0.0.1:5050
```

网站提供：

- 状态统计：全部、已发布、复核、拒绝。
- 模型选择：后台选择 Qwen、MiniCPM、InternVL 或本地 baseline。
- 视频信息流：视频播放器、标签、摘要、风险分、审核理由。
- 上传入口：上传本地 MP4/MOV/WEBM 后自动进入处理链路。
- 流处理事件：实时展示 ingest、frame_sample、understanding、moderation、publish 等事件。

核心 API：

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| `GET` | `/` | Demo 网站 |
| `GET` | `/api/health` | 服务健康状态 |
| `GET` | `/api/videos` | 查看全部视频及统计 |
| `GET` | `/api/videos/{status}` | 按状态查看视频 |
| `GET` | `/api/events` | 查看流处理事件 |
| `GET` | `/api/models` | 查看候选模型和当前模型 |
| `POST` | `/api/models/select` | 切换后台理解模型 |
| `POST` | `/api/demo` | 生成并处理内置样本流 |
| `POST` | `/api/upload` | 上传视频并处理 |
| `POST` | `/api/reset` | 清空演示数据库 |

---

## 第七阶段：接入 Kafka 视频进入事件

前五个阶段可以不依赖 Kafka，适合快速验证网站和审核链路。若要贴近前三章的流处理架构，请启动 Kafka 并运行生产者/消费者脚本。

### 1. 启动 Kafka

在仓库根目录可使用已有 `compose.yaml`：

```bash
docker compose up -d kafka
```

确认 Kafka 容器存在：

```bash
docker ps | grep bigdata-kafka
```

### 2. 创建主题

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

### 3. 启动消费者

终端 A：

```bash
source .venv/bin/activate
python scripts/kafka_ai_consumer.py
```

消费者会监听 `short_video_ingest`，读取视频路径，执行理解、审核、打标，并把结果写入 `short_video_result`。

### 4. 发送视频进入事件

终端 B：

```bash
source .venv/bin/activate
python scripts/kafka_video_producer.py
```

消息示例：

```json
{
  "title": "校园运动短视频",
  "path": "/absolute/path/to/campus_sports.mp4",
  "source": "generated-demo",
  "event_time": 1778718730000
}
```

此时网站仍然可以打开，观察 Kafka 消费者处理后写入的发布结果。

---

## 第八阶段：观察、测试与迭代

### 1. 本地流水线测试

```bash
python scripts/run_pipeline_once.py
```

### 2. 一键验收测试

```bash
python scripts/verify_demo.py
```

验收脚本会检查：

- 是否生成 3 个样本视频。
- 是否至少产生 1 个自动发布视频。
- 是否至少产生 1 个复核视频。
- 每个视频是否都有标签、摘要、帧级指标。
- 每个视频是否真正使用默认 `Qwen3-VL 4B (Ollama)`，而不是悄悄回退到 baseline。
- 事件日志是否记录了主要流水线步骤。

### 3. API 验证

网站启动后执行：

```bash
curl http://127.0.0.1:5050/api/health
curl http://127.0.0.1:5050/api/videos
curl http://127.0.0.1:5050/api/events
```

### 4. 迭代方向

同学们可以选择一个方向继续增强：

- 把 SQLite 换成 PostgreSQL，增加审核任务表。
- 把视频文件上传到 MinIO，并只在数据库中保存对象存储 URL。
- 把帧级指标写入 Paimon，进行离线统计和热榜分析。
- 接入 OCR/ASR，审核画面文字和音频文本。
- 使用真实视觉模型替换规则标签器。
- 将 `review` 状态加入人工审核页面，支持通过/拒绝二次决策。
- 把标签结果接入第三章推荐系统，构建内容推荐流。

---

## 关键代码说明

### 1. 主流水线 `app/pipeline.py`

`ShortVideoPipeline.process_video()` 是端到端主流程：

```python
analysis = self.model.analyze(
    media_path,
    title=title,
    video_id=video_id,
    emit_event=add_event,
    simulate_delay_sec=0.03 if simulate_stream else 0.0,
)

moderation = moderate_analysis(analysis, title)
upsert_video(record)
add_event(video_id, "publish", publish_message, {"status": moderation["status"]})
```

它完成四件事：

1. 将上传文件复制到媒体区。
2. 调用 `MultimodalUnderstandingService` 完成关键帧预处理、模型选择、Ollama 本地多模态模型调用或 OpenCV 兜底。
3. 调用审核策略，将 VLM 风险和平台规则合并。
4. 将最终结果写入 SQLite，并发布到网站 API。

### 2. 多模型理解服务 `app/understanding_service.py`

```python
candidate = get_active_model()
local = self.local_baseline.analyze(...)
preprocess = self.preprocessor.prepare(...)
vlm_payload = self.local_vlm_client.analyze_video(...)
```

这层是实验升级后的核心。它不把模型名称写死在流水线里，而是从 `model_registry.py` 读取当前后台选择；如果 Ollama 未启动或模型未下载，则记录 `local_model_fallback` 并用本地 baseline 保持演示链路可运行。

### 3. 网站服务 `app/server.py`

FastAPI 提供页面、媒体访问和 JSON API：

```python
app = FastAPI(title="Short Video Stream Review Demo")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

@app.post("/api/demo")
def api_demo(background_tasks: BackgroundTasks, overwrite: bool = False):
    started = _start_background_job(background_tasks, _process_demo, overwrite)
    if not started:
        raise HTTPException(status_code=409, detail="pipeline is already running")
    return {"started": True, "processing": True}
```

这里使用后台任务，是为了让网站触发样本流后仍能继续刷新事件列表，观察处理过程。

模型选择 API 也在这一层：

```python
@app.post("/api/models/select")
def api_select_model(selection: ModelSelectionRequest):
    active = set_active_model(selection.model_id)
    return {"active": active.to_dict()}
```

### 4. Kafka 脚本

`scripts/kafka_video_producer.py` 只发送视频进入事件；`scripts/kafka_ai_consumer.py` 才负责真正处理视频。这种拆分体现了消息队列的核心价值：上传侧和 AI 审核侧解耦。

---

## 故障排除 / FAQ

### 1. `ModuleNotFoundError: No module named 'cv2'`

说明没有安装 OpenCV，或没有激活虚拟环境。执行：

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -c "import cv2; print(cv2.__version__)"
```

### 2. Python 3.14 安装 NumPy 很慢

请选择 Python 3.11 或 3.12 创建虚拟环境。原因是 Python 3.14 上某些科学计算包可能暂时没有稳定预编译 wheel。

### 3. `ffmpeg and ffprobe are required`

安装 ffmpeg，并确认命令行可访问：

```bash
ffmpeg -version
ffprobe -version
```

### 4. 端口 `5050` 被占用

修改 `app/server.py` 中的端口：

```python
uvicorn.run("app.server:app", host="127.0.0.1", port=5051, reload=False)
```

### 5. Kafka 连接失败

检查 Kafka 是否启动：

```bash
docker ps | grep bigdata-kafka
```

检查主题是否存在：

```bash
docker exec -it bigdata-kafka /opt/kafka/bin/kafka-topics.sh \
  --list \
  --bootstrap-server localhost:9092
```

### 6. 视频能上传但不能播放

浏览器对编码格式有要求。建议使用 H.264/AAC 或常见 MP4 文件。内置样本由 ffmpeg 生成，默认可以播放。

### 7. 已选择 Qwen 但事件里出现 `local_model_fallback`

这说明后台模型配置已经选择 Qwen，但 Ollama 没有启动、模型没有下载，或模型输出不是严格 JSON。课堂演示时可以临时接受这个回退；如果要完成真实本地模型验收，请确认：

```bash
ollama list
python scripts/download_ollama_models.py --model qwen3-vl-4b-ollama
curl http://127.0.0.1:11434/api/tags
python scripts/verify_demo.py
```

如果 16GB 机器推理太慢，保持默认 `LOCAL_VLM_MAX_IMAGES=4`；如果 32GB 机器希望增强视频理解，可设置 `LOCAL_VLM_MAX_IMAGES=6` 或选择 `qwen3-vl-8b-ollama`。

真实部署中建议将 Ollama 服务、业务 API、Kafka 消费者拆成独立进程，避免模型推理影响网站稳定性。

---

## 参考资源

- FastAPI 官方文档：https://fastapi.tiangolo.com/
- OpenCV Python 文档：https://docs.opencv.org/
- Apache Kafka 文档：https://kafka.apache.org/documentation/
- ffmpeg 文档：https://ffmpeg.org/documentation.html
- Ollama Vision 文档：https://docs.ollama.com/capabilities/vision
- Ollama Qwen3-VL：https://ollama.com/library/qwen3-vl
- Ollama Qwen2.5-VL：https://ollama.com/library/qwen2.5vl
- Ollama Gemma 3：https://ollama.com/library/gemma3
- Ollama MiniCPM-V：https://ollama.com/library/minicpm-v
- 可选 MP4 样本：https://filesamples.com/formats/mp4
