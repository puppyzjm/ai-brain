const THEME_KEY = 'aibrain-theme'

export type Theme = 'dark' | 'light'

export function currentTheme(): Theme {
  return localStorage.getItem(THEME_KEY) === 'light' ? 'light' : 'dark'
}

export function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark')
  localStorage.setItem(THEME_KEY, theme)
}

export function toggleTheme(): Theme {
  const next: Theme = currentTheme() === 'dark' ? 'light' : 'dark'
  applyTheme(next)
  return next
}

/** 应用启动时初始化：默认深色，尊重用户保存的偏好 */
export function initTheme() {
  applyTheme(currentTheme())
}
