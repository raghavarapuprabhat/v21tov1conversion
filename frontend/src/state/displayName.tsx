import { createContext, useContext, useState, type ReactNode } from 'react'

interface DisplayNameCtx {
  name: string
  setName: (n: string) => void
}

const Ctx = createContext<DisplayNameCtx>({ name: '', setName: () => {} })

function initialName(): string {
  const seed = new URLSearchParams(window.location.search).get('as')
  if (seed) {
    localStorage.setItem('displayName', seed)
    return seed
  }
  return localStorage.getItem('displayName') || ''
}

export function DisplayNameProvider({ children }: { children: ReactNode }) {
  const [name, setNameState] = useState<string>(initialName)
  const setName = (n: string) => {
    localStorage.setItem('displayName', n)
    setNameState(n)
  }
  return <Ctx.Provider value={{ name, setName }}>{children}</Ctx.Provider>
}

export const useDisplayName = () => useContext(Ctx)
