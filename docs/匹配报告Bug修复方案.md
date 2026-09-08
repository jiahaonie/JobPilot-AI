# JobPilot AI 匹配报告 Bug 修复方案

## 1. 结论

当前问题是匹配输入契约不一致，不是单个 `Python` 关键词遗漏，也不是前端展示错误。

岗位分析会把完整要求句子写入 `required_skills`，简历分析则输出 `Python`、`FastAPI` 等原子技能。当前匹配器只比较规范化后的完整字符串，因此即使 JD 和简历都明确包含同一技能，也可能得到未匹配和 `0` 分。

本次修复应升级为通用的匹配报告 V2：JD 和简历中的同一技能必须得到相同规范键；简历具备则匹配，简历不具备则缺失；不得为某一份简历或 `Python` 编写特判。

## 2. 已确认的故障链路

本次真实测试数据中：

- JD 包含 `Python/TypeScript/Go`、`Prompt Engineering`、`Tool Use` 等要求。
- 简历技能包含 `Python`、`TypeScript`、`Prompt Engineering`、`Tool Calling` 等。
- 岗位分析将“熟练掌握至少一门主流编程语言……”整句保存为一个技能。
- `MatchService` 使用“岗位技能规范键是否存在于简历技能集合”的完整相等判断。
- 整句岗位要求不等于单独的 `Python`，最终 `matched_skills=[]`，技能覆盖分为 `0.0`。
- 学习计划随后直接消费错误的 `priority_skills`，因此也生成了整句式任务。

根因集中在三个位置：

1. JD 提取契约没有要求技能必须原子化，也无法表达“任意满足”与“全部满足”。
2. JD 和简历没有使用同一种结构化技能契约。
3. 匹配器只能比较单个字符串，无法处理组合要求。

## 3. 修复目标

### 3.1 通用匹配不变量

对任意技能 `X`：

```text
JD 要求 X，并且简历具备 X       -> 匹配成功
JD 要求 X，但简历不具备 X       -> 匹配失败
两侧只是大小写或分隔符不同       -> 匹配成功
两侧属于已确认的等价表达         -> 匹配成功
只是相关、相似或存在子串关系     -> 不自动匹配
```

`Python` 仅作为回归样例。相同逻辑必须适用于 Java、Rust、Kubernetes、LangGraph、向量数据库以及未来出现的新技能。

### 3.2 产品目标

- 岗位要求以原子技能或技能组选项参与匹配。
- 支持“任意满足”和“全部满足”两种组合关系。
- 报告区分已覆盖、部分覆盖、尚未覆盖。
- 每项结果包含 JD 证据，并尽量返回简历中的命中证据。
- 评分只包含可可靠判断的技术能力。
- 匹配过程保持确定性、可重复和可测试，不在生成报告时再次调用 LLM。
- V1 历史报告保持不可变，不删除、不覆盖。

### 3.3 本次不处理

- 不优化学习计划的任务模板和资源推荐。
- 不引入向量相似度作为技能匹配依据。
- 不让 LLM 在生成报告时直接决定“匹配或不匹配”。
- 不评估候选人的真实熟练度、项目深度或录用概率。
- 不扩展多用户、权限和部署能力。

## 4. V2 岗位要求契约

新增结构化技能要求，不再让完整自然语言句子直接充当技能名称。

```python
class SkillRequirement(BaseModel):
    label: str
    importance: Literal["required", "preferred"]
    match_mode: Literal["any", "all"]
    options: list[str]
    evidence: str


class UnscoredRequirement(BaseModel):
    category: Literal["experience", "education", "soft_skill", "other"]
    text: str
    evidence: str
```

字段含义：

- `label`：面向用户展示的简短能力名称，例如“主流编程语言”。
- `importance`：必需能力或加分能力。
- `match_mode=any`：`options` 命中任意一个即满足。
- `match_mode=all`：逐项检查 `options`，允许显示部分覆盖。
- `options`：只保存可独立比较的原子技能，不保存要求语气、经验描述和完整句子。
- `evidence`：必须是 JD 中支持该要求的原文片段。
- `UnscoredRequirement`：保存经验、学历和软能力等不能仅凭技能词可靠评分的要求。

