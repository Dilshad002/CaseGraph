import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Database, MessageSquare } from 'lucide-react'
import api from '../lib/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
  cypher?: string
  sources?: string[]
  results?: any[]
}

export default function QueryPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async () => {
    if (!input.trim() || loading) return
    const userMsg: Message = { role: 'user', content: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await api.get(`/query`, { params: { question: input } })
      const data = res.data
      const assistantMsg: Message = {
        role: 'assistant',
        content: data.answer || data.message || 'No answer returned.',
        cypher: data.cypher,
        sources: data.sources || [],
        results: data.results || [],
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Query failed. Check that the backend is running.',
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-8 py-6 border-b border-[#2A2D35]">
        <p className="text-[#7A7F8E] font-mono text-xs uppercase tracking-widest mb-1">Investigation Assistant</p>
        <h1 className="text-2xl font-semibold text-[#E8EAF0]">Query the Graph</h1>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-8 py-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
            <MessageSquare className="text-[#2A2D35]" size={48} />
            <div>
              <p className="text-[#7A7F8E] text-sm mb-3">Ask anything about the uploaded FIRs</p>
              <div className="flex flex-wrap gap-2 justify-center">
                {[
                  'Who are all accused persons?',
                  'What vehicles are linked to Vikram Reddy?',
                  'Which phone numbers appear in multiple FIRs?',
                  'Summarize FIR 145/2026',
                ].map(q => (
                  <button
                    key={q}
                    onClick={() => setInput(q)}
                    className="text-xs font-mono px-3 py-1.5 bg-[#161920] border border-[#2A2D35] text-[#7A7F8E] rounded-lg hover:border-[#4F8EF7]/50 hover:text-[#E8EAF0] transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-2xl ${msg.role === 'user' ? 'ml-12' : 'mr-12'}`}>
              {msg.role === 'user' ? (
                <div className="bg-[#4F8EF7]/10 border border-[#4F8EF7]/20 rounded-xl px-4 py-3">
                  <p className="text-sm text-[#E8EAF0]">{msg.content}</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {/* Answer */}
                  <div className="bg-[#161920] border border-[#2A2D35] rounded-xl px-4 py-3">
                    <p className="text-sm text-[#E8EAF0] leading-relaxed">{msg.content}</p>
                  </div>

                  {/* Cypher — source attribution */}
                  {msg.cypher && (
                    <div className="bg-[#0D0F12] border border-[#2A2D35] rounded-lg px-4 py-3">
                      <div className="flex items-center gap-2 mb-2">
                        <Database size={12} className="text-[#4F8EF7]" />
                        <span className="text-[10px] font-mono text-[#7A7F8E] uppercase tracking-widest">Graph Query</span>
                      </div>
                      <code className="text-xs text-[#4F8EF7] font-mono whitespace-pre-wrap">{msg.cypher}</code>
                    </div>
                  )}

                  {/* Source spans */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-[10px] font-mono text-[#7A7F8E] uppercase tracking-widest">Source Evidence</p>
                      {msg.sources.map((s, j) => (
                        <div key={j} className="border-l-2 border-[#4F8EF7]/40 pl-3">
                          <p className="text-xs text-[#7A7F8E] italic">"{s}"</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-[#161920] border border-[#2A2D35] rounded-xl px-4 py-3">
              <Loader2 className="animate-spin text-[#4F8EF7]" size={16} />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-8 py-4 border-t border-[#2A2D35]">
        <div className="flex gap-3">
          <input
            className="flex-1 bg-[#161920] border border-[#2A2D35] rounded-lg px-4 py-3 text-sm text-[#E8EAF0] placeholder:text-[#7A7F8E] focus:outline-none focus:border-[#4F8EF7] font-mono"
            placeholder="Ask about cases, persons, vehicles, contradictions..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && send()}
          />
          <button
            onClick={send}
            disabled={loading || !input.trim()}
            className="px-4 py-3 bg-[#4F8EF7] hover:bg-[#4F8EF7]/80 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}