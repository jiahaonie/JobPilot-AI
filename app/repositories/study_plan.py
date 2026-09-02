"""学习计划持久化操作。"""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.match_report import MatchReportRow
from app.models.study_plan import StudyPlan


class StudyPlanRepository:
    """保存并查询绑定不可变匹配报告的学习计划。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, plan: StudyPlan) -> StudyPlan:
        """暂存计划及其任务并填充数据库生成字段。"""
        self.session.add(plan)
        self.session.flush()
        return plan

    def get(self, plan_id: int) -> StudyPlan | None:
        """按主键读取计划及其有序任务。"""
        statement = (
            select(StudyPlan)
            .options(selectinload(StudyPlan.tasks))
            .where(StudyPlan.id == plan_id)
        )
        return self.session.scalar(statement)

    def get_by_match_report(self, match_report_id: int) -> StudyPlan | None:
        """读取指定匹配报告已经创建的学习计划。"""
        statement = (
            select(StudyPlan)
            .options(selectinload(StudyPlan.tasks))
            .where(StudyPlan.match_report_id == match_report_id)
        )
        return self.session.scalar(statement)

    def list(
        self,
        *,
        job_id: int | None = None,
        resume_id: int | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[StudyPlan]:
        """按可选岗位和简历筛选学习计划。"""
        statement = select(StudyPlan).join(
            MatchReportRow,
            StudyPlan.match_report_id == MatchReportRow.id,
        )
        if job_id is not None:
            statement = statement.where(MatchReportRow.job_id == job_id)
        if resume_id is not None:
            statement = statement.where(MatchReportRow.resume_id == resume_id)
        statement = (
            statement.options(selectinload(StudyPlan.tasks))
            .order_by(StudyPlan.created_at.desc(), StudyPlan.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def delete(self, plan: StudyPlan) -> None:
        """暂存学习计划删除，任务由数据库级联删除。"""
        self.session.delete(plan)
