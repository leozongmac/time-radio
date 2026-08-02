"use strict";

const currentYear = new Date().getFullYear();
const TTS_SETTINGS_STORAGE_KEY = "time-radio-tts-settings-v1";
const DEEPSEEK_SETTINGS_STORAGE_KEY = "time-radio-deepseek-settings-v1";

const state = {
  year: Math.min(1986, currentYear),
  month: 8,
  minimumYear: 1949,
  maximumYear: currentYear,
  poweredOn: false,
  activeMode: "time",
  ttsEngine: "iflytek",
  deepseekModel: "deepseek-v4-flash",
  whiteNoiseVolume: 18,
  runtimeMode: "web",
  currentAudio: null,
  finishCurrentAudio: null,
  playbackPaused: false,
  activeAbortController: null,
  playbackGeneration: 0,
  broadcastRunning: false,
  newsDigest: null,
};

const elements = {
  systemStatus: document.querySelector("#system-status"),
  systemStatusText: document.querySelector("#system-status-text"),
  yearKnob: document.querySelector("#year-knob"),
  monthKnob: document.querySelector("#month-knob"),
  powerButton: document.querySelector("#power-button"),
  playbackToggle: document.querySelector("#playback-toggle"),
  dateDisplay: document.querySelector("#date-display"),
  displayYear: document.querySelector("#display-year"),
  displayMonth: document.querySelector("#display-month"),
  consoleYear: document.querySelector("#console-year"),
  consoleMonth: document.querySelector("#console-month"),
  broadcastStatus: document.querySelector("#broadcast-status"),
  newsEmpty: document.querySelector("#news-empty"),
  newsList: document.querySelector("#news-list"),
  newsDisclaimer: document.querySelector("#news-disclaimer"),
  stopBroadcast: document.querySelector("#stop-broadcast"),
  settingsDrawer: document.querySelector("#settings-drawer"),
  drawerBackdrop: document.querySelector("#drawer-backdrop"),
  openSettings: document.querySelector("#open-settings"),
  openSettingsFromText: document.querySelector("#open-settings-from-text"),
  closeSettings: document.querySelector("#close-settings"),
  applySettings: document.querySelector("#apply-settings"),
  saveTTSSettings: document.querySelector("#save-tts-settings"),
  clearTTSSettings: document.querySelector("#clear-tts-settings"),
  deepseekKey: document.querySelector("#deepseek-key"),
  deepseekModel: document.querySelector("#deepseek-model"),
  saveDeepSeekKey: document.querySelector("#save-deepseek-key"),
  clearDeepSeekKey: document.querySelector("#clear-deepseek-key"),
  refreshDeepSeekModels: document.querySelector("#refresh-deepseek-models"),
  selectDeepSeekModel: document.querySelector("#select-deepseek-model"),
  deepseekModelNote: document.querySelector("#deepseek-model-note"),
  whiteNoiseAudio: document.querySelector("#white-noise-audio"),
  whiteNoiseVolume: document.querySelector("#white-noise-volume"),
  whiteNoiseVolumeValue: document.querySelector("#white-noise-volume-value"),
  iflytekSettings: document.querySelector("#iflytek-settings"),
  baiduSettings: document.querySelector("#baidu-settings"),
  refreshIflytekVoices: document.querySelector("#refresh-iflytek-voices"),
  refreshBaiduVoices: document.querySelector("#refresh-baidu-voices"),
  iflytekVoiceOptions: document.querySelector("#iflytek-voice-options"),
  iflytekVoiceNote: document.querySelector("#iflytek-voice-note"),
  baiduVoice: document.querySelector("#baidu-voice"),
  baiduVoiceNote: document.querySelector("#baidu-voice-note"),
  activeEngineName: document.querySelector("#active-engine-name"),
  activeVoiceName: document.querySelector("#active-voice-name"),
  ttsText: document.querySelector("#tts-text"),
  textCount: document.querySelector("#text-count"),
  startTextSpeech: document.querySelector("#start-text-speech"),
  stopTextSpeech: document.querySelector("#stop-text-speech"),
  textPlayStatus: document.querySelector("#text-play-status"),
  toastRegion: document.querySelector("#toast-region"),
};

function requiredElement(element, name) {
  if (element === null) {
    throw new Error(`Required UI element is missing: ${name}`);
  }
  return element;
}

Object.entries(elements).forEach(([name, element]) => requiredElement(element, name));

function showToast(message, type) {
  const toast = document.createElement("div");
  toast.className = `toast${type === "error" ? " is-error" : ""}`;
  toast.textContent = message;
  elements.toastRegion.append(toast);
  window.setTimeout(() => toast.remove(), 5600);
}

async function readError(response) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    const payload = await response.json();
    if (payload.error && payload.error.message) {
      return payload.error.message;
    }
    if (payload.detail) {
      return typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
    }
  }
  const text = await response.text();
  return text || `请求失败，HTTP ${response.status}`;
}

function clamp(value, minimum, maximum) {
  return Math.min(Math.max(value, minimum), maximum);
}

function rotationForValue(value, minimum, maximum) {
  const ratio = (value - minimum) / (maximum - minimum);
  return -135 + ratio * 270;
}

function updateKnobVisual(knob, value, minimum, maximum) {
  const face = knob.querySelector(".knob-face");
  face.style.transform = `rotate(${rotationForValue(value, minimum, maximum)}deg)`;
  knob.setAttribute("aria-valuemin", String(minimum));
  knob.setAttribute("aria-valuemax", String(maximum));
  knob.setAttribute("aria-valuenow", String(value));
}

