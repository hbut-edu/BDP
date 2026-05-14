const state = {
  filter: "all",
  processing: false,
  models: [],
  activeModel: null,
};

const labels = {
  published: "已发布",
  review: "待复核",
  rejected: "已拒绝",
};

function $(selector) {
  return document.querySelector(selector);
}

function setStatus(message) {
  $("#statusText").textContent = message;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      message = payload.detail || payload.error || message;
    } catch {
      // Keep the default HTTP message.
    }
    throw new Error(message);
  }
  return response.json();
}

function renderStats(stats) {
  $("#totalCount").textContent = stats.total ?? 0;
  $("#publishedCount").textContent = stats.published ?? 0;
  $("#reviewCount").textContent = stats.review ?? 0;
  $("#rejectedCount").textContent = stats.rejected ?? 0;
}

function renderModelSelector(payload) {
  state.models = payload.candidates || [];
  state.activeModel = payload.active || null;
  const select = $("#modelSelect");
  select.innerHTML = state.models
    .map((model) => {
      const selected = model.id === state.activeModel?.id ? " selected" : "";
      return `<option value="${escapeHtml(model.id)}"${selected}>${escapeHtml(model.name)}</option>`;
    })
    .join("");
  renderModelDetails(state.activeModel);
}

function renderModelDetails(model) {
  const target = $("#modelDetails");
  if (!model) {
    target.textContent = "未加载模型配置";
    return;
  }
  const downloadState = model.downloaded ? "已下载到本机" : "未下载到本机";
  target.innerHTML = `
    <strong>${escapeHtml(model.family)}</strong>
    <span>${escapeHtml(model.recommended_for)}</span>
    <small>${escapeHtml(model.hardware)} · ${escapeHtml(model.estimated_memory_gb || "")}</small>
    <small>${escapeHtml(downloadState)} · ${escapeHtml(model.pull_command || "无需下载")} · ${escapeHtml(model.notes)}</small>
  `;
}

async function loadModels() {
  const payload = await requestJson("/api/models");
  renderModelSelector(payload);
}

async function selectModel(event) {
  const modelId = event.target.value;
  setStatus("切换模型中");
  try {
    const payload = await requestJson("/api/models/select", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({model_id: modelId}),
    });
    state.activeModel = payload.active;
    renderModelDetails(payload.active);
    setStatus(`已切换为 ${payload.active.name}`);
  } catch (error) {
    setStatus(error.message);
    await loadModels();
  }
}

function reasonText(video) {
  return (video.reasons || [])
    .map((reason) => reason.message)
    .slice(0, 2)
    .join(" ");
}

function metricText(video) {
  const metrics = video.metrics || {};
  const brightness = metrics.brightness?.avg ?? 0;
  const motion = metrics.motion?.avg ?? 0;
  const duration = metrics.duration_sec ?? 0;
  const model = metrics.model?.selected_name || "未记录模型";
  const backend = metrics.model?.backend || "unknown";
  return `${duration.toFixed(1)}s · 亮度 ${brightness} · 运动 ${motion} · ${model} / ${backend}`;
}

function renderVideos(videos) {
  const grid = $("#videoGrid");
  const filtered =
    state.filter === "all" ? videos : videos.filter((video) => video.status === state.filter);

  if (filtered.length === 0) {
    grid.innerHTML = `<div class="empty">暂无视频</div>`;
    return;
  }

  grid.innerHTML = filtered
    .map((video) => {
      const tags = (video.tags || []).map((tag) => `<span>${escapeHtml(tag)}</span>`).join("");
      const statusLabel = labels[video.status] || video.status;
      const poster = video.thumbnail_file ? ` poster="/media/${encodeURIComponent(video.thumbnail_file)}"` : "";
      return `
        <article class="video-card ${video.status}">
          <video controls preload="metadata"${poster} src="/media/${encodeURIComponent(video.media_file)}"></video>
          <div class="video-body">
            <div class="video-title-row">
              <h2>${escapeHtml(video.title)}</h2>
              <b>${escapeHtml(statusLabel)}</b>
            </div>
            <p class="caption">${escapeHtml(video.caption)}</p>
            <div class="tags">${tags}</div>
            <div class="meta">
              <span>风险 ${escapeHtml(video.risk_score)}</span>
              <span>${escapeHtml(metricText(video))}</span>
            </div>
            <p class="reason">${escapeHtml(reasonText(video))}</p>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderEvents(events) {
  const list = $("#eventList");
  if (!events.length) {
    list.innerHTML = `<li class="empty-event">暂无事件</li>`;
    return;
  }
  list.innerHTML = events
    .slice(0, 40)
    .map(
      (event) => `
        <li>
          <time>${new Date(event.created_at).toLocaleTimeString()}</time>
          <strong>${escapeHtml(event.stage)}</strong>
          <span>${escapeHtml(event.message)}</span>
        </li>
      `,
    )
    .join("");
}

async function refresh() {
  const [health, videoPayload, eventPayload] = await Promise.all([
    requestJson("/api/health"),
    requestJson("/api/videos"),
    requestJson("/api/events"),
  ]);
  state.processing = health.processing;
  state.activeModel = health.active_model || state.activeModel;
  $("#processingBadge").textContent = health.processing ? "running" : "idle";
  $("#processingBadge").classList.toggle("running", health.processing);
  renderStats(videoPayload.stats || {});
  renderVideos(videoPayload.videos || []);
  renderEvents(eventPayload.events || []);
}

async function runDemo() {
  setStatus("样本流处理中");
  try {
    await requestJson("/api/demo", { method: "POST" });
  } catch (error) {
    setStatus(error.message);
  } finally {
    await refresh();
  }
}

async function resetDemo() {
  setStatus("清空中");
  try {
    await requestJson("/api/reset", { method: "POST" });
    setStatus("已清空");
  } catch (error) {
    setStatus(error.message);
  } finally {
    await refresh();
  }
}

async function uploadVideo(event) {
  event.preventDefault();
  const input = $("#videoInput");
  if (!input.files.length) {
    setStatus("请选择视频文件");
    return;
  }
  const form = new FormData();
  form.append("video", input.files[0]);
  form.append("title", $("#titleInput").value || input.files[0].name);
  setStatus("上传处理中");
  try {
    await requestJson("/api/upload", { method: "POST", body: form });
    $("#uploadForm").reset();
  } catch (error) {
    setStatus(error.message);
  } finally {
    await refresh();
  }
}

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    state.filter = button.dataset.filter;
    refresh();
  });
});

$("#runDemo").addEventListener("click", runDemo);
$("#resetDemo").addEventListener("click", resetDemo);
$("#uploadForm").addEventListener("submit", uploadVideo);
$("#modelSelect").addEventListener("change", selectModel);

loadModels();
refresh();
setInterval(refresh, 1800);
