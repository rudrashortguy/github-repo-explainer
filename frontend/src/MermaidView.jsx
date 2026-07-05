import { useEffect, useRef, useState } from 'react'
import mermaid from 'mermaid'

mermaid.initialize({ startOnLoad: false })

export default function MermaidView({ definition }) {
  const ref = useRef(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!ref.current || !definition) return
    setError(null)
    ref.current.innerHTML = definition
    mermaid.run({ nodes: [ref.current] }).catch((e) => {
      setError('Failed to render diagram: ' + e.message)
    })
  }, [definition])

  if (error) {
    return (
      <div className="border border-red-300 bg-red-50 rounded p-4 text-red-700">
        <p className="font-semibold">Diagram Error</p>
        <p className="text-sm mt-1">{error}</p>
        <pre className="mt-2 text-xs bg-white p-2 rounded overflow-auto max-h-60">{definition}</pre>
      </div>
    )
  }

  return <div ref={ref} className="mermaid overflow-auto" />
}