function updateDateUI() {
  const paddedMonth = String(state.month).padStart(2, "0");
  elements.displayYear.textContent = String(state.year);
  elements.displayMonth.textContent = paddedMonth;
  elements.consoleYear.textContent = String(state.year);
  elements.consoleMonth.textContent = paddedMonth;
  updateKnobVisual(elements.yearKnob, state.year, state.minimumYear, state.maximumYear);
  updateKnobVisual(elements.monthKnob, state.month, 1, 12);
}

function setDateValue(kind, value) {
  if (kind === "year") {
    state.year = clamp(Math.round(value), state.minimumYear, state.maximumYear);
  } else {
    state.month = clamp(Math.round(value), 1, 12);
  }
  updateDateUI();
}

function setupKnob(knob, kind, minimumGetter, maximumGetter) {
  let dragStartY = 0;
  let dragStartValue = 0;
  let dragging = false;

  knob.addEventListener("pointerdown", (event) => {
    dragging = true;
    dragStartY = event.clientY;
    dragStartValue = kind === "year" ? state.year : state.month;
    knob.setPointerCapture(event.pointerId);
  });

  knob.addEventListener("pointermove", (event) => {
    if (!dragging) {
      return;
    }
    const sensitivity = kind === "year" ? 0.28 : 0.08;
    const delta = (dragStartY - event.clientY) * sensitivity;
    setDateValue(kind, dragStartValue + delta);
  });

  knob.addEventListener("pointerup", (event) => {
    dragging = false;
    knob.releasePointerCapture(event.pointerId);
  });

  knob.addEventListener(
    "wheel",
    (event) => {
      event.preventDefault();
      const direction = event.deltaY < 0 ? 1 : -1;
      const currentValue = kind === "year" ? state.year : state.month;
      setDateValue(kind, currentValue + direction);
    },
    { passive: false },
  );

  knob.addEventListener("keydown", (event) => {
    const currentValue = kind === "year" ? state.year : state.month;
    if (event.key === "ArrowUp" || event.key === "ArrowRight") {
      event.preventDefault();
      setDateValue(kind, currentValue + 1);
    }
    if (event.key === "ArrowDown" || event.key === "ArrowLeft") {
      event.preventDefault();
      setDateValue(kind, currentValue - 1);
    }
    if (event.key === "Home") {
      event.preventDefault();
      setDateValue(kind, minimumGetter());
    }
    if (event.key === "End") {
      event.preventDefault();
      setDateValue(kind, maximumGetter());
    }
  });
}

function setBroadcastStatus(message, live) {
  elements.broadcastStatus.textContent = message;
  elements.broadcastStatus.parentElement.classList.toggle("is-live", live);
}

function setPower(on) {
  state.poweredOn = on;
  elements.powerButton.classList.toggle("is-on", on);
  elements.powerButton.setAttribute("aria-pressed", String(on));
  elements.dateDisplay.classList.toggle("is-on", on);
  elements.dateDisplay.setAttribute("aria-hidden", String(!on));
  if (on) {
    setBroadcastStatus("已开机，请调整时间后按播放", false);
  } else {
    setBroadcastStatus("已关机", false);
  }
  updatePlaybackControl();
}

function updatePlaybackControl() {
  const hasAudio = state.currentAudio !== null;
  elements.playbackToggle.disabled =
    !state.poweredOn || (state.broadcastRunning && !hasAudio);
  elements.playbackToggle.classList.toggle("is-active", state.poweredOn);
  elements.playbackToggle.classList.toggle("is-playing", hasAudio && !state.playbackPaused);
  elements.playbackToggle.setAttribute(
    "aria-label",
    !hasAudio ? "获取并播放新闻" : state.playbackPaused ? "继续播放" : "暂停播放",
  );
  elements.playbackToggle.querySelector(".playback-icon").textContent =
    hasAudio && !state.playbackPaused ? "Ⅱ" : "▶";
}

async function togglePlaybackPause() {
  const audio = state.currentAudio;
  if (audio === null) {
    throw new Error("当前没有正在播放的语音。");
  }
  if (audio.paused) {
    await audio.play();
    state.playbackPaused = false;
    if (state.activeMode === "time") {
      setBroadcastStatus("继续实时播报", true);
    } else {
      elements.textPlayStatus.textContent = "继续播放";
    }
  } else {
    audio.pause();
    state.playbackPaused = true;
    if (state.activeMode === "time") {
      setBroadcastStatus("播报已暂停", false);
    } else {
      elements.textPlayStatus.textContent = "播放已暂停";
    }
  }
  updatePlaybackControl();
}

function openSettingsDrawer() {
  elements.drawerBackdrop.hidden = false;
  elements.settingsDrawer.classList.add("is-open");
  elements.settingsDrawer.setAttribute("aria-hidden", "false");
  window.setTimeout(() => elements.deepseekKey.focus(), 50);
}

function closeSettingsDrawer() {
  elements.settingsDrawer.classList.remove("is-open");
  elements.settingsDrawer.setAttribute("aria-hidden", "true");
  elements.drawerBackdrop.hidden = true;
}

function selectedEngine() {
  const input = document.querySelector('input[name="tts-engine"]:checked');
  return input ? input.value : "iflytek";
}

function updateProviderPanels() {
  const engine = selectedEngine();
  elements.iflytekSettings.hidden = engine !== "iflytek";
  elements.baiduSettings.hidden = engine !== "baidu";
}

function readIntegerInput(selector) {
  const element = document.querySelector(selector);
  return Number.parseInt(element.value, 10);
}

function updateWhiteNoiseVolume() {
  const volume = Number.parseInt(elements.whiteNoiseVolume.value, 10);
  if (!Number.isInteger(volume) || volume < 0 || volume > 100) {
    throw new Error(`白噪声音量必须是 0 到 100 的整数。当前值：${elements.whiteNoiseVolume.value}`);
  }
  state.whiteNoiseVolume = volume;
  elements.whiteNoiseAudio.volume = volume / 100;
  elements.whiteNoiseVolumeValue.textContent = `${volume}%`;
}

