/** 费曼复盘相关接口（PRD 模块 4）。 */

import { http } from './client'
import type { Review, ReviewForm, ReviewGuide } from './types'

export const reviewApi = {
  /** 复盘引导：3 种形式 + 引导问题 */
  guide: () => http.get<ReviewGuide>('/review/guide'),

  /** 提交复盘内容，AI 纠错补全（AI 接口） */
  generate: (projectId: number, form: ReviewForm, userContent: string) =>
    http.post<Review>(
      '/review/generate',
      { project_id: projectId, form, user_content: userContent },
      true,
    ),

  /** 读取项目最新复盘（未复盘时 data 为 null） */
  latest: (projectId: number) => http.get<Review | null>(`/review/${projectId}`),
}
