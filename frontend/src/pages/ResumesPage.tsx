import { useCallback, useState } from 'react'
import { resumesApi } from '../api/resumes'
import { AppLink, navigate } from '../app/router'
import { EmptyState, ErrorState, InlineMessage, LoadingState } from '../components/feedback/PageState'
import { SkillTags, StatusBadge } from '../components/ui/StatusBadge'
import { useAsyncResource } from '../hooks/useAsyncResource'
import { formatDate } from '../utils/format'

const SUPPORTED_SUFFIXES = ['.txt', '.md', '.markdown', '.pdf']
const MAX_FILE_BYTES = 5 * 1024 * 1024

export function ResumesPage() {
  const loader = useCallback(() => resumesApi.list(), [])
  const resource = useAsyncResource(loader)
  const [title, setTitle] = useState('')
  const [rawText, setRawText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [mode, setMode] = useState<'upload' | 'text'>('upload')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    if (mode === 'upload') {
      if (!file) return setError('请选择一份简历文件')
      const suffix = `.${file.name.split('.').at(-1)?.toLowerCase()}`
      if (!SUPPORTED_SUFFIXES.includes(suffix)) return setError('仅支持 TXT、Markdown 和电子 PDF')
      if (file.size > MAX_FILE_BYTES) return setError('文件不能超过 5 MB')
    } else if (!rawText.trim()) return setError('简历原文不能为空')

    setSubmitting(true)
    try {
      const resume = mode === 'upload'
        ? await resumesApi.upload(file!, title)
        : await resumesApi.create(title, rawText)
      navigate(`/resumes/${resume.id}`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <div className="page-heading"><div><p className="eyebrow">候选人资料</p><h1>简历</h1><p>上传后需要显式触发技能分析。</p></div></div>
      <section className="panel form-panel compact-form">
        <div className="tabs" role="tablist"><button className={mode === 'upload' ? 'active' : ''} onClick={() => setMode('upload')}>上传文件</button><button className={mode === 'text' ? 'active' : ''} onClick={() => setMode('text')}>粘贴文本</button></div>
        <form onSubmit={submit}>
          {error && <InlineMessage kind="error">{error}</InlineMessage>}
          <label><span>简历标题（可选）</span><input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={200} /></label>
          {mode === 'upload' ? (
            <label className="file-input"><span>简历文件 *</span><input type="file" accept=".txt,.md,.markdown,.pdf" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /><small>支持 UTF-8 TXT、Markdown、电子 PDF，最大 5 MB；扫描 PDF 暂不支持。</small></label>
          ) : (
            <label><span>简历原文 * <small>{rawText.length.toLocaleString()}/100,000</small></span><textarea rows={9} maxLength={100000} value={rawText} onChange={(event) => setRawText(event.target.value)} /></label>
          )}
          <button className="button primary" disabled={submitting}>{submitting ? '正在保存…' : '保存简历'}</button>
        </form>
      </section>

      <div className="section-heading standalone"><div><p className="eyebrow">已保存</p><h2>简历列表</h2></div></div>
      {resource.loading ? <LoadingState /> : resource.error ? <ErrorState error={resource.error} onRetry={resource.reload} /> : !resource.data?.length ? (
        <EmptyState title="还没有简历" description="上传文件或粘贴文本创建第一份简历。" />
      ) : (
        <div className="card-grid">
          {resource.data.map((resume) => (
            <article className="entity-card" key={resume.id}>
              <div className="card-topline"><span>#{resume.id}</span><StatusBadge status={resume.analysis_status} /></div>
              <h2><AppLink to={`/resumes/${resume.id}`}>{resume.title}</AppLink></h2>
              <SkillTags skills={resume.skills.slice(0, 6)} empty="尚未提取技能" />
              <small className="muted">创建于 {formatDate(resume.created_at)}</small>
              <div className="card-actions"><AppLink className="button secondary" to={`/resumes/${resume.id}`}>查看与分析</AppLink></div>
            </article>
          ))}
        </div>
      )}
    </>
  )
}