async function startWhiteNoise() {
  updateWhiteNoiseVolume();
  elements.whiteNoiseAudio.currentTime = 0;
  await elements.whiteNoiseAudio.play();
}

function stopWhiteNoise() {
  elements.whiteNoiseAudio.pause();
  elements.whiteNoiseAudio.currentTime = 0;
}

function buildTTSBody(text) {
  const body = {
    engine: state.ttsEngine,
    text,
    iflytek: null,
    baidu: null,
  };

  if (state.ttsEngine === "iflytek") {
    body.iflytek = {
      app_id: document.querySelector("#iflytek-app-id").value,
      api_key: document.querySelector("#iflytek-api-key").value,
      api_secret: document.querySelector("#iflytek-api-secret").value,
      voice: document.querySelector("#iflytek-voice").value.trim(),
      speed: readIntegerInput("#iflytek-speed"),
      pitch: readIntegerInput("#iflytek-pitch"),
      volume: readIntegerInput("#iflytek-volume"),
    };
  }
  if (state.ttsEngine === "baidu") {
    body.baidu = {
      api_key: document.querySelector("#baidu-api-key").value,
      secret_key: document.querySelector("#baidu-secret-key").value,
      voice: readIntegerInput("#baidu-voice"),
      speed: readIntegerInput("#baidu-speed"),
      pitch: readIntegerInput("#baidu-pitch"),
      volume: readIntegerInput("#baidu-volume"),
    };
  }
  return body;
}

function validateTTSConfiguration() {
  const configurationError = getTTSConfigurationError();
  if (configurationError !== null) {
    throw new Error(configurationError);
  }
}

function getTTSConfigurationError() {
  if (state.ttsEngine === "iflytek") {
    const requiredValues = [
      document.querySelector("#iflytek-app-id").value,
      document.querySelector("#iflytek-api-key").value,
      document.querySelector("#iflytek-api-secret").value,
      document.querySelector("#iflytek-voice").value,
    ];
    if (requiredValues.some((value) => !value.trim())) {
      return "讯飞云 TTS 需要填写 AppID、APIKey、APISecret 和发音人参数。";
    }
  }
  if (state.ttsEngine === "baidu") {
    const requiredValues = [
      document.querySelector("#baidu-api-key").value,
      document.querySelector("#baidu-secret-key").value,
    ];
    if (requiredValues.some((value) => !value.trim())) {
      return "百度云 TTS 需要填写 API Key 和 Secret Key。";
    }
  }
  return null;
}

function applySettings() {
  state.ttsEngine = selectedEngine();
  const engineLabels = {
    iflytek: "讯飞云 TTS",
    baidu: "百度云 TTS",
  };
  elements.activeEngineName.textContent = engineLabels[state.ttsEngine];
  elements.activeVoiceName.textContent =
    state.ttsEngine === "iflytek"
      ? document.querySelector("#iflytek-voice").value || "未填写发音人"
      : elements.baiduVoice.selectedOptions[0]?.textContent || "未选择发音人";
  closeSettingsDrawer();
  showToast(`已切换为${engineLabels[state.ttsEngine]}`, "info");
}

function currentTTSSettings() {
  return {
    version: 2,
    engine: selectedEngine(),
    whiteNoiseVolume: state.whiteNoiseVolume,
    iflytek: {
      appId: document.querySelector("#iflytek-app-id").value,
      apiKey: document.querySelector("#iflytek-api-key").value,
      apiSecret: document.querySelector("#iflytek-api-secret").value,
      voice: document.querySelector("#iflytek-voice").value,
      speed: readIntegerInput("#iflytek-speed"),
      pitch: readIntegerInput("#iflytek-pitch"),
      volume: readIntegerInput("#iflytek-volume"),
    },
    baidu: {
      apiKey: document.querySelector("#baidu-api-key").value,
      secretKey: document.querySelector("#baidu-secret-key").value,
      voice: elements.baiduVoice.value,
      speed: readIntegerInput("#baidu-speed"),
      pitch: readIntegerInput("#baidu-pitch"),
      volume: readIntegerInput("#baidu-volume"),
    },
  };
}

function isStoredProviderSettings(value, secretFields) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }
  const stringsAreValid = secretFields.every((field) => typeof value[field] === "string");
  const rangesAreValid = ["speed", "pitch", "volume"].every(
    (field) => Number.isInteger(value[field]),
  );
  return stringsAreValid && rangesAreValid;
}

function isStoredTTSSettings(value) {
  const commonFieldsAreValid =
    value !== null &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    (value.version === 1 || value.version === 2) &&
    (value.engine === "iflytek" || value.engine === "baidu") &&
    isStoredProviderSettings(value.iflytek, ["appId", "apiKey", "apiSecret", "voice"]) &&
    isStoredProviderSettings(value.baidu, ["apiKey", "secretKey", "voice"]);
  if (!commonFieldsAreValid) {
    return false;
  }
  return (
    value.version === 1 ||
    (Number.isInteger(value.whiteNoiseVolume) &&
      value.whiteNoiseVolume >= 0 &&
      value.whiteNoiseVolume <= 100)
  );
}

function normalizeStoredTTSSettings(value) {
  if (!isStoredTTSSettings(value)) {
    return null;
  }
  return {
    ...value,
    version: 2,
    whiteNoiseVolume: value.version === 1 ? 18 : value.whiteNoiseVolume,
  };
}

function setInputValue(selector, value) {
  document.querySelector(selector).value = String(value);
}

