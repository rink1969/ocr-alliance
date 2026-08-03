/**
 * Frontend application logic for OCR Alliance.
 */

const state = {
    inputDir: '',
    outputDir: '',
    tasks: [],
    selectedPath: null,
    statusTimer: null,
};

const els = {
    tree: document.getElementById('tree'),
    dirCount: document.getElementById('dir-count'),
    imagePreview: document.getElementById('image-preview'),
    resultPaddle: document.getElementById('result-paddleocr'),
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
};

async function init() {
    try {
        const settings = await api.settings();
        console.log('Settings:', settings);
    } catch (e) {
        console.warn('Failed to load settings', e);
    }

    if (window.pywebview && window.pywebview.api) {
        try {
            const platform = await window.pywebview.api.get_platform();
            els.platformInfo.textContent = platform;
        } catch (e) {
            console.warn('Failed to get platform', e);
        }
    }

    els.btnScan.addEventListener('click', onScan);
    els.btnStart.addEventListener('click', onStart);
    els.btnStop.addEventListener('click', onStop);
    els.btnSettings.addEventListener('click', () => alert('设置面板待实现'));

    startStatusPolling();
}

async function onScan() {
    // Placeholder: in production, use a file picker via pywebview or a settings panel
    const inputDir = prompt('请输入输入目录绝对路径:', state.inputDir || '/tmp/ocr-input');
    const outputDir = prompt('请输入输出目录绝对路径:', state.outputDir || '/tmp/ocr-output');
    if (!inputDir || !outputDir) return;

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
    els.resultPaddle.textContent = results.paddleocr || '-';
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
