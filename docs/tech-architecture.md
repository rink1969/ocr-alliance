# OCR Alliance 技术架构文档

## 1. 项目概述

OCR Alliance 是一款带 WebUI 的跨平台桌面应用，用于批量 OCR 识别扫描纸质文件图片。应用通过并行调用三个先进的本地 OCR 模型，再经由用户指定的大语言模型（LLM）统合结果，以达到比单一 OCR 工具更高的识别准确率。

### 1.1 核心需求

- 批量处理输入文件夹中的图片，输出到指定文件夹并保持目录结构。
- 每个图片生成 4 个 OCR 结果文件：分别来自 PaddleOCR-VL-1.6、HunyuanOCR、GLM-OCR，以及 LLM 统合结果。
- 支持处理进度持久化，应用重启后可断点续传。
- 结果可视化：左侧目录树、右侧展示原图与三模型结果及统合结果，并高亮差异。
- 发布 Windows(x86)、macOS(arm)、Linux(x86) 三个平台的二进制包。
- 模型权重不打包进二进制，应用负责指引用户下载并放置到指定目录。

## 2. 技术选型

### 2.1 总体技术栈

| 模块 | 技术选型 | 选型理由 |
|------|---------|---------|
| 后端语言/运行时 | Python 3.10+ | 三个 OCR 模型均生于 Python 生态，官方示例、依赖和社区支持最完善。 |
| Web 服务框架 | FastAPI | 异步能力强、类型注解友好、自动生成 API 文档，适合前端调用。 |
| 桌面窗口壳 | pywebview | 轻量，调用系统原生 WebView（Windows WebView2、macOS WKWebView、Linux WebKitGTK），无需内嵌 Chromium。 |
| 前端技术 | 原生 HTML / CSS / JavaScript | 无需构建步骤，降低复杂度；目录树、图片预览、差异高亮均可原生实现。 |
| 前后端通信 | pywebview `expose` + FastAPI HTTP API | 前端可直接调用 Python 函数，也可走本地 HTTP 服务。 |
| 进度/配置持久化 | SQLite | 单文件、零配置、Python 内置 sqlite3 即可，适合断点续传。 |
| 打包工具 | PyInstaller | Python 桌面应用打包方案成熟，支持生成单文件/单目录可执行程序。 |
| CI/CD | GitHub Actions | 可在 `windows-latest`、`macos-latest`、`ubuntu-latest` runner 上分别构建三平台产物。 |

### 2.2 为什么不选 Electron / Tauri

- **Electron**：需要内嵌 Chromium 与 Node.js，打包体积巨大、内存占用高，对本项目没有必要。
- **Tauri**：Rust + WebView 的组合确实体积更小、原生集成更强，但 OCR 引擎全部依赖 Python，采用 Tauri 意味着需要同时维护 Rust 前端壳与 Python 后端两套运行时，并通过 IPC/HTTP 桥接，增加了打包与调试复杂度。本项目以 Python 统一栈为最优解。

## 3. 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      桌面应用窗口 (pywebview)                    │
│  ┌───────────────────┐  ┌───────────────────────────────────┐  │
│  │  左侧目录树        │  │  右侧内容区                        │  │
│  │  - 输入文件夹      │  │  - 原始图片预览                    │  │
│  │  - 处理状态标记    │  │  - 三个 OCR 模型识别结果            │  │
│  │  - 点击切换文件    │  │  - LLM 统合结果                    │  │
│  │                    │  │  - 不一致内容高亮                  │  │
│  └───────────────────┘  └───────────────────────────────────┘  │
└──────────────────────────┬────────────────────────────────────┘
                           │ JS ↔ Python API (pywebview expose)
┌──────────────────────────▼────────────────────────────────────┐
│                    Python 后端服务 (FastAPI)                     │
│  - 任务调度 / 批处理队列                                          │
│  - 进度持久化 (SQLite)                                            │
│  - OCR 模型适配器层                                               │
│  - LLM 统合调用 (OpenAI 兼容 API)                                 │
└──────────────────────────┬────────────────────────────────────┘
                           │ 适配器调用