示例一：

```json
{
  "label": "主流编程语言",
  "importance": "required",
  "match_mode": "any",
  "options": ["Python", "TypeScript", "Go"],
  "evidence": "熟练掌握至少一门主流编程语言（Python/TypeScript/Go 等）"
}
```

示例二：

```json
{
  "label": "Agent 核心机制",
  "importance": "required",
  "match_mode": "all",
  "options": ["Planning", "Memory", "Tool Use", "Reflection"],
  "evidence": "深入理解 Agent 原理与架构，包括 Planning、Memory、Tool Use、Reflection 等核心机制"
}
```

规范键由应用代码计算，不接受 LLM 直接生成或持久化，避免模型自行创造匹配关系。

## 5. JD 提取规则

更新 `build_job_requirement_prompt` 和 Pydantic Schema，使模型遵守以下规则：

1. 每个 `option` 必须是一个独立技能、工具、语言、框架或技术概念。
2. “熟练掌握”“有经验”“了解”等程度描述不得进入 `option`。
3. “至少一种”“任意一种”“或”对应 `match_mode=any`。
4. 明确要求多个能力共同具备时使用 `match_mode=all`。
5. 技术技能之外的经验、学历和软能力进入非评分要求。
6. 每项要求必须携带对应的 JD 原文证据，不得使用整份 JD 作为统一证据。
7. 不得补充 JD 中不存在的技能。

服务层在写入数据库前执行确定性校验：

- `options` 非空并去重。
- 单个技能不得包含换行或句末分隔符，不得保存明显的枚举长句。
- 原文证据必须能够在 JD 中找到。
- `any` 和 `all` 至少包含一个选项。
- 规范化后为空或重复的选项直接拒绝。

不再静默保存不符合契约的分析结果。结构校验失败时，岗位分析应进入 `failed`，并返回可定位的错误信息。

## 6. 技能标准化规则

JD 选项和简历技能必须调用同一个 `SkillNormalizer`。

基础规范化包括：

- Unicode NFKC 规范化。
- 大小写不敏感。
- 忽略无语义的空格、点号、下划线、连字符和斜杠差异。
- 保留词边界，避免短词匹配到其他单词内部。

别名只允许通过人工维护的映射加入，例如：

```text
FastAPI = Fast API
LLM = 大语言模型 = Large Language Model
Vector DB = Vector Database = 向量数据库
Tool Use = Tool Calling = Function Calling = 工具调用
```

以下关系不得自动视为等价：

- `PostgreSQL` 与 `MySQL`
- `Chroma` 与任意“向量数据库”能力
- `Go` 与 `Django`
- `ReAct` 与完整的 Planning、Memory、Reflection 能力

后续新增别名必须同时增加正向和反向测试，防止扩大误匹配范围。

## 7. V2 匹配算法

### 7.1 简历能力索引

匹配器先对 `resume.skills` 生成规范键集合，并保留“规范键 → 简历原始写法”的映射。

为了降低简历 LLM 漏提取造成的假阴性，对每个 JD 原子选项还可以在简历原文中执行一次带词边界的精确表面词检查。只有原子技能本身或已批准别名明确出现时才能补充命中，不做语义猜测。

### 7.2 单组选项计算

```text
matched_options = JD options 中能够在简历能力索引中找到的选项
missing_options = JD options - matched_options
```

状态规则：

```text
any + 至少命中一个     -> covered
any + 一个都未命中     -> missing
all + 全部命中         -> covered
all + 命中部分         -> partial
all + 一个都未命中     -> missing
```

### 7.3 评分

保持现有“必需技能 80%、加分技能 20%”的产品口径，但评分单位改为技能要求组：

```text
any 组覆盖率 = 命中任意选项时为 1，否则为 0
all 组覆盖率 = matched_options 数量 / options 数量
必需覆盖率   = 所有 required 组覆盖率的平均值
加分覆盖率   = 所有 preferred 组覆盖率的平均值
```

当岗位没有加分技能时，必需覆盖率直接换算为 100 分制。非评分要求不进入分母。

### 7.4 明确禁止的实现

