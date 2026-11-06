import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Identifiant de la construction : le front compare le sien à /version.json pour proposer de recharger
const BUILD_ID = new Date().toISOString()
const versionFile = (): Plugin => ({
  name: 'tickson-version',
  generateBundle() {
    this.emitFile({ type: 'asset', fileName: 'version.json', source: JSON.stringify({ build: BUILD_ID }) })
  },
})

export default defineConfig({
  plugins: [react(), tailwindcss(), versionFile()],
  define: { __BUILD_ID__: JSON.stringify(BUILD_ID) },
  // Développement hors Docker : l'API tourne sur le port 8000
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
