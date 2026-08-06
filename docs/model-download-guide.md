# 模型下载与放置指南

OCR Alliance 首次启动时会自动检测 OCR 模型是否存在。如果缺失，应用会从魔搭社区自动下载，并显示下载进度；已有模型时会直接跳过。

模型权重文件**不会**随二进制包一起发布，但应用内置了自动下载逻辑。你也可以手动下载后放入对应目录，或在 `.env` 中关闭自动下载。

## 模型目录结构

应用启动后会在程序根目录自动创建：

```
models/
├── rapidocr/
├── hunyuanocr/
└── glm-ocr/
```

> 注：`rapidocr` 的 ONNX 模型已内置在 `rapidocr` Python 包中，不需要额外下载；该目录仅作保留。`hunyuanocr` 和 `glm-ocr` 需要下载 VLM 权重。

> 如果你下载的是 GitHub Release 的二进制包，`models/` 位于可执行文件所在目录；如果你从源码运行，`models/` 位于项目根目录。

## 自动下载（推荐）

启动应用后，前端会弹出模型下载窗口。点击“开始下载”后，应用会从魔搭社区自动拉取以下模型：

| 模型 | 魔搭社区地址 |
|------|-------------|
| HunyuanOCR | <https://modelscope.cn/models/Tencent-Hunyuan/HunyuanOCR> |
| GLM-OCR | <https://modelscope.cn/models/ZhipuAI/GLM-OCR> |

下载完成后，窗口会自动消失并进入主界面。后续启动时如果模型已存在，则不会再下载。

### 关闭自动下载

在 `.env` 中添加：

```bash
AUTO_DOWNLOAD_MODELS=false
```

关闭后，你需要按下方“手动下载”章节自行放置模型文件。

## 手动下载

如果你选择手动下载，可以从魔搭社区或 Hugging Face 获取模型文件，放入对应目录。

### HunyuanOCR

- 魔搭社区：<https://modelscope.cn/models/Tencent-Hunyuan/HunyuanOCR>
- Hugging Face：<https://huggingface.co/Tencent-Hunyuan/HunyuanOCR>

放入：`models/hunyuanocr/`

### GLM-OCR

- 魔搭社区：<https://modelscope.cn/models/ZhipuAI/GLM-OCR>
- Hugging Face：<https://huggingface.co/ZhipuAI/GLM-OCR>

放入：`models/glm-ocr/`

## 从源码运行

源码运行时需要先安装运行依赖：

```bash
pip install -e "."
```

然后再启动应用即可。模型会在首次启动时自动下载，或者你也可以按上方“手动下载”章节提前放置。

## LLM 统合模型

LLM 用于统合三个 OCR 引擎的结果，通过 OpenAI 兼容 API 调用。无论使用二进制还是源码，都需要在 `.env` 中配置：

```bash
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o
LLM_API_KEY=your-api-key
```

也支持任何提供 `/chat/completions` 接口的服务商。
