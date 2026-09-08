# Agent 开发工程师简历（JobPilot 测试用）

> 说明：这是一份为验证 JobPilot AI 简历解析、岗位匹配和分析流程准备的虚构测试简历。姓名、联系方式、公司名称和量化数据均为测试数据，不应直接用于真实求职。

## 基本信息

- 姓名：林子谦（虚构）
- 求职方向：Agent 开发工程师 / LLM 应用开发工程师 / RAG 应用工程师
- 所在城市：深圳
- 电话：138-0000-0000
- 邮箱：agent.test@example.com
- GitHub：github.com/example-agent-engineer

## 个人简介

具备 Python 后端和大语言模型应用开发经验，能够独立完成从需求分析、数据处理、Prompt 设计、工具调用、RAG 检索到 API 服务交付的完整链路。熟悉 FastAPI、Pydantic、SQLAlchemy、Alembic、React/TypeScript，能够使用 DeepSeek/OpenAI 兼容接口实现结构化输出、函数调用和 Agent 工作流。重视可解释性、错误处理和离线评测，能够通过 pytest、Recall@K、MRR 和人工评测验证系统效果。

## 实习经历

### 示例智能科技有限公司｜AI 应用开发实习生

2025.07 – 2026.02｜深圳

- 参与企业知识库 Agent 开发，使用 Python、FastAPI、Pydantic 和 SQLAlchemy 构建文档上传、切分、检索、问答和引用返回接口。
- 设计基于工具注册表的 Agent 执行流程，支持岗位要求查询、简历对比、知识库搜索和学习计划生成等工具；对工具名称、参数 Schema 和返回结果进行校验。
- 使用 DeepSeek 兼容 API 实现结构化 JSON 输出，增加超时、限次重试、模型响应解析失败和第三方服务不可用时的错误处理。
- 使用 FastEmbed 生成向量、Chroma 保存向量索引，通过 Top-K 检索和 cosine distance 阈值过滤控制上下文质量；回答中返回来源文档和 chunk 引用。
- 编写 pytest 单元测试和集成测试，覆盖 API 契约、数据库事务、工具参数校验、无证据拒答、LLM 超时和重复请求等场景。
- 将一次完整请求拆分为“输入校验 → Agent 决策 → 工具执行 → 结果校验 → 结构化响应”，便于日志追踪和问题定位。

## 项目经历

### 招聘岗位分析与学习路径 Agent

2025.02 – 2025.06｜个人项目

技术栈：Python、FastAPI、React、TypeScript、DeepSeek API、Pydantic、SQLAlchemy、Alembic、SQLite、pytest

- 接收岗位描述和简历文本，使用 LLM 提取岗位技能、学历要求、工作职责和原文证据，并以 Pydantic Schema 校验输出。
- 实现岗位与简历的技能匹配，输出技能覆盖分、已满足技能、缺失技能、优先补齐技能以及对应证据。
- 将岗位分析、简历分析和匹配报告分离保存，支持失败重试，并避免读取接口隐式触发 LLM 调用。
- 基于匹配报告生成规则化学习计划，支持任务排序、状态更新和完成度计算；历史匹配报告保存为不可变快照。
- 使用 Alembic 管理数据库迁移，使用 SQLite 外键级联和事务保证岗位、简历、报告之间的数据一致性。
- 编写 API 集成测试和服务层单元测试，覆盖 404、409、422、503 等异常响应以及重复分析场景。

### 企业知识库问答 Agent

2024.09 – 2025.01｜个人项目

技术栈：Python、FastAPI、Chroma、FastEmbed、Markdown、PDF、pytest

- 支持 TXT、Markdown 和电子 PDF 文档导入，完成文本提取、清洗、分块、向量化和索引写入。
- 设计带引用的问答流程：先检索相关 chunk，再将文档来源、chunk ID 和正文注入上下文；没有足够证据时明确拒答。
- 使用 Recall@K 和 MRR 评估检索质量，针对 chunk 大小、重叠长度、Top-K 和距离阈值进行对比实验。
- 增加文档删除、重复导入、空问题、超大文件和向量索引异常等边界处理。

### 多工具个人效率助手

2024.03 – 2024.07｜课程项目

技术栈：Python、FastAPI、Function Calling、JSON Schema、Redis、Docker

- 实现日程查询、任务创建、网页内容摘要和本地知识搜索四个工具，通过 Function Calling 让模型选择工具。
- 使用 JSON Schema 校验工具参数，限制工具访问范围，避免模型生成参数直接进入数据库或文件系统。
- 为工具调用增加超时、重试、幂等键和失败回退逻辑，并记录 request_id、tool_name、latency 和 error_type。
- 使用 Docker 编排 API、Redis 和本地开发环境，编写接口文档和启动说明。

## 技术能力

- 编程语言：Python、SQL、TypeScript、JavaScript
- Agent 开发：Tool Calling、Function Calling、ReAct、Agent Orchestrator、工具注册表、参数校验、状态管理、重试与回退
- LLM 应用：Prompt Engineering、结构化输出、JSON Schema、DeepSeek/OpenAI 兼容 API、上下文控制、证据约束
- RAG：文档解析、文本分块、Embedding、FastEmbed、Chroma、Top-K 检索、cosine distance、引用溯源、Recall@K、MRR
- 后端：FastAPI、Pydantic、SQLAlchemy、Alembic、SQLite、PostgreSQL、REST API、OpenAPI
- 前端：React、TypeScript、Vite、表单状态、加载/空数据/错误状态
- 工程实践：pytest、Ruff、ESLint、Docker、Git、日志、API 集成测试、离线评测

## 教育经历

### 某理工大学｜计算机科学与技术｜本科

2022.09 – 2026.06

- 相关课程：数据结构与算法、操作系统、数据库系统、计算机网络、软件工程、机器学习
- 课程设计：使用 Python 完成文本检索、向量相似度计算和 REST API 服务开发

## 证书与补充信息

- 英语：能够阅读 FastAPI、Pydantic、LangChain、Chroma 和主流 LLM API 官方文档
- 开发习惯：先定义 API 和数据契约，再实现服务；为关键业务流程编写可重复测试
- 求职偏好：Agent 应用开发、RAG 系统、LLM 后端、AI 工具调用和可评测的 AI 产品
