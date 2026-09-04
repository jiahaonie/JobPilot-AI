import { apiRequest, longOperation } from './client'
import type { Resume, ResumeSummary } from '../types/api'

export const resumesApi = {
  list: () => apiRequest<ResumeSummary[]>('/resumes'),
  get: (resumeId: number) => apiRequest<Resume>(`/resumes/${resumeId}`),
  create: (title: string, rawText: string) =>
    apiRequest<Resume>('/resumes', {
      method: 'POST',
      body: { title: title || null, raw_text: rawText },
    }),
  upload: (file: File, title: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (title.trim()) formData.append('title', title.trim())
    return apiRequest<Resume>('/resumes/upload', { method: 'POST', body: formData })
  },
  analyze: (resumeId: number) =>
    apiRequest<Resume>(`/resumes/${resumeId}/analyze`, {
      method: 'POST',
      ...longOperation,
    }),
  remove: (resumeId: number) =>
    apiRequest<void>(`/resumes/${resumeId}`, { method: 'DELETE' }),
}
