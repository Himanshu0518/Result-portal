/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Public API origin, e.g. https://result-portal-api.onrender.com (no /api suffix). */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
