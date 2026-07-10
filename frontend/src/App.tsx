import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { Upload, GitGraph, AlertTriangle, MessageSquare } from 'lucide-react'
import UploadPage from './pages/UploadPage'
import GraphPage from './pages/GraphPage'
import ContradictionsPage from './pages/ContradictionsPage'
import QueryPage from './pages/QueryPage'

const navItems = [
  { to: '/', icon: Upload, label: 'Upload' },
  { to: '/graph', icon: GitGraph, label: 'Graph' },
  { to: '/contradictions', icon: AlertTriangle, label: 'Contradictions' },
  { to: '/query', icon: MessageSquare, label: 'Query' },
]

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-[#0D0F12] text-[#E8EAF0]">
        {/* Sidebar */}
        <nav className="w-20 flex flex-col items-center py-6 gap-6 border-r border-[#2A2D35] bg-[#161920]">
          <div className="w-11 h-10 flex items-center justify-center text-xs font-mono font-bold text-white">Case Graph</div>
          <div className="flex flex-col gap-4 mt-4">
            {navItems.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `flex flex-col items-center gap-1 p-2 rounded-lg transition-colors group ${
                    isActive
                      ? 'bg-[#4F8EF7]/10 text-[#4F8EF7]'
                      : 'text-[#7A7F8E] hover:text-[#E8EAF0]'
                  }`
                }
              >
                <Icon size={18} />
                <span className="text-[10px] font-mono">{label}</span>
              </NavLink>
            ))}
          </div>
        </nav>

        {/* Main content */}
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<UploadPage />} />
            <Route path="/graph" element={<GraphPage />} />
            <Route path="/contradictions" element={<ContradictionsPage />} />
            <Route path="/query" element={<QueryPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}