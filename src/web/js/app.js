/**
 * Frontend application logic for OCR Alliance.
 */

const state = {
    inputDir: '',
    outputDir: '',
    tasks: [],
    selectedPath: null,
    statusTimer: null,
    modelStatusTimer: null,
    modelsReady: false,
    autoDownload: true,
};

const els = {
    tree: document.getElementById('tree'),
    dirCount: document.getElementById('dir-count'),
    imagePreview: document.getElementById('image-preview'),
    resultRapidocr: document.getElementById('result-rapidocr'),
    resultHunyuan: document.getElementById('result-hunyuan'),
    resultGlm: document.getElementById('result-glm'),
    resultUnified: document.getElementById('result-unified'),
    statusText: document.getElementById('status-text'),
    progressText: document.querySelector('.progress-text'),
    progressFill: document.getElementById('progress-fill'),
    btnScan: document.getElementById('btn-scan'),
    btnStart: document.getElementById('btn-start'),
    btnStop: document.getElementById('btn-stop'),
    btnSettings: document.getElementById('btn-settings'),
    platformInfo: document.getElementById('platform-info'),
    setupModal: document.getElementById('setup-modal'),
    setupModelList: document.getElementById('setup-model-list'),
    btnStartDownload: document.getElementById('btn-start-download'),
    btnSkipDownload: document.getElementById('btn-skip-download'),
    settingsModal: document.getElementById('settings-modal'),
    settingsBaseUrl: document.getElementById('settings-base-url'),
    settingsModel: document.getElementById('settings-model'),
    settingsApiKey: document.getElementById('settings-api-key'),
    settingsTemperature: document.getElementById('settings-temperature'),
    settingsMaxTokens: document.getElementById('settings-max-tokens'),
    settingsMessage: document.getElementById('settings-message'),
    btnTestLLM: document.getElementById('btn-test-llm'),
    btnSaveSettings: document.getElementById('btn-save-settings'),
    btnCancelSettings: document.getElementById('btn-cancel-settings'),
};

async function init() {
    let settings = {};
    try {
        settings = await api.settings();
        state.autoDownload = settings.auto_download_models !== false;
    } catch (e) {
        console.warn('Failed to load settings', e);
    }

    try {
        const status = await api.modelStatus();
        if (!status.all_ready) {
            showSetupModal(status.models);
            if (state.autoDownload) {
                await startModelDownloads();
            }
            return;
        }
    } catch (e) {
        console.warn('Failed to check model status', e);
    }

    finishInit(settings);
}

function finishInit(settings) {
    state.modelsReady = true;
    if (els.setupModal) {
        els.setupModal.style.display = 'none';
    }

    console.log('Settings:', settings);

    if (window.pywebview && window.pywebview.api) {
        try {
            window.pywebview.api.get_platform().then(platform => {
                els.platformInfo.textContent = platform;
            });
        } catch (e) {
            console.warn('Failed to get platform', e);
        }
    }

    els.btnScan.addEventListener('click', onScan);
    els.btnStart.addEventListener('click', onStart);
    els.btnStop.addEventListener('click', onStop);
    els.btnSettings.addEventListener('click', openSettingsModal);
    if (els.btnTestLLM) els.btnTestLLM.addEventListener('click', onTestLLM);
    if (els.btnSaveSettings) els.btnSaveSettings.addEventListener('click', onSaveSettings);
    if (els.btnCancelSettings) els.btnCancelSettings.addEventListener('click', closeSettingsModal);

    startStatusPolling();
}

function openSettingsModal() {
    if (!els.settingsModal) return;
    loadLLMSettings();
    showSettingsMessage('', true);
    els.settingsModal.style.display = 'flex';
}

function closeSettingsModal() {
    if (els.settingsModal) els.settingsModal.style.display = 'none';
}

async function loadLLMSettings() {
    if (!els.settingsBaseUrl) return;
    try {
        const s = await api.getLLMSettings();
        els.settingsBaseUrl.value = s.llm_base_url || '';
        els.settingsModel.value = s.llm_model || '';
        els.settingsApiKey.value = '';
        els.settingsTemperature.value = s.llm_temperature;
        els.settingsMaxTokens.value = s.llm_max_tokens;
    } catch (e) {
        setStatus('加载设置失败: ' + e.message);
    }
}

function collectSettingsBody() {
    return {
        llm_base_url: els.settingsBaseUrl.value.trim(),
        llm_model: els.settingsModel.value.trim(),
        llm_api_key: els.settingsApiKey.value.trim(),
        llm_temperature: parseFloat(els.settingsTemperature.value),
        llm_max_tokens: parseInt(els.settingsMaxTokens.value, 10),
    };
}

function showSettingsMessage(text, success) {
    if (!els.settingsMessage) return;
    els.settingsMessage.textContent = text;
    els.settingsMessage.className = 'settings-message ' + (success ? 'success' : 'error');
}