function selectBaiduVoice(value) {
  const voiceValue = String(value);
  const optionExists = Array.from(elements.baiduVoice.options).some(
    (option) => option.value === voiceValue,
  );
  if (!optionExists) {
    const option = document.createElement("option");
    option.value = voiceValue;
    option.textContent = `已保存的发音人 · ${voiceValue}`;
    elements.baiduVoice.append(option);
  }
  elements.baiduVoice.value = voiceValue;
}

function applyStoredTTSSettings(settings) {
  document.querySelector(`input[name="tts-engine"][value="${settings.engine}"]`).checked = true;
  setInputValue("#iflytek-app-id", settings.iflytek.appId);
  setInputValue("#iflytek-api-key", settings.iflytek.apiKey);
  setInputValue("#iflytek-api-secret", settings.iflytek.apiSecret);
  setInputValue("#iflytek-voice", settings.iflytek.voice);
  setInputValue("#iflytek-speed", settings.iflytek.speed);
  setInputValue("#iflytek-pitch", settings.iflytek.pitch);
  setInputValue("#iflytek-volume", settings.iflytek.volume);
  setInputValue("#baidu-api-key", settings.baidu.apiKey);
  setInputValue("#baidu-secret-key", settings.baidu.secretKey);
  selectBaiduVoice(settings.baidu.voice);
  setInputValue("#baidu-speed", settings.baidu.speed);
  setInputValue("#baidu-pitch", settings.baidu.pitch);
  setInputValue("#baidu-volume", settings.baidu.volume);
  elements.whiteNoiseVolume.value = String(settings.whiteNoiseVolume);
  updateWhiteNoiseVolume();
  state.ttsEngine = settings.engine;
  updateProviderPanels();
  elements.activeEngineName.textContent =
    settings.engine === "iflytek" ? "讯飞云 TTS" : "百度云 TTS";
  elements.activeVoiceName.textContent =
    settings.engine === "iflytek"
      ? settings.iflytek.voice || "未填写发音人"
      : elements.baiduVoice.selectedOptions[0]?.textContent || "未选择发音人";
}

function saveStoredTTSSettings() {
  const settings = currentTTSSettings();
  window.localStorage.setItem(TTS_SETTINGS_STORAGE_KEY, JSON.stringify(settings));
  showToast("TTS 凭证和声音设置已保存在当前浏览器。", "info");
}

function loadStoredTTSSettings() {
  const storedValue = window.localStorage.getItem(TTS_SETTINGS_STORAGE_KEY);
  if (storedValue === null) {
    return;
  }
  const settings = normalizeStoredTTSSettings(JSON.parse(storedValue));
  if (settings === null) {
    throw new Error(
      `浏览器中的 TTS 设置格式无效。请点击“清空 TTS 凭证”后重新填写。存储键：${TTS_SETTINGS_STORAGE_KEY}`,
    );
  }
  applyStoredTTSSettings(settings);
}

function clearStoredTTSSettings() {
  window.localStorage.removeItem(TTS_SETTINGS_STORAGE_KEY);
  [
    "#iflytek-app-id",
    "#iflytek-api-key",
    "#iflytek-api-secret",
    "#baidu-api-key",
    "#baidu-secret-key",
  ].forEach((selector) => setInputValue(selector, ""));
  showToast("浏览器中保存的 TTS 凭证已清空。", "info");
}

function validateVoiceCatalog(payload, provider) {
  const payloadIsObject =
    payload !== null && typeof payload === "object" && !Array.isArray(payload);
  const voicesAreValid =
    payloadIsObject &&
    Array.isArray(payload.voices) &&
    payload.voices.every(
      (voice) =>
        voice !== null &&
        typeof voice === "object" &&
        typeof voice.id === "string" &&
        typeof voice.name === "string" &&
        typeof voice.category === "string" &&
        typeof voice.requires_authorization === "boolean",
    );
  if (
    !payloadIsObject ||
    payload.provider !== provider ||
    typeof payload.source_note !== "string" ||
    !voicesAreValid
  ) {
    throw new Error(`服务器返回了无效的 ${provider} 声音目录。`);
  }
  return payload;
}

function voiceOptionLabel(voice) {
  const authorizationLabel = voice.requires_authorization ? " · 需授权" : "";
  return `${voice.name} · ${voice.category} · ${voice.id}${authorizationLabel}`;
}

function populateVoiceCatalog(provider, catalog) {
  if (provider === "iflytek") {
    elements.iflytekVoiceOptions.replaceChildren(
      ...catalog.voices.map((voice) => {
        const option = document.createElement("option");
        option.value = voice.id;
        option.label = voiceOptionLabel(voice);
        return option;
      }),
    );
    elements.iflytekVoiceNote.textContent = catalog.source_note;
    return;
  }

  const selectedVoice = elements.baiduVoice.value;
  elements.baiduVoice.replaceChildren(
    ...catalog.voices.map((voice) => {
      const option = document.createElement("option");
      option.value = voice.id;
      option.textContent = voiceOptionLabel(voice);
      return option;
    }),
  );
  const selectedVoiceExists = catalog.voices.some((voice) => voice.id === selectedVoice);
  elements.baiduVoice.value = selectedVoiceExists ? selectedVoice : catalog.voices[0]?.id || "";
  elements.baiduVoiceNote.textContent = catalog.source_note;
}

async function refreshVoiceCatalog(provider, button) {
  button.disabled = true;
  try {
    const response = await fetch(`/api/tts/voices?provider=${encodeURIComponent(provider)}`);
    if (!response.ok) {
      throw new Error(await readError(response));
    }
    const catalog = validateVoiceCatalog(await response.json(), provider);
    populateVoiceCatalog(provider, catalog);
    showToast(`已刷新 ${catalog.voices.length} 个声音选项。`, "info");
  } finally {
    button.disabled = false;
  }
}

