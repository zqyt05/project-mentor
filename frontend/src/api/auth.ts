/** 演示门禁接口。 */

import { http } from './client'

export interface AuthState {
  /** 是否开启了演示门禁（未开启时为本地单用户模式） */
  required: boolean
  /** 当前是否已通过验证 */
  authenticated: boolean
  /** 访客短标识，仅用于界面展示 */
  visitor_label: string | null
}

export const authApi = {
  /** 探测门禁状态（未登录也返回 200，不是错误） */
  me: () => http.get<AuthState>('/auth/me'),
  login: (password: string) => http.post<AuthState>('/auth/login', { password }),
  logout: () => http.post<AuthState>('/auth/logout'),
}
