import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import type { AppSettings } from '../types'

interface SettingsStore extends AppSettings {
  // Actions
  setTheme: (theme: 'light' | 'dark' | 'system') => void
  setLanguage: (language: string) => void
  setAutoSave: (autoSave: boolean) => void
  setNotifications: (notifications: boolean) => void
  setSoundEnabled: (soundEnabled: boolean) => void
  resetSettings: () => void
  
  // Computed values
  isDarkMode: () => boolean
  getEffectiveTheme: () => 'light' | 'dark'
}

const defaultSettings: AppSettings = {
  theme: 'system',
  language: 'es',
  autoSave: true,
  notifications: true,
  soundEnabled: true
}

export const useSettingsStore = create<SettingsStore>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        ...defaultSettings,
        
        // Actions
        setTheme: (theme) => set({ theme }),
        
        setLanguage: (language) => set({ language }),
        
        setAutoSave: (autoSave) => set({ autoSave }),
        
        setNotifications: (notifications) => set({ notifications }),
        
        setSoundEnabled: (soundEnabled) => set({ soundEnabled }),
        
        resetSettings: () => set(defaultSettings),
        
        // Computed values
        isDarkMode: () => {
          const { theme } = get()
          if (theme === 'system') {
            return window.matchMedia('(prefers-color-scheme: dark)').matches
          }
          return theme === 'dark'
        },
        
        getEffectiveTheme: () => {
          const { theme } = get()
          if (theme === 'system') {
            return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
          }
          return theme
        }
      }),
      {
        name: 'settings-store',
        partialize: (state) => ({
          theme: state.theme,
          language: state.language,
          autoSave: state.autoSave,
          notifications: state.notifications,
          soundEnabled: state.soundEnabled
        })
      }
    ),
    { name: 'settings-store' }
  )
)
