import { apiRequest } from './client'
import type { MatchReport } from '../types/api'

export const matchReportsApi = {
  list: (filters: { jobId?: number; resumeId?: number } = {}) => {
    const params = new URLSearchParams()
    if (filters.jobId) params.set('job_id', String(filters.jobId))
    if (filters.resumeId) params.set('resume_id', String(filters.resumeId))
    const query = params.size ? `?${params.toString()}` : ''
    return apiRequest<MatchReport[]>(`/match-reports${query}`)
  },
  get: (reportId: number) => apiRequest<MatchReport>(`/match-reports/${reportId}`),
}
