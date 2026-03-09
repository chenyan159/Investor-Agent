# Investor-Agent (Google Drive + LangGraph + Web App)

这是一个可部署的网页工具，实现你要求的两种模式：

- **方式1**：输入 `prompt` 模板 + 可选列表，使用 `{{item}}` 替换并行执行；支持模型选择；支持保存配置（命名）；支持开关控制是否提取公司名/股票代号并保存。
- **方式2**：可切换项目。每个项目在 Google Drive 下对应一个**同名文件夹**，项目内配置、运行记录、输出结果都写回该文件夹。

## 架构

- 前端：静态页面（`static/index.html` + `static/app.js`）
- 后端：FastAPI（`app/main.py`）
- 执行引擎：LangGraph / LangChain（`app/workflow.py`）
- 存储层：Google Drive API（`app/drive_store.py`）

## Google Drive 作为数据库/服务端存储

应用会在 Drive 中创建（或复用）一个根目录（默认 `InvestorAgentProjects`），每个项目一个子目录：

- `saved_configs.json`：保存的 prompt/list/设置
- `runs.jsonl`：每次运行记录（jsonl）
- `outputs.json`：扁平化输出汇总
- `meta.json`：元信息

## 环境变量

至少需要配置 Drive 服务账号之一：

- `GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/service_account.json`
- 或 `GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'`

可选：

- `GOOGLE_DRIVE_ROOT_FOLDER_NAME=InvestorAgentProjects`
- `GOOGLE_DRIVE_ROOT_FOLDER_ID=<existing_folder_id>`
- `LLM_PROVIDER=gemini` 或 `openai`（默认 `gemini`）
- `GOOGLE_API_KEY=<for langchain_google_genai>`
- `OPENAI_API_KEY=<for langchain_openai>`

## 启动

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

浏览器打开：

- `http://localhost:8000`

## 方式1使用说明

1. 选择或创建项目。
2. 输入 Prompt 模板（可含 `{{item}}`）。
3. 列表每行一个字符串（可为空）。
4. 选择模型，设置公司名/股票代码提取开关。
5. 点击“并行运行”。
6. 如需保存配置，输入“保存配置名称”后点击保存。

## 方式2使用说明

- 顶部可切换/创建项目。
- 项目名对应 Drive 文件夹名。
- 项目所有数据自动保存到该项目目录，因此只要账号可访问 Drive，在任何地方打开该网页都能使用。

## 备注

- 默认提取逻辑为正则启发式，可按你后续需要改成专门的 NER/证券代码识别链。
- 并行执行采用 `asyncio.gather` + LangGraph `ainvoke`。