- 禁止为 `Python` 或当前 JD 写条件分支。
- 禁止用 `if job_skill in resume_text` 进行无边界子串匹配。
- 禁止使用字符串相似度达到阈值就算匹配。
- 禁止把模型生成的规范键当作可信结果。
- 禁止为修复新报告而覆盖历史报告。

## 8. V2 匹配报告契约

新增要求级别的结果：

```python
class SkillOptionMatch(BaseModel):
    option: str
    matched_resume_skill: str | None
    resume_evidence: str | None


class RequirementMatch(BaseModel):
    label: str
    importance: Literal["required", "preferred"]
    match_mode: Literal["any", "all"]
    status: Literal["covered", "partial", "missing"]
    options: list[SkillOptionMatch]
    job_evidence: str
```

示例结果：

```json
{
  "label": "主流编程语言",
  "importance": "required",
  "match_mode": "any",
  "status": "covered",
  "options": [
    {
      "option": "Python",
      "matched_resume_skill": "Python",
      "resume_evidence": "编程语言：Python、SQL、TypeScript"
    },
    {
      "option": "TypeScript",
      "matched_resume_skill": "TypeScript",
      "resume_evidence": "编程语言：Python、SQL、TypeScript"
    },
    {
      "option": "Go",
      "matched_resume_skill": null,
      "resume_evidence": null
    }
  ],
  "job_evidence": "熟练掌握至少一门主流编程语言（Python/TypeScript/Go 等）"
}
```

`matched_skills`、`missing_skills` 和 `priority_skills` 暂时保留为兼容字段，由 V2 要求结果推导，避免本次改动直接破坏学习计划接口。

## 9. 数据库与历史兼容

采用新增字段的 Alembic 迁移，不改变已有 JSON 字段含义：

### 9.1 `job_requirements`

- 新增 `extraction_version`，旧数据标记为 `job-requirements-v1`。
- 新增 `skill_requirements` JSON，可空，用于保存 V2 技能要求组。
- 新增 `unscored_requirements` JSON，可空，用于保存非评分要求。

### 9.2 `match_reports`

- 新增 `requirement_matches` JSON，可空。
- 继续使用现有 `scoring_version`，新报告写入 `skill-coverage-v2`。
- V1 报告的新增字段保持为空，读取接口继续兼容。

兼容规则：

- 已有 V1 匹配报告保持不可变并可继续查看。
- V1 岗位分析不得继续生成已知不可靠的新报告；创建报告时返回明确的 `409`，提示重新分析岗位。
- 用户重新分析岗位后保存 V2 要求，再创建新的 V2 报告。
- 不自动改写、不猜测迁移旧的自然语言技能句子。
- 不删除当前测试数据。

## 10. 前端展示

匹配报告详情页按要求组展示：

- 已覆盖：绿色状态，列出具体命中的简历技能。
- 部分覆盖：显示已覆盖项和待补齐项。
- 尚未覆盖：显示缺失选项和 JD 原文证据。
- `any` 组明确显示“任意一项满足即可”。
- `all` 组明确显示“需要全部满足”。
- V1 历史报告显示“旧版匹配算法”提示，不伪装成 V2 结果。
- 分数旁继续显示“技能覆盖分不等于录用概率”的免责声明。

当前简历全部技能标签可以继续展示，但不能再代替要求级匹配解释。

## 11. 预计修改范围

后端主要文件：

- `app/schemas/requirements.py`
- `app/schemas/matching.py`
- `app/llm/prompts.py`
- `app/services/analysis.py`
- `app/services/skill_normalization.py`
- `app/services/matching.py`
- `app/services/match_report.py`
- `app/models/job_requirement.py`
- `app/models/match_report.py`
- `migrations/versions/`

前端主要文件：

- `frontend/src/types/api.ts`
- `frontend/src/pages/MatchReportsPage.tsx`
- 必要的匹配报告样式文件

测试主要文件：

- `tests/unit/test_job_analysis.py`
- `tests/unit/test_matching.py`
- `tests/unit/test_skill_normalization.py`，如果拆分出独立测试文件
- `tests/integration/test_job_requirements_api.py`
- `tests/integration/test_match_reports_api.py`
- `tests/integration/test_migrations.py`

