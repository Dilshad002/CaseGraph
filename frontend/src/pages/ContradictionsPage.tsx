import { useState } from 'react'
import { AlertTriangle, ChevronDown, ChevronUp, Search } from 'lucide-react'
import axios from 'axios'

const API = 'http://localhost:8000'

interface Contradiction {
  type: string
  attribute?: string
  relation?: string
  conflict: Record<string, any>
  supporting_spans?: { fir: string; span: string }[]
  date?: string
}

interface ContradictionResult {
  entity: string
  appears_in: { fir_number: string; filename: string }[]
  contradictions: Contradiction[]
}

export default function ContradictionsPage() {
  const [entity, setEntity] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ContradictionResult | null>(null)
  const [expanded, setExpanded] = useState<number | null>(null)

  const search = async () => {
    if (!entity.trim()) return
    setLoading(true)
    setResult(null)
    try {
      const res = await axios.get(`${API}/contradict`, { params: { entity } })
      setResult(res.data)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <p className="text-[#7A7F8E] font-mono text-xs uppercase tracking-widest mb-1">Cross-FIR Analysis</p>
        <h1 className="text-2xl font-semibold text-[#E8EAF0]">Contradiction Detection</h1>
      </div>

      {/* Search */}
      <div className="flex gap-3 mb-8">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#7A7F8E]" size={16} />
          <input
            className="w-full bg-[#161920] border border-[#2A2D35] rounded-lg pl-9 pr-4 py-2.5 text-sm text-[#E8EAF0] placeholder:text-[#7A7F8E] focus:outline-none focus:border-[#4F8EF7] font-mono"
            placeholder="Enter entity name e.g. Vikram Reddy"
            value={entity}
            onChange={e => setEntity(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && search()}
          />
        </div>
        <button
          onClick={search}
          disabled={loading}
          className="px-4 py-2.5 bg-[#4F8EF7] hover:bg-[#4F8EF7]/80 text-white text-sm font-mono rounded-lg transition-colors disabled:opacity-50"
        >
          {loading ? 'Searching...' : 'Detect'}
        </button>
      </div>

      {result && (
        <div className="space-y-4">
          {/* Appears in */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-[#7A7F8E] font-mono">Appears in:</span>
            {result.appears_in.map(a => (
              <span key={a.fir_number} className="font-mono text-xs bg-[#2A2D35] text-[#E8EAF0] px-2 py-1 rounded">
                FIR {a.fir_number}
              </span>
            ))}
          </div>

          {result.contradictions.length === 0 ? (
            <div className="bg-[#161920] border border-[#2A2D35] rounded-lg p-8 text-center">
              <p className="text-[#7A7F8E] text-sm">No contradictions detected across {result.appears_in.length} FIR{result.appears_in.length !== 1 ? 's' : ''}.</p>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="text-[#E05252]" size={16} />
                <span className="text-[#E05252] font-mono text-sm">{result.contradictions.length} contradiction{result.contradictions.length !== 1 ? 's' : ''} detected</span>
              </div>

              {result.contradictions.map((c, i) => (
                <div key={i} className="bg-[#161920] border border-[#E05252]/30 rounded-xl overflow-hidden">
                  {/* Header */}
                  <button
                    className="w-full flex items-center justify-between p-4 text-left"
                    onClick={() => setExpanded(expanded === i ? null : i)}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-[#E05252] font-mono text-xs bg-[#E05252]/10 px-2 py-1 rounded uppercase">
                        {c.type === 'attribute_conflict' ? `${c.attribute} mismatch` :
                         c.type === 'relation_conflict' ? `${c.relation} conflict` :
                         'temporal-spatial conflict'}
                      </span>
                      {c.date && <span className="text-[#7A7F8E] font-mono text-xs">{c.date}</span>}
                    </div>
                    {expanded === i ? <ChevronUp size={16} className="text-[#7A7F8E]" /> : <ChevronDown size={16} className="text-[#7A7F8E]" />}
                  </button>

                  {/* Expanded content */}
                  {expanded === i && (
                    <div className="border-t border-[#2A2D35] p-4 space-y-4">
                      {/* Split view */}
                      <div className="grid grid-cols-2 gap-3">
                        {Object.entries(c.conflict).map(([fir, value]) => (
                          <div key={fir} className="bg-[#0D0F12] border border-[#2A2D35] rounded-lg p-3">
                            <p className="font-mono text-xs text-[#7A7F8E] mb-2">FIR {fir}</p>
                            {typeof value === 'string' ? (
                              <p className="text-sm text-[#E8EAF0]">{value}</p>
                            ) : (
                              <div className="space-y-1">
                                {Object.entries(value as Record<string, string>).map(([k, v]) => (
                                  <p key={k} className="text-sm text-[#E8EAF0]"><span className="text-[#7A7F8E]">{k}:</span> {v}</p>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>

                      {/* Source spans */}
                      {c.supporting_spans && c.supporting_spans.length > 0 && (
                        <div>
                          <p className="text-xs font-mono text-[#7A7F8E] uppercase tracking-widest mb-2">Source Evidence</p>
                          {c.supporting_spans.map((s, j) => (
                            <div key={j} className="border-l-2 border-[#4F8EF7]/40 pl-3 mb-2">
                              <p className="font-mono text-xs text-[#4F8EF7] mb-1">FIR {s.fir}</p>
                              <p className="text-xs text-[#7A7F8E] italic">"{s.span}"</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  )
}