function ensureDeepSeekModelOption(model) {
  const exists = Array.from(elements.deepseekModel.options).some(
    (option) => option.value === model,
  );
  if (!exists) {
    const option = document.createElement("option");
    option.value = model;
    option.textContent = model;
    elements.deepseekModel.append(option);
  }
  elements.deepseekModel.value = model;
}

function selectCurrentDeepSeekModel() {
  const model = elements.deepseekModel.value.trim();
  if (!model) {
    throw new Error("请先刷新并选择一个 DeepSeek 模型。");
  }
  state.deepseekModel = model;
  elements.deepseekModelNote.textContent = `当前使用：${model}`;
  showToast(`已选择 DeepSeek 模型：${model}`, "info");
}

function currentDeepSeekSettings() {
  return {
    version: 1,
    apiKey: elements.deepseekKey.value.trim(),
    model: state.deepseekModel,
  };
}

function isStoredDeepSeekSettings(value) {
  return (
    value !== null &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    value.version === 1 &&
    typeof value.apiKey === "string" &&
    typeof value.model === "string" &&
    value.model.length > 0
  );
}

function saveStoredDeepSeekSettings() {
  const settings = currentDeepSeekSettings();
  if (!settings.apiKey) {
    throw new Error("DeepSeek API Key 不能为空。");
  }
  window.localStorage.setItem(DEEPSEEK_SETTINGS_STORAGE_KEY, JSON.stringify(settings));
  showToast("DeepSeek API Key 和所选模型已保存在当前浏览器。", "info");
}

function loadStoredDeepSeekSettings() {
  const storedValue = window.localStorage.getItem(DEEPSEEK_SETTINGS_STORAGE_KEY);
  if (storedValue === null) {
    return;
  }
  const settings = JSON.parse(storedValue);
  if (!isStoredDeepSeekSettings(settings)) {
    throw new Error(
      `浏览器中的 DeepSeek 设置格式无效。请清空后重新填写。存储键：${DEEPSEEK_SETTINGS_STORAGE_KEY}`,
    );
  }
  elements.deepseekKey.value = settings.apiKey;
  ensureDeepSeekModelOption(settings.model);
  state.deepseekModel = settings.model;
  elements.deepseekModelNote.textContent = `当前使用：${settings.model}`;
}

function clearStoredDeepSeekSettings() {
  window.localStorage.removeItem(DEEPSEEK_SETTINGS_STORAGE_KEY);
  elements.deepseekKey.value = "";
  showToast("浏览器中保存的 DeepSeek API Key 已清空。", "info");
}

function validateDeepSeekModelsResponse(payload) {
  const valid =
    payload !== null &&
    typeof payload === "object" &&
    !Array.isArray(payload) &&
    Array.isArray(payload.models) &&
    payload.models.length > 0 &&
    payload.models.every((model) => typeof model === "string" && model.length > 0);
  if (!valid) {
    throw new Error("服务器返回了无效的 DeepSeek 模型列表。");
  }
  return payload.models;
}

async function refreshDeepSeekModelList() {
  const apiKey = elements.deepseekKey.value.trim();
  if (!apiKey) {
    throw new Error("请先填写 DeepSeek API Key，再刷新模型。");
  }
  elements.refreshDeepSeekModels.disabled = true;
  try {
    const response = await fetch("/api/deepseek/models", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ deepseek_api_key: apiKey }),
    });
    if (!response.ok) {
      throw new Error(await readError(response));
    }
    const models = validateDeepSeekModelsResponse(await response.json());
    const selectedModel = state.deepseekModel;
    elements.deepseekModel.replaceChildren(
      ...models.map((model) => {
        const option = document.createElement("option");
        option.value = model;
        option.textContent = model;
        return option;
      }),
    );
    elements.deepseekModel.value = models.includes(selectedModel) ? selectedModel : models[0];
    showToast(`已刷新 ${models.length} 个 DeepSeek 模型，请确认选择。`, "info");
  } finally {
    elements.refreshDeepSeekModels.disabled = false;
  }
}

function buildNewsRequestBody() {
  const apiKey = elements.deepseekKey.value.trim();
  if (!apiKey) {
    openSettingsDrawer();
    throw new Error("请先在播音设置中填写 DeepSeek API Key。");
  }
  return {
    year: state.year,
    month: state.month,
    deepseek_api_key: apiKey,
    model: state.deepseekModel,
  };
}

