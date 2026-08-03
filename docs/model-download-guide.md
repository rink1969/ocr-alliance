# 模型下载与放置指南

OCR Alliance 内置三个 OCR 模型目录，应用启动时会自动创建这些目录。模型权重文件**不会**随二进制包一起发布，需要按本指南下载并放到指定位置，或在 `.env` 中配置自定义路径。

## 模型目录结构

应用启动后会在程序根目录自动创建：

```
models/
├── paddleocr-vl-1.6/
├── hunyuanocr/
└── glm-ocr/
```

> 如果你下载的是 GitHub Release 的二进制包，`models/` 位于可执行文件所在目录；如果你从源码运行，`models/` 位于项目根目录。

## 使用二进制包

二进制包已经把 Python 运行依赖（PyTorch、Transformers 等）打包在内，你**不需要**再安装这些依赖，只需下载模型权重文件。

### PaddleOCR-VL-1.6

PaddleOCR-VL-1.6 是一个 0.9B 参数的视觉语言模型，可通过 Transformers 加载。

- Hugging Face：<https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6>
- 魔搭社区：<https://modelscope.cn/models/PaddlePaddle/PaddleOCR-VL-1.6>

下载全部模型文件（如 `config.json`、`model.safetensors` 等）后放入：

- `models/paddleocr-vl-1.6/`

### HunyuanOCR

- Hugging Face：<https://huggingface.co/Tencent-Hunyuan/HunyuanOCR>
- 魔搭社区：<https://modelscope.cn/models/Tencent-Hunyuan/HunyuanOCR>

下载全部模型文件后放入：

- `models/hunyuanocr/`

### GLM-OCR

- Hugging Face：<https://huggingface.co/ZhipuAI/GLM-OCR>
- 魔搭社区：<https://modelscope.cn/models/ZhipuAI/GLM-OCR>

下载全部模型文件后放入：

- `models/glm-ocr/`

## 从源码运行

源码运行时需要先安装运行依赖：

```bash
pip install -e "."
```

然后再按上方“使用二进制包”章节的步骤下载并放置模型权重。

## LLM 统合模型

LLM 用于统合三个 OCR 引擎的结果，通过 OpenAI 兼容 API 调用。无论使用二进制还是源码，都需要在 `.env` 中配置：

```bash
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o
LLM_API_KEY=your-api-key
```

也支持任何提供 `/chat/completions` 接口的服务商。