本次不修改 `app/services/study_plan.py` 的任务生成策略。

## 12. 实施顺序

1. 增加能够稳定复现本次问题的失败测试。
2. 定义 V2 岗位要求和匹配报告 Schema。
3. 更新 JD 提取提示词与结果校验。
4. 扩展技能规范化器和经过批准的别名。
5. 实现 `any/all` 通用匹配算法和证据返回。
6. 增加 Alembic 迁移并验证旧数据库升级。
7. 更新匹配报告持久化和 API 契约。
8. 更新前端 V1/V2 报告展示。
9. 使用当前 Agent 开发工程师 JD 和测试简历完成浏览器主流程验证。
10. 完成后再单独设计学习计划 V2，不与本次修复混在同一提交中。

## 13. 测试矩阵

### 13.1 通用匹配

- 任意技能 `X` 两侧完全相同，结果为覆盖。
- 任意技能 `X` 只存在于 JD，结果为缺失。
- 任意未预先写入别名表的新技能，例如 `Temporal`，两侧相同时仍能匹配。
- 大小写、空格、点号、连字符不同但语义不变时匹配。
- 已批准别名能够匹配。
- 未批准的相关技能不能匹配。
- `Go` 不得匹配 `Django`。

### 13.2 组合要求

- `Python/TypeScript/Go` 为 `any`，简历有 Python 时覆盖。
- `Python/TypeScript/Go` 为 `any`，简历三个都没有时缺失。
- `Planning/Memory/Tool Use/Reflection` 为 `all`，只命中 Tool Use 时部分覆盖。
- `all` 组选项全部命中时覆盖。

### 13.3 证据和数据质量

- 每项岗位要求的证据能够在原始 JD 中找到。
- 匹配成功时返回实际命中的简历技能写法。
- 没有证据时不得伪造证据。
- 长句和多个技能的枚举不得作为单个 `option` 保存。
- 软能力不得进入技能覆盖分。

### 13.4 API、持久化与兼容

- V2 报告创建、保存、读取后结构一致。
- V1 历史报告仍可读取。
- V1 岗位要求创建新报告时返回要求重新分析的明确错误。
- 数据库从当前迁移头升级成功。
- 岗位、简历删除时原有级联规则不回归。

### 13.5 前端

- 正确展示覆盖、部分覆盖、缺失和双侧证据。
- `any/all` 规则对用户可见。
- V1 报告有旧版提示。
- 加载、空数据和错误状态不回归。

## 14. 验收标准

代码验收必须同时满足：

- 当前测试简历中的 `Python`、`TypeScript`、`Prompt Engineering` 能与 JD 中对应要求匹配。
- 报告不再把“熟练掌握至少一门……”等整句显示为单个技能。
- 相同技能的通用测试不依赖具体技能名称或当前测试简历。
- 简历不存在的技能仍然保持缺失，不因模糊相似而误匹配。
- 每项结果能够解释命中的 JD 要求、简历技能和匹配规则。
- 新报告使用 `skill-coverage-v2`，旧报告不被覆盖。
- Alembic 升级、后端测试、Ruff、前端 ESLint 和 TypeScript 构建全部通过。
- 使用浏览器完成“重新分析岗位 → 创建新报告 → 查看解释”的真实主流程验证。

## 15. 风险与控制

- LLM 再次输出长句：通过 V2 Schema、原子技能约束和持久化前校验阻止错误结果入库。
- 别名过度扩张：只维护明确批准的等价关系，并为每条关系添加反例测试。
- 原文直接匹配产生子串误判：统一使用带词边界的表面词检查。
- 新旧结构混用：通过 `extraction_version` 和 `scoring_version` 明确分流。
- 历史数据被误改：采用新增字段迁移，旧报告只读，不自动转换。
- 修复范围扩散到学习计划：本次只保证 `priority_skills` 来源正确，任务生成质量留给独立迭代。

本方案不通过增加某个关键词解决症状，而是统一 JD 与简历的技能表达、组合关系、规范化和证据边界，从数据入口消除假阴性匹配。
