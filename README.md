# OCR Alliance

OCR Alliance 是一款跨平台桌面应用，通过并行调用多个先进的 OCR 模型，再经由大语言模型（LLM）统合结果，提升复杂扫描文档的识别准确率。

## 项目目标

- 批量 OCR 识别包含复杂排版、盖章、手写文字的扫描图片。
- 并行使用三个本地 OCR 模型：RapidOCR、HunyuanOCR、GLM-OCR。
- 由用户指定 LLM（OpenAI 兼容 API）统合多模型结果。
- 支持批量处理、断点续传、结果可视化。
- 发布 Windows(x86_64)、macOS(arm)、Linux(x86_64) 二进制包。

## 文档

- [技术架构文档](./docs/tech-architecture.md)
- [模型下载与放置指南](./docs/model-download-guide.md)

## 本地构建

```bash
pip install -e ".[packaging]"
python scripts/build.py
```

构建产物位于 `dist/OCRAlliance/`（目录形式，便于增量更新模型）。

## 发布

推送 `v*` 标签即可触发 GitHub Actions，自动构建并发布：

```bash
git tag v0.1.0
git push origin v0.1.0
```

也可以在 `main` 分支上手动触发 **Build Release** 工作流，输入 release tag（例如 `v0.1.0-main`）和是否标记为 prerelease，即可编译并发布：

- Linux x86_64 (`ocr-alliance-linux-x86_64.tar.gz`)
- Windows x86_64 (`ocr-alliance-windows-x86_64.zip`)
- macOS arm64 (`ocr-alliance-macos-arm64.zip`)

## 日志排查

如果启动后没有反应，可以查看日志文件定位问题：

- 源码运行：`data/ocr_alliance.log`
- 二进制包：可执行文件所在目录下的 `data/ocr_alliance.log`

日志采用滚动保留，最多保留 3 个历史文件。

## 当前状态

已完成基础桌面应用框架、FastAPI 后端、任务调度与持久化、Web 前端骨架、OCR 适配器接口、LLM 统合逻辑、端到端流水线测试、跨平台二进制构建工作流，以及模型自动下载与日志持久化。
