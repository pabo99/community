/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * Base URL of the backend REST API. Configured now as a typed seam; no
   * requests are made from the frontend yet (backend communication arrives in
   * later milestone issues).
   */
  readonly VITE_API_BASE_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
