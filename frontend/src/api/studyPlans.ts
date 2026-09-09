import { apiRequest, longOperation } from './client'
import type { StudyPlan, StudyTask, StudyTaskStatus } from '../types/api'

export const studyPlansApi = {
  list: (filters: { matchReportId?: number } = {}) => {
    const query = new URLSearchParams()
    if (filters.matchReportId) query.set('match_report_id', String(filters.matchReportId))
    const suffix = query.size ? `?${query}` : ''
    return apiRequest<StudyPlan[]>(`/study-plans${suffix}`)
  },
  get: (planId: number) => apiRequest<StudyPlan>(`/study-plans/${planId}`),
  create: (matchReportId: number, deadline: string | null) =>
    apiRequest<StudyPlan>('/study-plans', {
      method: 'POST',
      body: { match_report_id: matchReportId, deadline: deadline || null },
      ...longOperation,
    }),
  updateTask: (taskId: number, status: StudyTaskStatus) =>
    apiRequest<StudyTask>(`/study-tasks/${taskId}`, {
      method: 'PATCH',
      body: { status },
    }),
}
