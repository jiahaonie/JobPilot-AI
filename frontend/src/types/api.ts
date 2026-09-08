export type JobStatus =
  | 'preparing'
  | 'applied'
  | 'contacted'
  | 'interview'
  | 'closed'

export type AnalysisStatus = 'pending' | 'analyzing' | 'ready' | 'failed'
export type StudyTaskPhase = 'learn' | 'practice' | 'verify'
export type StudyTaskStatus = 'todo' | 'in_progress' | 'done'
export type StudyPlanStatus = 'not_started' | 'in_progress' | 'completed'
export type RequirementImportance = 'required' | 'preferred'
export type MatchMode = 'any' | 'all'
export type RequirementMatchStatus = 'covered' | 'partial' | 'missing'

export interface Job {
  id: number
  company_name: string
  job_title: string
  city: string | null
  internship_duration: string | null
  raw_text: string
  source_url: string | null
  status: JobStatus | null
  resume_id: number | null
  analysis_status: AnalysisStatus
  analysis_error: string | null
  analyzed_at: string | null
  created_at: string
  updated_at: string
}

export interface JobCreate {
  company_name: string
  job_title: string
  city?: string | null
  internship_duration?: string | null
  raw_text: string
  source_url?: string | null
}

export interface ResumeSummary {
  id: number
  title: string
  skills: string[]
  analysis_status: AnalysisStatus
  analysis_error: string | null
  analyzed_at: string | null
  created_at: string
}

export interface Resume extends ResumeSummary {
  raw_text: string
}

export interface JobRequirement {
  job_title: string
  extraction_version: string
  skill_requirements: SkillRequirement[]
  unscored_requirements: UnscoredRequirement[]
  required_skills: string[]
  preferred_skills: string[]
  education: string | null
  internship_duration: string | null
  responsibilities: string[]
  evidence: string[]
}

export interface SkillRequirement {
  label: string
  importance: RequirementImportance
  match_mode: MatchMode
  options: string[]
  evidence: string
}

export interface UnscoredRequirement {
  category: 'experience' | 'education' | 'soft_skill' | 'other'
  text: string
  evidence: string
}

export interface SkillGap {
  skill: string
  evidence: string | null
}

export interface SkillOptionMatch {
  option: string
  matched_resume_skill: string | null
  resume_evidence: string | null
}

export interface RequirementMatch {
  label: string
  importance: RequirementImportance
  match_mode: MatchMode
  status: RequirementMatchStatus
  options: SkillOptionMatch[]
  job_evidence: string
}

export interface MatchReport {
  id: number
  job_id: number
  resume_id: number
  skill_coverage_score: number | null
  required_score: number | null
  preferred_score: number | null
  score_disclaimer: string
  matched_skills: string[]
  bonus_skills: string[]
  missing_skills: SkillGap[]
  priority_skills: SkillGap[]
  requirement_matches: RequirementMatch[] | null
  required_skills_snapshot: string[]
  preferred_skills_snapshot: string[]
  resume_skills_snapshot: string[]
  job_requirement_updated_at: string
  resume_analyzed_at: string | null
  scoring_version: string
  created_at: string
}

export interface StudyTask {
  id: number
  study_plan_id: number
  skill: string
  phase: StudyTaskPhase
  title: string
  completion_criteria: string
  resource_query: string
  position: number
  status: StudyTaskStatus
  due_date: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface StudyPlan {
  id: number
  match_report_id: number
  deadline: string | null
  generation_method: string
  status: StudyPlanStatus
  completed_count: number
  task_count: number
  tasks: StudyTask[]
  created_at: string
  updated_at: string
}

export const analysisStatusLabels: Record<AnalysisStatus, string> = {
  pending: '待分析',
  analyzing: '分析中',
  ready: '已完成',
  failed: '失败',
}

export const jobStatusLabels: Record<JobStatus, string> = {
  preparing: '准备中',
  applied: '已投递',
  contacted: '已联系',
  interview: '面试中',
  closed: '已结束',
}

export const taskStatusLabels: Record<StudyTaskStatus, string> = {
  todo: '待开始',
  in_progress: '进行中',
  done: '已完成',
}

export const taskPhaseLabels: Record<StudyTaskPhase, string> = {
  learn: '学习',
  practice: '实践',
  verify: '验证',
}

export const planStatusLabels: Record<StudyPlanStatus, string> = {
  not_started: '未开始',
  in_progress: '进行中',
  completed: '已完成',
}
