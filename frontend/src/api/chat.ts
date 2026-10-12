/** 答疑相关接口（PRD 模块 3 · 双窗口隔离）。 */

import { http } from './client'
import type { ChatAskResult, ChatHistory, ChatScope } from './types'

export const chatApi = {
  /** 提问：自动拼接项目 + 任务上下文（AI 接口） */
  ask: (payload: {
    project_id: number
    task_id?: number | null
    scope: ChatScope
    question: string
  }) => http.post<ChatAskResult>('/chat/ask', payload, true),

  /** 加载指定任务 / 复盘的独立对话历史 */
  history: (projectId: number, scope: ChatScope, taskId?: number | null) =>
    http.get<ChatHistory>('/chat/history', {
      project_id: projectId,
      scope,
      task_id: taskId ?? undefined,
    }),

  /** 清空当前任务的对话（不影响其他任务与主窗口） */
  clear: (projectId: number, scope: ChatScope, taskId?: number | null) =>
    http.delete<{ deleted: number }>('/chat/history', {
      project_id: projectId,
      scope,
      task_id: taskId ?? undefined,
    }),
}
