/**
 * Minimal API client for OCR Alliance backend.
 */

const API_BASE = '/api';

async function apiPost(path, body) {
    const resp = await fetch(API_BASE + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || resp.statusText);
    }
    return resp.json();
}

async function apiGet(path) {
    const resp = await fetch(API_BASE + path);
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || resp.statusText);
    }
    return resp.json();
}

const api = {
    scan: (inputDir, outputDir) => apiPost('/scan', { input_dir: inputDir, output_dir: outputDir }),
    listTasks: (inputDir, outputDir) => apiGet('/tasks?' + new URLSearchParams({ input_dir: inputDir, output_dir: outputDir })),
    start: (inputDir, outputDir) => apiPost('/start', { input_dir: inputDir, output_dir: outputDir }),
    stop: () => apiPost('/stop', {}),
    status: () => apiGet('/status'),
    settings: () => apiGet('/settings'),
};
