/**
 * 演示门禁状态。
 *
 * 三种状态：
 * - `checking`：启动时正在探测（避免闪现登录页）
 * - 需要登录：门禁开启但未通过验证
 * - 已通过：门禁开启且已验证，或门禁未开启（本地单用户模式）
 */

import { create } from 'zustand'
import { authApi } from '@/api/auth'
import { setUnauthorizedHandler } from '@/api/client'

interface AuthStore {
  /** 启动探测是否完成 */
  ready: boolean
  /** 是否开启了演示门禁 */
  required: boolean
  /** 是否已通过验证 */
  authenticated: boolean
  /** 访客短标识 */
  visitorLabel: string | null
  error: string | null

  /** 启动时探测门禁状态 */
  bootstrap: () => Promise<void>
  /** 提交口令 */
  login: (password: string) => Promise<boolean>
  /** 退出演示身份 */
  logout: () => Promise<void>
}

export const useAuthStore = create<AuthStore>((set) => ({
  ready: false,
  required: false,
  authenticated: false,
  visitorLabel: null,
  error: null,

  bootstrap: async () => {
    try {
      const state = await authApi.me()
      set({
        ready: true,
        required: state.required,
        authenticated: state.authenticated,
        visitorLabel: state.visitor_label,
      })
    } catch {
      // 后端不可达时不锁死界面：放行让原有错误提示去解释原因
      set({ ready: true, required: false, authenticated: true })
    }
  },

  login: async (password) => {
    set({ error: null })
    try {
      const state = await authApi.login(password)
      set({
        required: state.required,
        authenticated: state.authenticated,
        visitorLabel: state.visitor_label,
      })
      return true
    } catch {
      set({ error: '口令不正确，请向分享者确认' })
      return false
    }
  },

  logout: async () => {
    try {
      await authApi.logout()
    } finally {
      set({ authenticated: false, visitorLabel: null })
    }
  },
}))

// 门禁失效（Cookie 过期 / 口令变更）时把用户拉回登录页
setUnauthorizedHandler(() => {
  useAuthStore.setState({ authenticated: false, visitorLabel: null })
})
