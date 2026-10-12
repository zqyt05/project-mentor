/**
 * 项目匹配流程的临时状态（Zustand）。
 *
 * 匹配结果由 AI 生成、耗时较长，放在全局 store 中可以让用户在
 * 「匹配结果页」与「首页」之间往返时不必重新请求。
 */

import { create } from 'zustand'
import type { Difficulty, ProjectMatchResult } from '@/api/types'

interface MatchState {
  /** 用户输入的学习方向 */
  domain: string
  /** 用户选择的难度 */
  difficulty: Difficulty
  /** 匹配结果（未匹配时为 null） */
  result: ProjectMatchResult | null
  /** 匹配请求进行中 */
  loading: boolean
  /** 正在初始化（点击「开始学习」后拆解任务）的项目名，用于局部 loading */
  startingName: string | null

  setDomain: (domain: string) => void
  setDifficulty: (difficulty: Difficulty) => void
  setResult: (result: ProjectMatchResult | null) => void
  setLoading: (loading: boolean) => void
  setStartingName: (name: string | null) => void
  /** 重置整个匹配流程 */
  reset: () => void
}

export const useMatchStore = create<MatchState>((set) => ({
  domain: '',
  difficulty: '入门',
  result: null,
  loading: false,
  startingName: null,

  setDomain: (domain) => set({ domain }),
  setDifficulty: (difficulty) => set({ difficulty }),
  setResult: (result) => set({ result }),
  setLoading: (loading) => set({ loading }),
  setStartingName: (startingName) => set({ startingName }),
  reset: () => set({ domain: '', difficulty: '入门', result: null, loading: false, startingName: null }),
}))