┌──────────────────────────▼────────────────────────────────────┐
│                      OCR 模型推理层                              │
│   PaddleOCR-VL-1.6      HunyuanOCR         GLM-OCR              │
│   (paddlepaddle /       (transformers /     (transformers /     │
│    transformers)          vLLM 可选)        vLLM 可选)          │
└─────────────────────────────────────────────────────────────────┘
```

## 4. OCR 模型集成策略

三个目标模型均为 0.9B~1.6B 参数规模的视觉语言模型（VLM）：

| 模型 | 参数规模 | 默认推理方式 | 可选加速 | 模型目录 |
|------|---------|-------------|---------|---------|
| PaddleOCR-VL-1.6 | 0.9B | `paddleocr` 官方 Python API + `paddlepaddle` | vLLM 服务 | `models/paddleocr-vl-1.6/` |
| HunyuanOCR | 1B | `transformers` (`HunYuanVLForConditionalGeneration`) | vLLM / llama.cpp | `models/hunyuanocr/` |
| GLM-OCR | 0.9B | `transformers` 开发版 + `AutoModelForImageTextToText` | vLLM / SGLang / Ollama | `models/glm-ocr/` |

### 4.1 推理后端选择

- **默认使用 transformers 原生推理**：兼容性最好，支持 CPU / CUDA / MPS（macOS），无需额外安装推理服务器。
- **vLLM 作为可选加速后端**：在 Linux/Windows + NVIDIA GPU 环境下可显著提升吞吐，但 vLLM 对 macOS 与 Windows 的支持有限，因此不作为默认。
- **模型适配器层**：每个模型封装为独立 Adapter，统一输入输出接口，便于后续替换推理后端或升级模型版本。

### 4.2 执行策略

- **串行执行（默认）**：一次只加载一个 OCR 模型，处理完当前图片后释放/切换，降低显存与内存峰值。
- **可配置并行度**：高级用户可选择同时加载多个模型以加速，但需要足够的 GPU 显存（三模型 FP16 同时驻留约需 6~10GB+）。
- **自动设备选择**：检测 CUDA → MPS（macOS）→ CPU 的优先级自动选择。
- **模型存在性检查**：启动时扫描 `models/` 目录，缺失模型时弹出下载指引，并提供 `docs/model-download-guide.md` 与下载脚本说明。

## 5. LLM 统合策略

### 5.1 接口

- 采用 **OpenAI 兼容 Chat Completions API**。
- 用户配置项：baseURL、model id、apiKey、温度/最大 token 等。

### 5.2 Prompt 设计

- 输入：原始图片（可选 base64）+ 三个 OCR 模型输出的文本。
- 指令示例：

```text
你是一位文档识别专家。以下是一张扫描图片经三个不同 OCR 模型识别后的结果。
请综合三个结果，输出最准确、最完整的文本，并尽量保留原始排版。
对于三个结果不一致的地方，请根据上下文判断最可信的内容。

[PaddleOCR-VL-1.6 结果]
...

[HunyuanOCR 结果]
...

[GLM-OCR 结果]
...

请直接输出最终统合后的文本，不要添加额外解释。
```

### 5.3 输出与容错

- 输出文件：`{原文件名}.unified.txt`。
- LLM 调用失败时，仍保留三个 OCR 结果文件，并在数据库中标记统合失败，用户可后续手动重试。
- 失败重试策略：指数退避，最多重试 3 次。

## 6. 文件与进度设计

### 6.1 输入输出约定

- **输入**：用户选择的文件夹，应用递归扫描图片文件（默认支持 `*.jpg`, `*.jpeg`, `*.png`, `*.tiff`, `*.bmp`, `*.webp`）。
- **输出**：用户选择的文件夹，保持与输入相同的相对目录结构。
- **结果文件命名**：每个输入图片生成 4 个文本文件，后缀分别为模型名：
  - `{原文件名}.paddleocr.txt`
  - `{原文件名}.hunyuan.txt`
  - `{原文件名}.glm.txt`
  - `{原文件名}.unified.txt`

### 6.2 进度持久化

使用 SQLite 记录任务队列，建议表结构：

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    input_path TEXT NOT NULL,
    output_dir TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    status TEXT NOT NULL,        -- pending / processing / done / failed
    results_json TEXT,           -- 各模型结果文件路径及状态
    error TEXT,                  -- 失败原因
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

- 扫描阶段：将输入目录所有图片写入任务表，状态为 `pending`。
- 处理阶段：取出 `pending` 任务，更新为 `processing`，完成后更新为 `done`；失败则更新为 `failed` 并记录错误。
- 重启后：加载任务表，跳过 `done`，重试 `failed` 与 `pending`。

## 7. WebUI 设计

### 7.1 布局

- **左侧目录树**：展示输入文件夹结构，节点显示处理状态（未处理 / 处理中 / 完成 / 失败）。用户点击节点切换文件。
- **右侧内容区**：
  - 上方：原始图片预览。
  - 下方：四个结果卡片/列，分别为 PaddleOCR-VL-1.6、HunyuanOCR、GLM-OCR、LLM 统合结果。
  - 不一致处使用 `diff-match-patch` 高亮显示。

### 7.2 配置面板

- 输入/输出目录选择。
- 模型路径设置与下载指引。
- LLM API 参数：baseURL、model id、apiKey、温度、最大 token。
- 高级选项：并行度、设备选择、图片格式过滤。

### 7.3 实时日志

- 底部可折叠日志区，显示当前处理进度、模型加载状态、错误信息。

## 8. 跨平台打包方案

### 8.1 打包工具

- 使用 **PyInstaller** 将 Python 后端、前端静态资源、依赖库打包为各平台可执行文件。
- 产物形式建议：单目录包（启动更快、调试更方便），也可提供单文件包。

### 8.2 CI/CD 流程

GitHub Actions workflow 在以下 runner 上构建：

| Runner | 目标平台 | 产物示例 |
|--------|---------|---------|
| `windows-latest` | Windows x86 | `ocr-alliance-windows-x86.zip` |
| `macos-latest` (arm64) | macOS arm | `ocr-alliance-macos-arm.dmg` 或 `.zip` |
| `ubuntu-latest` | Linux x86 | `ocr-alliance-linux-x86.tar.gz` 或 AppImage |

### 8.3 模型权重处理

- 打包产物**不包含模型权重**。
- 首次启动时检测 `models/` 目录，缺失时弹出指引窗口，并打开 `docs/model-download-guide.md`。
- 提供可选的 `scripts/download_models.py` 辅助脚本，帮助用户通过 `huggingface-cli` 或 `modelscope` 下载。

## 9. 推荐项目目录结构

```
ocr-alliance/
├── src/
│   ├── main.py                 # 应用入口：启动 FastAPI + pywebview
│   ├── api/
│   │   ├── routes.py           # FastAPI 路由
│   │   └── schemas.py          # Pydantic 请求/响应模型
│   ├── core/
│   │   ├── config.py           # 配置管理
│   │   ├── database.py         # SQLite 数据库操作
│   │   ├── scheduler.py        # 批处理调度器
│   │   └── file_utils.py       # 目录扫描、路径处理
│   ├── ocr/
│   │   ├── base.py             # OCR 模型适配器基类
│   │   ├── paddleocr.py        # PaddleOCR-VL-1.6 适配器
│   │   ├── hunyuanocr.py       # HunyuanOCR 适配器
│   │   ├── glmocr.py           # GLM-OCR 适配器
│   │   └── registry.py         # 模型注册与选择
│   ├── llm/
│   │   └── unifier.py          # LLM 统合调用
│   └── web/
│       ├── index.html
│       ├── css/
│       ├── js/
│       └── assets/
├── models/                     # 运行时模型目录（用户下载后放置，不提交到 Git）
│   ├── paddleocr-vl-1.6/
│   ├── hunyuanocr/
│   └── glm-ocr/
├── docs/
│   ├── tech-architecture.md    # 本文件
│   └── model-download-guide.md # 模型下载与放置说明
├── scripts/
│   └── download_models.py      # 可选：一键下载脚本
├── tests/
├── requirements.txt            # Python 依赖
├── pyproject.toml              # 项目元数据与工具配置
├── pyinstaller.spec            # PyInstaller 打包配置
├── README.md
└── .github/workflows/
    └── build.yml               # 三平台 CI 构建
