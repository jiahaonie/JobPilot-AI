"""学习任务持久化操作。"""

from sqlalchemy.orm import Session

from app.models.study_task import StudyTask


class StudyTaskRepository:
    """按主键读取规则生成的学习任务。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, task_id: int) -> StudyTask | None:
        """按主键读取学习任务。"""
        return self.session.get(StudyTask, task_id)
