"""持久化层枚举。"""

from enum import StrEnum


class JobStatus(StrEnum):
    """岗位进入投递流程后的汇总阶段。"""

    PREPARING = "preparing"
    APPLIED = "applied"
    CONTACTED = "contacted"
    INTERVIEW = "interview"
    CLOSED = "closed"


class DocumentStatus(StrEnum):
    """跨 SQLite 与向量存储的索引生命周期。"""

    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"
    DELETING = "deleting"


class ResumeAnalysisStatus(StrEnum):
    """单份已保存简历的 LLM 技能提取生命周期。"""

    PENDING = "pending"
    ANALYZING = "analyzing"
    READY = "ready"
    FAILED = "failed"


class JobAnalysisStatus(StrEnum):
    """单个岗位描述的 LLM 分析生命周期。"""

    PENDING = "pending"
    ANALYZING = "analyzing"
    READY = "ready"
    FAILED = "failed"


class StudyTaskPhase(StrEnum):
    """规则生成的学习任务阶段。"""

    LEARN = "learn"
    PRACTICE = "practice"
    VERIFY = "verify"


class StudyTaskStatus(StrEnum):
    """用户手动维护的学习任务状态。"""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class StudyPlanStatus(StrEnum):
    """根据所属任务动态计算的学习计划状态。"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
