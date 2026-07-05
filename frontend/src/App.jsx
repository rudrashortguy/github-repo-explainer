import { lazy, Suspense, useState, useMemo, useCallback } from 'react'
import axios from 'axios'
import JSZip from 'jszip'

const MermaidView = lazy(() => import('./MermaidView'))
const MarkdownView = lazy(() => import('./MarkdownView'))

function App() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [report, setReport] = useState(null)
  const [tab, setTab] = useState('mermaid')

  const explain = useCallback(async () => {
    if (!url.trim()) return
    setLoading(true)
    setReport(null)
    try {
      const { data } = await axios.post('http://localhost:8000/explain', { repo_url: url })
      setReport(data)
    } catch (e) {
      alert('Error: ' + (e.response?.data?.detail || e.message))
    } finally {
      setLoading(false)
    }
  }, [url])

  const download = useCallback(async () => {
    if (!report) return
    const zip = new JSZip()
    zip.file('report.json', JSON.stringify(report, null, 2))
    for (const [folder, desc] of Object.entries(report.folder_explanations || {})) {
      zip.file(`folders/${folder.replace(/[/\\]/g, '_')}.md`, desc)
    }
    const blob = await zip.generateAsync({ type: 'blob' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'repo-report.zip'
    a.click()
  }, [report])

  const tabContent = useMemo(() => {
    if (!report) return null
    const fallback = <div className="animate-pulse h-40 bg-gray-100 rounded" />
    switch (tab) {
      case 'mermaid':
        return <Suspense fallback={fallback}><MermaidView definition={report.architecture_mermaid} /></Suspense>
      case 'folders':
        return (
          <div className="space-y-4">
            {Object.entries(report.folder_explanations || {}).map(([path, desc]) => (
              <div key={path}>
                <h3 className="font-semibold text-lg">{path}</h3>
                <Suspense fallback={fallback}><MarkdownView content={desc} /></Suspense>
              </div>
            ))}
          </div>
        )
      case 'endpoints':
        return (
          <ul className="list-disc pl-5 space-y-1">
            {(report.api_endpoints_guessed || []).map((ep, i) => (
              <li key={i}><code className="bg-gray-100 px-1 rounded">{ep}</code></li>
            ))}
          </ul>
        )
      case 'readme':
        return <Suspense fallback={fallback}><MarkdownView content={report.readme_summary} /></Suspense>
      case 'contributing':
        return <Suspense fallback={fallback}><MarkdownView content={report.contribution_guide} /></Suspense>
      default:
        return null
    }
  }, [report, tab])

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">GitHub Repo Explainer</h1>

      <div className="flex gap-2 mb-8">
        <input
          className="flex-1 border rounded px-4 py-2"
          placeholder="https://github.com/user/repo"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && explain()}
        />
        <button
          className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          onClick={explain}
          disabled={loading}
        >
          {loading ? 'Analyzing...' : 'Explain'}
        </button>
      </div>

      {loading && (
        <div className="flex justify-center py-12">
          <div className="animate-spin h-10 w-10 border-4 border-blue-500 border-t-transparent rounded-full" />
        </div>
      )}

      {report && (
        <>
          <div className="flex gap-2 mb-4 flex-wrap">
            {['mermaid', 'folders', 'endpoints', 'readme', 'contributing'].map((t) => (
              <button
                key={t}
                className={`px-4 py-1 rounded ${tab === t ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
                onClick={() => setTab(t)}
              >
                {t === 'mermaid' ? 'Architecture' : t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
            <button className="ml-auto bg-green-600 text-white px-4 py-1 rounded hover:bg-green-700" onClick={download}>
              Download Report
            </button>
          </div>

          <div className="bg-white rounded-lg shadow p-6 min-h-[400px]">
            {tabContent}
          </div>

          {report.tech_stack_badges?.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {report.tech_stack_badges.map((b, i) => (
                <span key={i} className="bg-gray-200 text-sm px-3 py-1 rounded-full">{b}</span>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default App