async function streamNews(onEvent, signal) {
  const response = await fetch("/api/news/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildNewsRequestBody()),
    signal,
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  if (response.body === null) {
    throw new Error("浏览器没有收到 DeepSeek 流式响应。");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    while (buffer.includes("\n")) {
      const newlineIndex = buffer.indexOf("\n");
      const line = buffer.slice(0, newlineIndex).trim();
      buffer = buffer.slice(newlineIndex + 1);
      if (line) {
        onEvent(JSON.parse(line));
      }
    }
    if (done) {
      break;
    }
  }
  if (buffer.trim()) {
    onEvent(JSON.parse(buffer));
  }
}

function resetNewsDisplay() {
  elements.newsEmpty.hidden = true;
  elements.newsList.innerHTML = "";
  elements.newsDisclaimer.textContent = "";
}

function appendNewsItem(item, index) {
  const listItem = document.createElement("li");
  listItem.className = "news-item is-arriving";
  listItem.dataset.newsIndex = String(index);

  const meta = document.createElement("div");
  meta.className = "news-meta";
  const region = document.createElement("span");
  region.textContent = item.region;
  const date = document.createElement("span");
  date.textContent = item.date_label;
  meta.append(region, date);

  const title = document.createElement("h3");
  title.textContent = item.title;
  const summary = document.createElement("p");
  summary.textContent = item.summary;
  listItem.append(meta, title, summary);
  elements.newsList.append(listItem);
  window.requestAnimationFrame(() => listItem.classList.remove("is-arriving"));
}

function splitSpeechText(text) {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (!normalized) {
    return [];
  }
  const sentences = normalized.match(/[^。！？!?；;]+[。！？!?；;]?/g) || [normalized];
  const chunks = [];
  let current = "";
  sentences.forEach((sentence) => {
    if ((current + sentence).length <= 260) {
      current += sentence;
      return;
    }
    if (current) {
      chunks.push(current);
    }
    if (sentence.length <= 260) {
      current = sentence;
      return;
    }
    for (let index = 0; index < sentence.length; index += 260) {
      chunks.push(sentence.slice(index, index + 260));
    }
    current = "";
  });
  if (current) {
    chunks.push(current);
  }
  return chunks;
}

function enqueueSpeechText(queue, text, newsIndex) {
  const segments = splitSpeechText(text);
  segments.forEach((segment) => {
    enqueue(queue, { text: segment, newsIndex });
  });
}

function createAsyncQueue() {
  return {
    values: [],
    waiters: [],
    closed: false,
    error: null,
  };
}

function enqueue(queue, value) {
  if (queue.closed) {
    throw new Error("Cannot enqueue into a closed speech queue.");
  }
  const waiter = queue.waiters.shift();
  if (waiter) {
    waiter.resolve(value);
    return;
  }
  queue.values.push(value);
}

function closeQueue(queue, error) {
  if (queue.closed) {
    return;
  }
  queue.closed = true;
  queue.error = error;
  queue.waiters.splice(0).forEach((waiter) => {
    if (error) {
      waiter.reject(error);
    } else {
      waiter.resolve(null);
    }
  });
}

function nextQueueValue(queue) {
  const value = queue.values.shift();
  if (value !== undefined) {
    return Promise.resolve(value);
  }
  if (queue.closed) {
    return queue.error ? Promise.reject(queue.error) : Promise.resolve(null);
  }
  return new Promise((resolve, reject) => {
    queue.waiters.push({ resolve, reject });
  });
}

async function synthesizeSegment(text, signal) {
  const response = await fetch("/api/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildTTSBody(text)),
    signal,
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return response.blob();
}

function playBlob(blob, generation) {
  return new Promise((resolve, reject) => {
    if (generation !== state.playbackGeneration) {
      resolve();
      return;
    }
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    let settled = false;
    state.currentAudio = audio;
    state.playbackPaused = false;
    updatePlaybackControl();

    const finish = (error) => {
      if (settled) {
        return;
      }
      settled = true;
      URL.revokeObjectURL(url);
      if (state.currentAudio === audio) {
        state.currentAudio = null;
        state.finishCurrentAudio = null;
        state.playbackPaused = false;
        updatePlaybackControl();
      }
      if (error === null) {
        resolve();
      } else {
        reject(error);
      }
    };
    state.finishCurrentAudio = finish;
    audio.addEventListener("ended", () => finish(null));
    audio.addEventListener("error", () => {
      finish(new Error("浏览器无法播放生成的音频。"));
    });
    audio.play().catch((error) => {
      finish(new Error(`浏览器拒绝播放音频：${error.message}`));
    });
  });
}

async function synthesizeSpeechQueue(textQueue, audioQueue, controller, generation) {
  try {
    while (generation === state.playbackGeneration) {
      const segment = await nextQueueValue(textQueue);
      if (segment === null) {
        break;
      }
      const blob = await synthesizeSegment(segment.text, controller.signal);
      enqueue(audioQueue, { ...segment, blob });
    }
    closeQueue(audioQueue, null);
  } catch (error) {
    closeQueue(audioQueue, error);
    throw error;
  }
}

function markPlayingNewsItem(index) {
  document.querySelectorAll(".news-item.is-playing").forEach((item) => {
    item.classList.remove("is-playing");
  });
  if (index === null) {
    return;
  }
  const activeItem = document.querySelector(`[data-news-index="${index}"]`);
  activeItem?.classList.add("is-playing");
  activeItem?.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

async function playSpeechQueue(audioQueue, generation) {
  let playedCount = 0;
  while (generation === state.playbackGeneration) {
    const segment = await nextQueueValue(audioQueue);
    if (segment === null) {
      break;
    }
    playedCount += 1;
    markPlayingNewsItem(segment.newsIndex);
    setBroadcastStatus(`实时播报第 ${playedCount} 段`, true);
    await playBlob(segment.blob, generation);
  }
  markPlayingNewsItem(null);
}

function stopPlayback() {
  state.playbackGeneration += 1;
  if (state.activeAbortController) {
    state.activeAbortController.abort();
    state.activeAbortController = null;
  }
  if (state.currentAudio) {
    state.currentAudio.pause();
    state.currentAudio.currentTime = 0;
  }
  if (state.finishCurrentAudio) {
    state.finishCurrentAudio(null);
  } else {
    state.currentAudio = null;
    state.playbackPaused = false;
    updatePlaybackControl();
  }
  document.querySelectorAll(".news-item.is-playing").forEach((item) => {
    item.classList.remove("is-playing");
  });
}

async function playSegments(segments, onSegmentStart, onStatus) {
  validateTTSConfiguration();
  stopPlayback();
  const generation = state.playbackGeneration;
  const controller = new AbortController();
  state.activeAbortController = controller;

  let nextAudio = synthesizeSegment(segments[0], controller.signal);
  for (let index = 0; index < segments.length; index += 1) {
    onSegmentStart(index, segments.length);
    const audioBlob = await nextAudio;
    if (generation !== state.playbackGeneration) {
      return;
    }
    if (index + 1 < segments.length) {
      nextAudio = synthesizeSegment(segments[index + 1], controller.signal);
    }
    onStatus(`正在播放第 ${index + 1} / ${segments.length} 段`);
    await playBlob(audioBlob, generation);
  }
  state.activeAbortController = null;
}

function initializeNewsSession() {
  state.newsDigest = {
    year: state.year,
    month: state.month,
    broadcast_intro: "",
    items: [],
    disclaimer: "",
  };
  setBroadcastStatus("正在连接 DeepSeek 流式新闻", true);
  resetNewsDisplay();
  elements.newsEmpty.hidden = false;
  elements.newsEmpty.querySelector("p").textContent =
    "DeepSeek 正在流式整理新闻，第一条返回后会立即显示……";
  elements.stopBroadcast.disabled = false;
}

function handleNewsStreamEvent(event, onSpeechText) {
  if (event.type === "error") {
    throw new Error(event.error.message);
  }
  if (event.type === "intro") {
    state.newsDigest.broadcast_intro = event.text;
    elements.newsEmpty.querySelector("p").textContent = "开场白已返回，正在接收新闻……";
    onSpeechText(event.text, null);
    return;
  }
  if (event.type === "item") {
    const newsIndex = state.newsDigest.items.length;
    state.newsDigest.items.push(event.item);
    elements.newsEmpty.hidden = true;
    appendNewsItem(event.item, newsIndex);
    onSpeechText(`${event.item.title}。${event.item.summary}`, newsIndex);
    if (!state.playbackPaused) {
      setBroadcastStatus(`已接收第 ${newsIndex + 1} 条新闻，持续生成中`, true);
    }
    return;
  }
  if (event.type === "disclaimer") {
    state.newsDigest.disclaimer = event.text;
    elements.newsDisclaimer.textContent = event.text;
    onSpeechText(event.text, null);
    return;
  }
  if (event.type === "complete") {
    setBroadcastStatus("新闻生成完成", false);
    return;
  }
  throw new Error(`收到未知的新闻流事件：${event.type}`);
}

async function loadNewsWithoutSpeech() {
  stopPlayback();
  const controller = new AbortController();
  state.activeAbortController = controller;
  initializeNewsSession();
  try {
    await streamNews(
      (event) => handleNewsStreamEvent(event, () => {}),
      controller.signal,
    );
    setBroadcastStatus("新闻获取完成；未配置语音播报", false);
  } finally {
    if (state.activeAbortController === controller) {
      state.activeAbortController = null;
    }
  }
}

async function loadNewsWithSpeech() {
  validateTTSConfiguration();
  stopPlayback();
  const generation = state.playbackGeneration;
  const controller = new AbortController();
  state.activeAbortController = controller;
  const textQueue = createAsyncQueue();
  const audioQueue = createAsyncQueue();
  const synthesisTask = synthesizeSpeechQueue(textQueue, audioQueue, controller, generation);
  const playbackTask = playSpeechQueue(audioQueue, generation);
  const speechTask = Promise.allSettled([synthesisTask, playbackTask]);
  initializeNewsSession();
  try {
    await streamNews(
      (event) =>
        handleNewsStreamEvent(event, (text, newsIndex) => {
          enqueueSpeechText(textQueue, text, newsIndex);
        }),
      controller.signal,
    );
    closeQueue(textQueue, null);
    const speechResults = await speechTask;
    const speechFailure = speechResults.find((result) => result.status === "rejected");
    if (speechFailure) {
      setBroadcastStatus("新闻已返回；语音合成失败", false);
      showToast(`新闻已正常显示，但语音播报失败：${speechFailure.reason.message}`, "error");
    } else {
      setBroadcastStatus("本期新闻与播报结束", false);
    }
  } catch (error) {
    closeQueue(textQueue, error);
    controller.abort();
    await speechTask;
    throw error;
  } finally {
    if (state.activeAbortController === controller) {
      state.activeAbortController = null;
    }
  }
}

async function handlePlaybackButton() {
  if (!state.poweredOn) {
    showToast("请先按开机按钮，再调整时间并播放。", "info");
    return;
  }
  if (state.currentAudio !== null) {
    await togglePlaybackPause();
    return;
  }
  if (state.broadcastRunning) {
    showToast("新闻正在获取或等待语音生成，请稍候。", "info");
    return;
  }
  state.broadcastRunning = true;
  updatePlaybackControl();
  try {
    const ttsError = getTTSConfigurationError();
    if (ttsError === null) {
      await loadNewsWithSpeech();
    } else {
      showToast(`${ttsError} 新闻仍会正常获取，但本次不播报语音。`, "info");
      await loadNewsWithoutSpeech();
    }
  } catch (error) {
    if (error.name !== "AbortError") {
      elements.newsEmpty.hidden = state.newsDigest?.items.length > 0;
      if (!elements.newsEmpty.hidden) {
        elements.newsEmpty.querySelector("p").textContent =
          "未能接收到历史新闻，请检查 DeepSeek 设置后重试。";
      }
      showToast(error.message, "error");
    }
  } finally {
    state.broadcastRunning = false;
    elements.stopBroadcast.disabled = true;
    updatePlaybackControl();
  }
}

async function handlePowerButton() {
  if (state.poweredOn) {
    stopPlayback();
    stopWhiteNoise();
    setPower(false);
    return;
  }
  setPower(true);
  try {
    await startWhiteNoise();
  } catch (error) {
    setPower(false);
    throw new Error(`白噪声无法播放：${error.message}`);
  }
}

async function startTextSpeech() {
  const segments = splitSpeechText(elements.ttsText.value);
  if (!segments.length) {
    showToast("请先输入需要播报的文字。", "error");
    return;
  }
  elements.startTextSpeech.disabled = true;
  elements.stopTextSpeech.disabled = false;
  try {
    await playSegments(
      segments,
      () => {},
      (message) => {
        elements.textPlayStatus.textContent = message;
      },
    );
    elements.textPlayStatus.textContent = "文字播报完成";
  } catch (error) {
    if (error.name !== "AbortError") {
      elements.textPlayStatus.textContent = "文字播报失败";
      showToast(error.message, "error");
    }
  } finally {
    elements.startTextSpeech.disabled = false;
    elements.stopTextSpeech.disabled = true;
  }
}

function stopTextSpeech() {
  stopPlayback();
  elements.textPlayStatus.textContent = "已停止";
}

function switchMode(mode) {
  state.activeMode = mode;
  document.querySelectorAll(".mode-button").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.mode === mode);
  });
  document.querySelectorAll(".mode-view").forEach((view) => {
    view.classList.toggle("is-active", view.dataset.view === mode);
  });
}

