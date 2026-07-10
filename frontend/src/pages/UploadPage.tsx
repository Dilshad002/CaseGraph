import { useState, useCallback } from 'react'
import { Upload, FileText, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import axios from 'axios'
import { useApp } from '../store/AppContext'

const API = 'http://localhost:8000'

type Status = 'idle' | 'uploading' | 'success' | 'error'

interface ExtractionResult {
  filename: string
  fir_number?: string
  entities: { text: string; type: string }[]
  regex_entities: Record<string, string | string[]>
  relationships: { subject: string; relation: string; object: string }[]
}

export default function UploadPage() {
  const { lastUpload, setLastUpload } = useApp()
  const [result, setResult] = useState<ExtractionResult | null>(lastUpload)
  const [status, setStatus] = useState<Status>(lastUpload ? 'success' : 'idle')
  const [error, setError] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  

  const upload = async (file: File) => {
    setStatus('uploading')
    setResult(null)
    setError(null)
    const form = new FormData()
    form.append('file', file)
    try {
      const res = await axios.post(`${API}/extract`, form)
      setResult(res.data)
      setLastUpload(res.data)
      setStatus('success')
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Upload failed')
      setStatus('error')
    }
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) upload(file)
  }, [])

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) upload(file)
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <p className="text-[#7A7F8E] font-mono text-xs uppercase tracking-widest mb-1">Evidence Ingestion</p>
        <h1 className="text-2xl font-semibold text-[#E8EAF0]">Upload Document</h1>
      </div>

      {/* Drop zone */}
      <label
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`flex flex-col items-center justify-center w-full h-48 border-2 border-dashed rounded-xl cursor-pointer transition-all ${
          dragging
            ? 'border-[#4F8EF7] bg-[#4F8EF7]/5'
            : 'border-[#2A2D35] bg-[#161920] hover:border-[#4F8EF7]/50'
        }`}
      >
        <input type="file" accept=".pdf,.png,.jpg,.jpeg" className="hidden" onChange={onFileChange} />
        {status === 'uploading' ? (
          <Loader2 className="animate-spin text-[#4F8EF7]" size={32} />
        ) : (
          <>
            <Upload className="text-[#7A7F8E] mb-3" size={32} />
            <p className="text-[#7A7F8E] text-sm">Drop PDF or image here, or <span className="text-[#4F8EF7]">browse</span></p>
            <p className="text-[#7A7F8E] text-xs mt-1 font-mono">FIR · Witness Statement · Police Report</p>
          </>
        )}
      </label>

      {/* Error */}
      {status === 'error' && (
        <div className="mt-4 flex items-center gap-2 text-[#E05252] bg-[#E05252]/10 border border-[#E05252]/20 rounded-lg p-3">
          <AlertCircle size={16} />
          <span className="text-sm font-mono">{error}</span>
        </div>
      )}

      {/* Results */}
      {status === 'success' && result && (
        <div className="mt-6 space-y-4">
          {/* Header */}
          <div className="flex items-center gap-3">
            <CheckCircle className="text-[#4CAF84]" size={18} />
            <span className="font-mono text-sm text-[#4CAF84]">Extraction complete</span>
            {result.regex_entities?.fir_number && (
              <span className="ml-auto font-mono text-xs text-[#7A7F8E] bg-[#2A2D35] px-2 py-1 rounded">
                FIR {result.regex_entities.fir_number as string}
              </span>
            )}
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'Entities', value: result.entities.length },
              { label: 'Relationships', value: result.relationships.length },
              { label: 'Identifiers', value: Object.values(result.regex_entities).filter(v => v && (Array.isArray(v) ? v.length > 0 : v)).length },
            ].map(({ label, value }) => (
              <div key={label} className="bg-[#161920] border border-[#2A2D35] rounded-lg p-4">
                <p className="text-3xl font-mono font-bold text-[#E8EAF0]">{value}</p>
                <p className="text-xs text-[#7A7F8E] mt-1">{label} extracted</p>
              </div>
            ))}
          </div>

          {/* Relationships */}
          {result.relationships.length > 0 && (
            <div className="bg-[#161920] border border-[#2A2D35] rounded-lg p-4">
              <p className="text-xs font-mono text-[#7A7F8E] uppercase tracking-widest mb-3">Relationships</p>
              <div className="space-y-2">
                {result.relationships.map((r, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    <span className="text-[#E8EAF0] font-medium">{r.subject}</span>
                    <span className="text-[#4F8EF7] font-mono text-xs bg-[#4F8EF7]/10 px-2 py-0.5 rounded">{r.relation}</span>
                    <span className="text-[#E8EAF0] font-medium">{r.object}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Entities */}
          <div className="bg-[#161920] border border-[#2A2D35] rounded-lg p-4">
            <p className="text-xs font-mono text-[#7A7F8E] uppercase tracking-widest mb-3">Entities</p>
            <div className="flex flex-wrap gap-2">
              {result.entities
                .filter(e => ['person', 'location', 'organization'].includes(e.type))
                .map((e, i) => (
                  <span key={i} className={`text-xs font-mono px-2 py-1 rounded border ${
                    e.type === 'person' ? 'border-[#4F8EF7]/30 text-[#4F8EF7] bg-[#4F8EF7]/5' :
                    e.type === 'location' ? 'border-[#4CAF84]/30 text-[#4CAF84] bg-[#4CAF84]/5' :
                    'border-[#7A7F8E]/30 text-[#7A7F8E] bg-[#7A7F8E]/5'
                  }`}>
                    {e.text}
                  </span>
                ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}