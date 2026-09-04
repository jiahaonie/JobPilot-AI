import {
  analysisStatusLabels,
  jobStatusLabels,
  planStatusLabels,
  taskStatusLabels,
  type AnalysisStatus,
  type JobStatus,
  type StudyPlanStatus,
  type StudyTaskStatus,
} from '../../types/api'

type Status = AnalysisStatus | JobStatus | StudyPlanStatus | StudyTaskStatus

const labels: Record<Status, string> = {
  ...analysisStatusLabels,
  ...jobStatusLabels,
  ...planStatusLabels,
  ...taskStatusLabels,
}

export function StatusBadge({ status }: { status: Status | null }) {
  if (!status) return <span className="status-badge neutral">未开始</span>
  return <span className={`status-badge ${status}`}>{labels[status]}</span>
}

export function SkillTags({ skills, empty = '暂无' }: { skills: string[]; empty?: string }) {
  if (!skills.length) return <span className="muted">{empty}</span>
  return (
    <div className="tag-list">
      {skills.map((skill) => <span className="skill-tag" key={skill}>{skill}</span>)}
    </div>
  )
}