```

## 10. 关键依赖（初稿）

```text
fastapi
uvicorn[standard]
pywebview
pillow
pydantic
pydantic-settings
aiofiles
transformers>=4.40.0
torch>=2.0.0
huggingface-hub
paddleocr[doc-parser]>=3.6.0
paddlepaddle                  # 或 paddlepaddle-gpu，按平台选择
openai
```

> **注意**：`PaddlePaddle`、`PyTorch`、`transformers` 之间存在版本兼容风险，实现阶段需在隔离环境（venv/conda）中充分测试。若冲突难以解决，可将 PaddleOCR 推理拆分为独立子进程，通过本地 HTTP/IPC 调用。

## 11. 风险与应对

| 风险 | 影响 | 应对策略 |
|------|------|---------|
| 依赖冲突（Paddle / PyTorch / transformers） | 高 | 隔离环境测试；必要时将 PaddleOCR 拆分为独立子进程。 |
| 打包体积过大 | 中 | 仅打包必要依赖；模型权重外置。 |
| 无 GPU 时 CPU 推理极慢 | 中 | 启动时检测并提示用户；提供量化模型/vLLM 可选配置。 |
| 模型官方接口变更 | 中 | 通过适配器层隔离具体调用；持续关注官方 release note。 |
| LLM API 调用失败或限流 | 中 | 失败重试 + 指数退避；保存中间 OCR 结果。 |
| 三个模型输出格式差异大 | 中 | 适配器层统一输出为纯文本/Markdown；LLM prompt 中明确说明格式。 |

## 12. 后续实施阶段建议

1. **阶段 1 — 基础骨架**：搭建 FastAPI + pywebview 最小可运行应用；实现目录扫描与 SQLite 任务表。
2. **阶段 2 — 单模型打通**：先集成一个 OCR 模型（如 HunyuanOCR），实现单张图片识别与结果保存。
3. **阶段 3 — 三模型集成**：抽象适配器层，集成 PaddleOCR-VL-1.6 与 GLM-OCR。
4. **阶段 4 — LLM 统合**：接入 OpenAI 兼容 API，实现统合与差异高亮。
5. **阶段 5 — UI 完善**：目录树、图片预览、结果对比、配置面板、实时日志。
6. **阶段 6 — 打包与 CI**：PyInstaller 本地验证 + GitHub Actions 三平台构建。
7. **阶段 7 — 文档与模型指引**：编写 `model-download-guide.md` 与下载脚本。
