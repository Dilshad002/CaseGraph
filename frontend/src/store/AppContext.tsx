import { createContext, useContext, useState, ReactNode } from 'react'

interface UploadRecord {
  filename: string
  fir_number: string | null
  entity_count: number
  relationship_count: number
  timestamp: string
}

interface AppState {
  uploadHistory: UploadRecord[]
  addUpload: (data: any) => void
  removeUpload: (filename: string) => void
  clearHistory: () => void
}

const AppContext = createContext<AppState>({
  uploadHistory: [],
  addUpload: () => {},
  removeUpload: () => {},
  clearHistory: () => {},
})

export function AppProvider({ children }: { children: ReactNode }) {
  const [uploadHistory, setUploadHistory] = useState<UploadRecord[]>([])

  const addUpload = (data: any) => {
    const record: UploadRecord = {
      filename: data.filename,
      fir_number: data.regex_entities?.fir_number || null,
      entity_count: data.entities?.length || 0,
      relationship_count: data.relationships?.length || 0,
      timestamp: new Date().toLocaleTimeString(),
    }
    setUploadHistory(prev => [record, ...prev.filter(r => r.filename !== data.filename)])
  }

  const removeUpload = (filename: string) => {
    setUploadHistory(prev => prev.filter(r => r.filename !== filename))
  }

  const clearHistory = () => setUploadHistory([])

  return (
    <AppContext.Provider value={{ uploadHistory, addUpload, removeUpload, clearHistory }}>
      {children}
    </AppContext.Provider>
  )
}

export const useApp = () => useContext(AppContext)