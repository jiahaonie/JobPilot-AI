# JobPilot AI

JobPilot AI 是一个面向岗位分析与学习知识库 Agent 的分层 FastAPI 项目。

当前版本已经按照项目规划建立以下模块边界：

- api：负责处理 HTTP 请求、返回响应和装配依赖。
- services：负责业务用例和业务流程。
- repositories：负责数据库访问。
- models 与 schemas：分别负责数据库模型和 API 数据契约。
- llm、rag 与 agents：作为可独立替换和测试的集成边界。

## 本地运行

安装开发依赖：

    uv sync --cache-dir .uv-cache --extra dev

首次运行或拉取到新迁移后，由 Alembic 创建或升级数据库：

    uv run --cache-dir .uv-cache --extra dev alembic upgrade head

运行测试：

    uv run --cache-dir .uv-cache pytest

启动开发服务器：

    uv run --cache-dir .uv-cache uvicorn app.main:app --reload

服务启动后，可以访问：

- API 地址：<http://127.0.0.1:8000>
- OpenAPI 接口文档：<http://127.0.0.1:8000/docs>

开发环境默认使用项目根目录下的 SQLite 数据库文件 `jobpilot.db`。
应用启动时不会自动建表，非测试数据库结构统一由 Alembic 管理。

## 已实现功能

- 岗位 CRUD（创建、查询、修改、删除）
- LLM 结构化 JD 解析：将原始岗位描述提取为技能、学历、职责和原文证据（DeepSeek，需配置 API Key）
- 简历管理：保存文本或上传 TXT/Markdown/电子 PDF，再独立触发 LLM 技能提取
- 简历与岗位匹配：输出技能覆盖分、已满足 / 缺失技能及原文证据，并可保存历史快照
- 有依据学习计划：按报告技能缺口检索已审核内置资料，由 DeepSeek 生成具体任务并保存引用快照；旧 `rule_v1` 计划保持兼容
- 本地知识库：TXT/Markdown 入库、Chroma 语义 Top-K 检索和余弦距离过滤
- Retrieval Evaluation：离线计算 Recall@K 与 MRR
- 带引用问答：无检索证据时拒答，并校验 `cited_chunk_ids`
- Agent：模型从 3 个真实工具中选择，参数校验后调用业务 Service/Repository

启动服务后，通过 Swagger 界面（`/docs`）或以下接口使用：

    POST /api/v1/jobs             # 创建岗位
    POST /api/v1/jobs/{id}/analyze        # 分析岗位并保存最新结果
    GET  /api/v1/jobs/{id}/requirements   # 只读取已有岗位分析结果
    POST /api/v1/resumes          # 保存简历文本（不调用 LLM）
    POST /api/v1/resumes/upload   # 上传 TXT/MD/电子 PDF（不调用 LLM）
    POST /api/v1/resumes/{id}/analyze # 单独触发或重试技能提取
    POST /api/v1/jobs/{id}/match  # 简历与岗位匹配
    POST /api/v1/jobs/{id}/match-reports # 匹配并保存历史报告
    GET  /api/v1/match-reports/{id}      # 读取历史报告
    GET  /api/v1/match-reports           # 筛选历史报告
    POST /api/v1/study-plans             # 创建或返回报告对应的 rag_v1 学习计划
    GET  /api/v1/study-plans/{id}        # 查询计划、进度和有序任务
    GET  /api/v1/study-plans             # 按报告、岗位或简历筛选计划
    PATCH /api/v1/study-tasks/{id}       # 更新任务状态
    POST /api/v1/knowledge/documents  # 上传知识文档
    POST /api/v1/knowledge/search     # 语义检索
    POST /api/v1/ask                  # 带引用问答
    POST /api/v1/agent/run            # 模型选择并执行工具

语义检索示例：

    {
      "query": "FastAPI 如何做依赖注入？",
      "top_k": 5,
      "max_distance": 0.45
    }

`distance` 是 Chroma cosine distance，越小越相关；超过 `max_distance`
的结果不会进入回答上下文。Agent 当前注册以下 4 个真实工具：

- `get_job_requirements`
- `compare_resume_with_job`
- `search_learning_material`
- `create_study_plan`

运行 Retrieval Evaluation：

    uv run --cache-dir .uv-cache --extra dev pytest -p no:cacheprovider tests/evaluation -q

## 配置 LLM

复制 `.env.example` 为 `.env`，填入 DeepSeek API Key：

    LLM_API_KEY=sk-xxxxxxxxxxxx

## 导入内置学习资料

先升级数据库，再将作者审核的电子 PDF 导入独立内置 collection：

    uv run --cache-dir .uv-cache --extra dev alembic upgrade head
    uv run --cache-dir .uv-cache --extra dev python -m scripts.import_builtin_knowledge "PDF 文件路径"

命令会输出文档 ID。将它写入 `.env`；多份资料用逗号分隔：

    RAG_BUILTIN_DOCUMENT_IDS=1

相同 PDF、嵌入模型和分块参数再次导入时会复用已成功结果。只有状态为
`ready`、标记为内置且已审核的配置文档能够参与学习计划生成。

可用下面的命令做一次不写业务数据的真实检索与生成检查：

    uv run --cache-dir .uv-cache --extra dev python -m scripts.smoke_builtin_study_plan "Agent 工具分类"

## 当前实现边界

本地真实 Chroma 的写入、查询和删除已有集成测试。内置资料导入需要电子 PDF；
扫描件、加密 PDF 和 OCR 留待后续。真实 FastEmbed 与 DeepSeek 可以用上述 smoke 命令检查，
但一次成功抽样不代表所有岗位技能都有资料覆盖，浏览器主流程仍应按实际部署环境验收。
