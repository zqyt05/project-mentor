/**
 * 全局状态管理（Zustand）。
 *
 * 设计要点（对应 PRD 模块 5 · 全局导航与状态管理）：
 * - `activeTaskId` 是双窗口联动的唯一纽带：主窗口切换任务 → 右窗口自动切换上下文
 * - 答疑窗口自身的状态（messages / loading）独立存放，保证「答疑不影响主窗口」
 */

import { create } from 'zustand'
import type { ChatMessage, ProjectDetail, ProjectStatus } from '@/api/types'

/** 左侧主窗口的页面分区 */
export type MainView = 'overview' | 'tasks' | 'review'

interface AppState {
  // ===== 左侧主窗口状态 =====
  /** 当前项目详情 */
  project: ProjectDetail | null
  /** 左侧当前页面分区 */
  mainView: MainView
  /** 当前绑定的任务 ID（双窗口联动的核心） */
  activeTaskId: number | null

  setProject: (project: ProjectDetail | null) => void
  setMainView: (view: MainView) => void
  /** 切换任务：只影响主窗口选中态与右侧答疑上下文 */
  setActiveTaskId: (taskId: number | null) => void
  /** 局部更新项目状态（完成/开始任务后同步，避免整页重新请求） */
  patchProjectStatus: (status: ProjectStatus) => void
  patchProgress: (progress: ProjectDetail['progress']) => void

  // ===== 右侧答疑窗口独立状态 =====
  /** 当前会话的消息列表 */
  messages: ChatMessage[]
  /** 正在等待 AI 回答 */
  chatLoading: boolean
  /** 快速提问模板 */
  quickPrompts: string[]

  setMessages: (messages: ChatMessage[]) => void
  appendMessages: (messages: ChatMessage[]) => void
  setChatLoading: (loading: boolean) => void
  setQuickPrompts: (prompts: string[]) => void
  /** 切换任务时重置答疑窗口的本地状态 */
  resetChat: () => void
}

export const useAppStore = create<AppState>((set) => ({
  project: null,
  mainView: 'overview',
  activeTaskId: null,

  setProject: (project) => set({ project }),
  setMainView: (mainView) => set({ mainView }),
  setActiveTaskId: (activeTaskId) => set({ activeTaskId }),

  patchProjectStatus: (status) =>
    set((state) => (state.project ? { project: { ...state.project, status } } : state)),

  patchProgress: (progress) =>
    set((state) => (state.project ? { project: { ...state.project, progress } } : state)),

  messages: [],
  chatLoading: false,
  quickPrompts: [],

  setMessages: (messages) => set({ messages }),
  appendMessages: (messages) => set((state) => ({ messages: [...state.messages, ...messages] })),
  setChatLoading: (chatLoading) => set({ chatLoading }),
  setQuickPrompts: (quickPrompts) => set({ quickPrompts }),
  resetChat: () => set({ messages: [], chatLoading: false, quickPrompts: [] }),
}))
