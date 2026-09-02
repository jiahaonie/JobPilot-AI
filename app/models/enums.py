"""持久化层枚举。"""

from enum import StrEnum


class JobStatus(StrEnum):
    """项目计划定义的投递状态值。"""

    PENDING_ANALYSIS = "pending_analysis"
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
