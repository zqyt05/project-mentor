/**
 * 与后端 Pydantic 模型一一对应的 TypeScript 类型定义。
 * 修改后端 schema 时需同步本文件。
 */

/** 统一响应格式 {code, message, data} */
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export type ProjectSource = 'github' | 'custom'
export type Difficulty = '入门' | '初级' | '中级'
export type TaskStatus = 'todo' | 'in_progress' | 'done'
export type ProjectStatus = 'learning' | 'reviewing' | 'completed'
export type ReviewForm = 'structured' | 'blog' | 'interview'
export type ChatScope = 'task' | 'review'

/** 项目卡片（匹配结果） */
export interface ProjectCandidate {
  name: string
  source: ProjectSource
  difficulty: string
  summary: string
  background: string
  goals: string[]
  core_points: string[]
  deliverable: string
  target_audience: string
  pitfalls: string
  match_reason: string
  repo_url: string | null
  repo_full_name: string | null
  stars: number | null
  language: string | null
}

/** 项目匹配响应 */
export interface ProjectMatchResult {
  path: ProjectSource
  route_reason: string
  projects: ProjectCandidate[]
}

/** 整体进度 */
export interface Progress {
  total: number
  done: number
  in_progress: number
  todo: number
  percent: number
  current_task_id: number | null
  all_completed: boolean
}

/** 任务 */
export interface Task {
  id: number
  project_id: number
  stage_id: number
  order_index: number
  name: string
  description: string
  knowledge_points: string[]
  deliverable_criteria: string
  ddl_days: number
  due_date: string | null
  status: TaskStatus
  started_at: string | null
  completed_at: string | null
  locked: boolean
}

/** 阶段 */
export interface Stage {
  id: number
  project_id: number
  order_index: number
  name: string
  description: string
  is_milestone: boolean
  tasks: Task[]
}

/** 项目列表项 */
export interface ProjectBrief {
  id: number
  name: string
  source: ProjectSource
  domain: string
  difficulty: string
  status: ProjectStatus
  summary: string
  deliverable: string
  repo_url: string | null
  repo_full_name: string | null
  stars: number | null
  language: string | null
  created_at: string
  progress: Progress | null
}

/** 项目详情 */
export interface ProjectDetail extends ProjectBrief {
  background: string
  goals: string[]
  core_points: string[]
  target_audience: string
  pitfalls: string
  stages: Stage[]
  tasks: Task[]
}

/** 对话消息 */
export interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

/** 会话历史 */
export interface ChatHistory {
  conversation_id: number | null
  project_id: number
  task_id: number | null
  scope: ChatScope
  title: string
  messages: ChatMessage[]
  quick_prompts: string[]
}

/** 提问响应 */
export interface ChatAskResult {
  conversation_id: number
  task_id: number | null
  answer: string
  messages: ChatMessage[]
}

/** 复盘引导 */
export interface ReviewGuide {
  forms: { value: ReviewForm; label: string; description: string }[]
  questions: string[]
}

/** 复盘记录 */
export interface Review {
  id: number
  project_id: number
  form: ReviewForm
  user_content: string
  final_content: string
  corrections: string[]
  supplements: string[]
  structure_advice: string
  next_steps: string[]
  created_at: string
}

/** 任务完成响应 */
export interface CompleteTaskResult {
  task: Task
  progress: Progress
  project_status: ProjectStatus
  unlocked_task: Task | null
}

/** 开始任务响应 */
export interface StartTaskResult {
  task: Task
  progress: Progress
}
