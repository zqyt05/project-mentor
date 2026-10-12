/** 项目相关接口（PRD 模块 1）。 */

import { http } from './client'
import type {
  Difficulty,
  ProjectCandidate,
  ProjectBrief,
  ProjectDetail,
  ProjectMatchResult,
} from './types'

export const projectApi = {
  /** 双路径项目智能匹配（AI 接口） */
  match: (domain: string, difficulty: Difficulty) =>
    http.post<ProjectMatchResult>('/project/match', { domain, difficulty }, true),

  /** 开始学习：项目落库 + 任务拆解（AI 接口） */
  start: (domain: string, difficulty: Difficulty, project: ProjectCandidate) =>
    http.post<ProjectDetail>('/project/start', { domain, difficulty, project }, true),

  /** 历史学习项目列表 */
  list: () => http.get<ProjectBrief[]>('/project/list'),

  /** 项目详情（含阶段任务时间线） */
  detail: (projectId: number) => http.get<ProjectDetail>(`/project/${projectId}`),

  /** 删除项目 */
  remove: (projectId: number) => http.delete<{ id: number }>(`/project/${projectId}`),
}
