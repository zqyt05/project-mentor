import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

/**
 * 后端地址：默认走本机 8000 端口。
 * 用容器（Docker Compose）运行时，通过环境变量指向后端服务名，例如
 *   VITE_API_TARGET=http://backend:8000
 * 这样同一份配置在「本地直跑」和「容器内运行」两种方式下都能用。
 */
const API_TARGET = process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8000'

// Vite 配置：开发期把 /api 代理到后端，避免跨域与硬编码域名
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    // 默认只监听本机回环地址：本应用无登录且后端持有用户的 API Key，
    // 不应在共享网络（咖啡馆/共享办公 WiFi）下对整个局域网开放。
    // 容器内运行时用 CLI 覆盖：vite --host 0.0.0.0（CLI 优先级高于本文件）。
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 1500,
  },
})
