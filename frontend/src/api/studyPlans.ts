import { apiRequest } from './client'
import type { StudyPlan, StudyTask, StudyTaskStatus } from '../types/api'

export const studyPlansApi = {
  list: () => apiRequest<StudyPlan[]>('/study-plans'),
  get: (planId: number) => apiRequest<StudyPlan>(`/study-plans/${planId}`),
  create: (matchReportId: number, deadline: string | null) =>
    apiRequest<StudyPlan>('/study-plans', {
      method: 'POST',
      body: { match_report_id: matchReportId, deadline: deadline || null },
    }),
  updateTask: (taskId: number, status: StudyTaskStatus) =>
    apiRequest<StudyTask>(`/study-tasks/${taskId}`, {
      method: 'PATCH',
      body: { status },
    }),
}