function setButtonLoading(btn, loading, text) {
    if (!btn) return;
    btn.disabled = loading;
    btn.textContent = text;
}

async function onTestLLM() {
    setButtonLoading(els.btnTestLLM, true, '测试中...');
    try {
        const body = collectSettingsBody();
        const result = await api.testLLMConnection(body);
        showSettingsMessage(result.message, result.success);
    } catch (e) {
        showSettingsMessage('测试失败: ' + e.message, false);
    } finally {
        setButtonLoading(els.btnTestLLM, false, '测试连接');
    }
}

async function onSaveSettings() {
    setButtonLoading(els.btnSaveSettings, true, '保存中...');
    try {
        const body = collectSettingsBody();
        await api.updateLLMSettings(body);
        showSettingsMessage('设置已保存', true);
        setTimeout(closeSettingsModal, 800);
    } catch (e) {
        showSettingsMessage('保存失败: ' + e.message, false);
    } finally {
        setButtonLoading(els.btnSaveSettings, false, '保存');
    }
}

function showSetupModal(models) {
    if (!els.setupModal || !els.setupModelList) return;
    els.setupModal.style.display = 'flex';
    renderModelList(models);

    els.btnStartDownload.addEventListener('click', startModelDownloads);
    els.btnSkipDownload.addEventListener('click', () => finishInit({}));
}

function renderModelList(models) {
    if (!els.setupModelList) return;
    els.setupModelList.innerHTML = '';
    models.forEach(model => {
        const item = document.createElement('div');
        item.className = 'model-item';
        item.dataset.name = model.name;

        const header = document.createElement('div');
        header.className = 'model-header';

        const name = document.createElement('span');
        name.textContent = model.name;

        const status = document.createElement('span');
        status.className = `model-status ${model.status}`;
        status.textContent = translateModelStatus(model.status);

        header.appendChild(name);
        header.appendChild(status);

        const message = document.createElement('div');
        message.className = 'model-message';
        message.textContent = model.message || '';

        const progress = document.createElement('div');
        progress.className = 'model-progress';
        const fill = document.createElement('div');
        fill.className = 'model-progress-fill';
        fill.id = `model-progress-fill-${model.name}`;
        progress.appendChild(fill);

        item.appendChild(header);
        item.appendChild(message);
        item.appendChild(progress);
        els.setupModelList.appendChild(item);
    });
}

function translateModelStatus(status) {
    const map = {
        ready: '已就绪',
        pending: '等待下载',
        downloading: '下载中',
        done: '下载完成',
        error: '下载失败',
    };
    return map[status] || status;
}

async function startModelDownloads() {
    if (els.btnStartDownload) {
        els.btnStartDownload.disabled = true;
        els.btnStartDownload.textContent = '下载中...';
    }
    try {
        await api.downloadModels(null);
        startModelProgressPolling();
    } catch (e) {
        console.error('Failed to start downloads', e);
        setStatus('启动模型下载失败: ' + e.message);
        if (els.btnStartDownload) {
            els.btnStartDownload.disabled = false;
            els.btnStartDownload.textContent = '开始下载';
        }
    }
}

function startModelProgressPolling() {
    if (state.modelStatusTimer) {
        clearInterval(state.modelStatusTimer);
    }
    state.modelStatusTimer = setInterval(async () => {
        try {
            const progress = await api.modelProgress();
            updateModelProgress(progress);

            const allReady = progress.every(m => m.status === 'ready' || m.status === 'done');
            const hasError = progress.some(m => m.status === 'error');

            if (allReady) {
                clearInterval(state.modelStatusTimer);
                state.modelStatusTimer = null;
                finishInit({});
            } else if (hasError && els.btnStartDownload) {
                els.btnStartDownload.disabled = false;
                els.btnStartDownload.textContent = '重试';
            }
        } catch (e) {
            console.warn('Model progress polling failed', e);
        }
    }, 1000);
}

function updateModelProgress(progress) {
    progress.forEach(model => {
        const item = els.setupModelList.querySelector(`[data-name="${model.name}"]`);
        if (!item) return;

        const status = item.querySelector('.model-status');
        if (status) {
            status.className = `model-status ${model.status}`;
            status.textContent = translateModelStatus(model.status);
        }

        const message = item.querySelector('.model-message');
        if (message) {
            message.textContent = model.message || '';
        }

        const fill = item.querySelector('.model-progress-fill');
        if (fill && model.total_bytes && model.total_bytes > 0) {
            const pct = Math.round((model.downloaded_bytes / model.total_bytes) * 100);
            fill.style.width = `${pct}%`;
        }
    });
}

