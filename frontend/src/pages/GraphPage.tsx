import { useEffect, useState, useRef } from 'react'
import CytoscapeComponent from 'react-cytoscapejs'
import axios from 'axios'

const API = 'http://localhost:8000'

const NODE_COLORS: Record<string, string> = {
  Case: '#4F8EF7',
  person: '#4CAF84',
  location: '#F7A84F',
  organization: '#7A7F8E',
  vehicle_number: '#E05252',
  phone_number: '#A78BFA',
  date: '#7A7F8E',
  time: '#7A7F8E',
  unknown: '#3A3D45',
}

export default function GraphPage() {
  const [elements, setElements] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string[]>([])
  const cyRef = useRef<any>(null)

  useEffect(() => {
    fetchGraph()
  }, [])

  useEffect(() => {
  const cy = cyRef.current
  if (!cy) return
  cy.elements().show()
  if (filter.length > 0) {
    cy.nodes().forEach((node: any) => {
      if (filter.includes(node.data('type'))) {
        node.hide()
        node.connectedEdges().hide()
      }
    })
  }
}, [filter])

  const fetchGraph = async () => {
    setLoading(true)
    try {
      const res = await axios.get(`${API}/graph`)
      setElements(res.data.elements || [])
    } catch {
      setElements([])
    } finally {
      setLoading(false)
    }
  }

  const toggleFilter = (type: string) => {
    setFilter(prev =>
      prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]
    )
  }

  const stylesheet: any[] = [
  {
    selector: 'node[type="Case"]',
    style: { 'background-color': '#4F8EF7', 'width': 40, 'height': 40 }
  },
  {
    selector: 'node[type="person"]',
    style: { 'background-color': '#4CAF84' }
  },
  {
    selector: 'node[type="location"]',
    style: { 'background-color': '#F7A84F' }
  },
  {
    selector: 'node[type="organization"]',
    style: { 'background-color': '#7A7F8E' }
  },
  {
    selector: 'node[type="vehicle_number"]',
    style: { 'background-color': '#E05252' }
  },
  {
    selector: 'node[type="phone_number"]',
    style: { 'background-color': '#A78BFA' }
  },
  {
    selector: 'node',
    style: {
      'background-color': '#3A3D45',
      'label': 'data(label)',
      'color': '#E8EAF0',
      'font-size': '10px',
      'font-family': 'monospace',
      'text-valign': 'bottom',
      'text-margin-y': 4,
      'width': 24,
      'height': 24,
    }
  },
  {
    selector: 'edge',
    style: {
      'width': 1,
      'line-color': '#2A2D35',
      'target-arrow-color': '#2A2D35',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
      'font-size': '8px',
      'color': '#7A7F8E',
      'font-family': 'monospace',
    }
  },
  {
    selector: 'edge[type="RELATION"]',
    style: {
      'label': 'data(label)',
      'line-color': '#4F8EF7',
      'target-arrow-color': '#4F8EF7',
      'width': 2,
      'text-rotation': 'autorotate',
    }
  },
  {
    selector: 'node:selected',
    style: { 'border-width': 3, 'border-color': '#4F8EF7' }
  }
]

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-48 border-r border-[#2A2D35] bg-[#161920] p-4 flex flex-col gap-4">
        <div>
          <p className="text-[10px] font-mono text-[#7A7F8E] uppercase tracking-widest mb-3">Filter Nodes</p>
          <div className="space-y-2">
            {Object.entries(NODE_COLORS).map(([type, color]) => (
              <button
                key={type}
                onClick={() => toggleFilter(type)}
                className={`flex items-center gap-2 w-full text-left text-xs font-mono transition-opacity ${
                  filter.includes(type) ? 'opacity-30' : 'opacity-100'
                }`}
              >
                <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                <span className="text-[#7A7F8E]">{type}</span>
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={() => cyRef.current?.fit()}
          className="mt-auto text-xs font-mono text-[#7A7F8E] hover:text-[#E8EAF0] transition-colors"
        >
          Reset view
        </button>
      </div>

      {/* Graph */}
      <div className="flex-1 relative">
        {loading ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-[#7A7F8E] font-mono text-sm">Loading graph...</p>
          </div>
        ) : elements.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-[#7A7F8E] font-mono text-sm">No graph data. Upload FIR documents first.</p>
          </div>
        ) : (
          <CytoscapeComponent
            elements={elements}
            stylesheet={stylesheet}
            style={{ width: '100%', height: '100%', background: '#0D0F12' }}
            layout={{name: 'cose', animate: false, randomize: true, nodeRepulsion: () => 8000, idealEdgeLength: () => 100,
              edgeElasticity: () => 100,
            }}
            cy={(cy: any) => { cyRef.current = cy }}
          />
        )}
      </div>
    </div>
  )
}