async function loadHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) {
      throw new Error(await readError(response));
    }
    const health = await response.json();
    state.minimumYear = health.minimum_year;
    state.maximumYear = health.maximum_year;
    state.runtimeMode = health.runtime_mode;
    elements.systemStatus.classList.add("is-ready");
    elements.systemStatusText.textContent = "云端 Web 服务已连接";
    elements.yearKnob.setAttribute("aria-valuemin", String(state.minimumYear));
    elements.yearKnob.setAttribute("aria-valuemax", String(state.maximumYear));
    updateDateUI();
  } catch (error) {
    elements.systemStatusText.textContent = "服务检查失败";
    showToast(error.message, "error");
  }
}

setupKnob(
  elements.yearKnob,
  "year",
  () => state.minimumYear,
  () => state.maximumYear,
);
setupKnob(elements.monthKnob, "month", () => 1, () => 12);

elements.powerButton.addEventListener("click", () => {
  handlePowerButton().catch((error) => showToast(error.message, "error"));
});
elements.playbackToggle.addEventListener("click", () => {
  handlePlaybackButton().catch((error) => showToast(error.message, "error"));
});
elements.stopBroadcast.addEventListener("click", () => {
  stopPlayback();
  elements.stopBroadcast.disabled = true;
  setBroadcastStatus("播报已停止", false);
});
elements.openSettings.addEventListener("click", openSettingsDrawer);
elements.openSettingsFromText.addEventListener("click", openSettingsDrawer);
elements.closeSettings.addEventListener("click", closeSettingsDrawer);
elements.drawerBackdrop.addEventListener("click", closeSettingsDrawer);
elements.applySettings.addEventListener("click", applySettings);
elements.saveDeepSeekKey.addEventListener("click", () => {
  try {
    saveStoredDeepSeekSettings();
  } catch (error) {
    showToast(`无法保存 DeepSeek API Key：${error.message}`, "error");
  }
});
elements.clearDeepSeekKey.addEventListener("click", () => {
  try {
    clearStoredDeepSeekSettings();
  } catch (error) {
    showToast(`无法清空 DeepSeek API Key：${error.message}`, "error");
  }
});
elements.refreshDeepSeekModels.addEventListener("click", () => {
  refreshDeepSeekModelList().catch((error) => {
    showToast(`DeepSeek 模型刷新失败：${error.message}`, "error");
  });
});
elements.selectDeepSeekModel.addEventListener("click", () => {
  try {
    selectCurrentDeepSeekModel();
  } catch (error) {
    showToast(error.message, "error");
  }
});
elements.saveTTSSettings.addEventListener("click", () => {
  try {
    saveStoredTTSSettings();
  } catch (error) {
    showToast(`无法保存 TTS 凭证：${error.message}`, "error");
  }
});
elements.clearTTSSettings.addEventListener("click", () => {
  try {
    clearStoredTTSSettings();
  } catch (error) {
    showToast(`无法清空 TTS 凭证：${error.message}`, "error");
  }
});
elements.whiteNoiseVolume.addEventListener("input", () => {
  try {
    updateWhiteNoiseVolume();
  } catch (error) {
    showToast(error.message, "error");
  }
});
elements.refreshIflytekVoices.addEventListener("click", () => {
  refreshVoiceCatalog("iflytek", elements.refreshIflytekVoices).catch((error) => {
    showToast(`讯飞声音刷新失败：${error.message}`, "error");
  });
});
elements.refreshBaiduVoices.addEventListener("click", () => {
  refreshVoiceCatalog("baidu", elements.refreshBaiduVoices).catch((error) => {
    showToast(`百度声音刷新失败：${error.message}`, "error");
  });
});
document.querySelectorAll('input[name="tts-engine"]').forEach((input) => {
  input.addEventListener("change", updateProviderPanels);
});
elements.ttsText.addEventListener("input", () => {
  elements.textCount.textContent = `${elements.ttsText.value.length} / 4000`;
});
elements.startTextSpeech.addEventListener("click", startTextSpeech);
elements.stopTextSpeech.addEventListener("click", stopTextSpeech);
document.querySelectorAll(".mode-button").forEach((button) => {
  button.addEventListener("click", () => switchMode(button.dataset.mode));
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && elements.settingsDrawer.classList.contains("is-open")) {
    closeSettingsDrawer();
  }
});

updateDateUI();
updateProviderPanels();
updatePlaybackControl();
updateWhiteNoiseVolume();
try {
  loadStoredTTSSettings();
} catch (error) {
  showToast(error.message, "error");
}
try {
  loadStoredDeepSeekSettings();
} catch (error) {
  showToast(error.message, "error");
}
loadHealth();
