import { apiRequest, longOperation } from './client'
import type { Job, JobCreate, JobRequirement, JobStatus, JobUpdate, MatchReport } from '../types/api'

export const jobsApi = {
  list: () => apiRequest<Job[]>('/jobs'),
  get: (jobId: number) => apiRequest<Job>(`/jobs/${jobId}`),
  create: (payload: JobCreate) =>
    apiRequest<Job>('/jobs', { method: 'POST', body: payload }),
  update: (jobId: number, payload: JobUpdate) =>
    apiRequest<Job>(`/jobs/${jobId}`, { method: 'PATCH', body: payload }),
  remove: (jobId: number) => apiRequest<void>(`/jobs/${jobId}`, { method: 'DELETE' }),
  bindResume: (jobId: number, resumeId: number) =>
    apiRequest<Job>(`/jobs/${jobId}/resume`, {
      method: 'PUT',
      body: { resume_id: resumeId },
    }),
  unbindResume: (jobId: number) =>
    apiRequest<void>(`/jobs/${jobId}/resume`, { method: 'DELETE' }),
  analyze: (jobId: number) =>
    apiRequest<JobRequirement>(`/jobs/${jobId}/analyze`, {
      method: 'POST',
      ...longOperation,
    }),
  getRequirements: (jobId: number) =>
    apiRequest<JobRequirement>(`/jobs/${jobId}/requirements`),
  prepare: (jobId: number) =>
    apiRequest<Job>(`/jobs/${jobId}/prepare`, { method: 'POST' }),
  updateStatus: (jobId: number, status: JobStatus) =>
    apiRequest<Job>(`/jobs/${jobId}/status`, {
      method: 'PATCH',
      body: { status },
    }),
  createReport: (jobId: number, resumeId: number) =>
    apiRequest<MatchReport>(`/jobs/${jobId}/match-reports`, {
      method: 'POST',
      body: { resume_id: resumeId },
    }),
}
