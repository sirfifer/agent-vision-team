import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: mode === 'web' ? '/' : './',
  build: {
    outDir: mode === 'web' ? '../../server/static' : 'dist',
    rollupOptions: {
      output: {
        entryFileNames: mode === 'web' ? 'assets/[name].[hash].js' : 'assets/[name].js',
        chunkFileNames: mode === 'web' ? 'assets/[name].[hash].js' : 'assets/[name].js',
        assetFileNames: mode === 'web' ? 'assets/[name].[hash].[ext]' : 'assets/[name].[ext]',
      },
    },
  },
}));
