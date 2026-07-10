import { createContext, useContext, useState, ReactNode } from 'react'

interface AppState {
  lastUpload: any | null
  setLastUpload: (data: any) => void
}

const AppContext = createContext<AppState>({
  lastUpload: null,
  setLastUpload: () => {},
})

export function AppProvider({ children }: { children: ReactNode }) {
  const [lastUpload, setLastUpload] = useState<any | null>(null)
  return (
    <AppContext.Provider value={{ lastUpload, setLastUpload }}>
      {children}
    </AppContext.Provider>
  )
}

export const useApp = () => useContext(AppContext)