/** 任务相关接口（PRD 模块 2）。 */

import { http } from './client'
import type {
  CompleteTaskResult,
  Progress,
  Stage,
  StartTaskResult,
  Task,
  TaskStatus,
} from './types'

export const taskApi = {
  /** 阶段任务时间线 */
  stages: (projectId: number) => http.get<Stage[]>(`/task/project/${projectId}/stages`),

  /** 项目整体进度 */
  progress: (projectId: number) => http.get<Progress>(`/task/project/${projectId}/progress`),

  /** 任务详情 */
  detail: (taskId: number) => http.get<Task>(`/task/${taskId}`),

  /** 更新任务（调整 DDL / 状态 / 内容） */
  update: (
    taskId: number,
    payload: {
      name?: string
      description?: string
      due_date?: string | null
      status?: TaskStatus
      knowledge_points?: string[]
      deliverable_criteria?: string
    },
  ) => http.patch<Task>(`/task/${taskId}`, payload),

  /** 开始任务：状态变为进行中，答疑窗口切换上下文 */
  start: (taskId: number) => http.post<StartTaskResult>(`/task/${taskId}/start`),

  /** 标记完成：自动解锁下一任务 */
  complete: (taskId: number) => http.post<CompleteTaskResult>(`/task/${taskId}/complete`),

  /** 重置为未开始 */
  reset: (taskId: number) => http.post<Task>(`/task/${taskId}/reset`),
}