async function onScan() {
    let inputDir = '';
    let outputDir = '';

    if (window.pywebview && window.pywebview.api && window.pywebview.api.open_directory_dialog) {
        try {
            inputDir = await window.pywebview.api.open_directory_dialog('选择输入目录');
        } catch (e) {
            console.warn('Directory picker failed', e);
        }
        if (!inputDir) return;
        try {
            outputDir = await window.pywebview.api.open_directory_dialog('选择输出目录');
        } catch (e) {
            console.warn('Directory picker failed', e);
        }
        if (!outputDir) return;
    } else {
        inputDir = prompt('请输入输入目录绝对路径:', state.inputDir || '/tmp/ocr-input');
        outputDir = prompt('请输入输出目录绝对路径:', state.outputDir || '/tmp/ocr-output');
        if (!inputDir || !outputDir) return;
    }

    state.inputDir = inputDir.trim();
    state.outputDir = outputDir.trim();

    try {
        setStatus('正在扫描目录...');
        const result = await api.scan(state.inputDir, state.outputDir);
        setStatus(`扫描完成，共 ${result.total} 个文件，新增 ${result.added} 个任务`);
        await refreshTasks();
    } catch (e) {
        setStatus('扫描失败: ' + e.message);
        console.error(e);
    }
}

async function onStart() {
    if (!state.inputDir || !state.outputDir) {
        alert('请先扫描输入/输出目录');
        return;
    }
    try {
        const result = await api.start(state.inputDir, state.outputDir);
        setStatus(result.message);
        els.btnStart.disabled = true;
        els.btnStop.disabled = false;
    } catch (e) {
        setStatus('启动失败: ' + e.message);
    }
}

async function onStop() {
    try {
        const result = await api.stop();
        setStatus(result.message);
        els.btnStart.disabled = false;
        els.btnStop.disabled = true;
    } catch (e) {
        setStatus('停止失败: ' + e.message);
    }
}

async function refreshTasks() {
    if (!state.inputDir || !state.outputDir) return;
    try {
        const resp = await api.listTasks(state.inputDir, state.outputDir);
        state.tasks = resp.tasks;
        renderTree(resp);
        updateProgress(resp);
    } catch (e) {
        console.error('Failed to refresh tasks', e);
    }
}

function renderTree(resp) {
    els.tree.innerHTML = '';
    els.dirCount.textContent = resp.total;

    if (!state.tasks.length) {
        els.tree.innerHTML = '<div class="placeholder" style="padding:12px">暂无任务</div>';
        return;
    }

    state.tasks.forEach(task => {
        const item = document.createElement('div');
        item.className = 'tree-item';
        if (state.selectedPath === task.relative_path) {
            item.classList.add('active');
        }

        const dot = document.createElement('span');
        dot.className = `status-dot ${task.status}`;

        const label = document.createElement('span');
        label.textContent = task.relative_path;
        label.title = task.relative_path;

        item.appendChild(dot);
        item.appendChild(label);
        item.addEventListener('click', () => selectTask(task));
        els.tree.appendChild(item);
    });
}

function selectTask(task) {
    state.selectedPath = task.relative_path;
    renderTree({ total: state.tasks.length, tasks: state.tasks });

    // Show image preview
    const imgUrl = `/api/image?path=${encodeURIComponent(state.inputDir + '/' + task.relative_path)}`;
    els.imagePreview.innerHTML = `<img src="${imgUrl}" alt="preview" onerror="this.parentElement.innerHTML='<div class=\\'placeholder\\'>无法加载图片</div>'">`;

    // Load result texts if available
    const results = task.results_json || {};
    els.resultRapidocr.textContent = results.rapidocr || '-';
    els.resultHunyuan.textContent = results.hunyuan || '-';
    els.resultGlm.textContent = results.glm || '-';
    els.resultUnified.textContent = results.unified || '-';
}

function updateProgress(resp) {
    const total = resp.total || 1;
    const completed = resp.done + resp.failed;
    const pct = Math.round((completed / total) * 100);
    els.progressFill.style.width = `${pct}%`;
    els.progressText.textContent = `总任务 ${resp.total} | 完成 ${resp.done} | 失败 ${resp.failed} | 待处理 ${resp.pending} | 处理中 ${resp.processing}`;
}

function startStatusPolling() {
    state.statusTimer = setInterval(async () => {
        try {
            const s = await api.status();
            if (s.status === 'running') {
                els.btnStart.disabled = true;
                els.btnStop.disabled = false;
                setStatus(`处理中: ${s.progress.current_file || ''}`);
            } else {
                els.btnStart.disabled = false;
                els.btnStop.disabled = true;
            }
            // Refresh task list if a job is active or was recently active
            if (s.status === 'running' || s.progress.total > 0) {
                await refreshTasks();
            }
        } catch (e) {
            console.warn('Status polling failed', e);
        }
    }, 2000);
}

function setStatus(text) {
    els.statusText.textContent = text;
}

init();
