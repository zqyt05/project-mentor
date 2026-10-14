/**
 * 任务列表页（PRD 模块 2）。
 *
 * 主任务窗口的任务操作区：按阶段顺序展示全部任务卡片，
 * 支持开始 / 完成 / 重置 / 调整 DDL。右侧答疑窗口随之切换上下文。
 */

import { Alert, Button, Card, Empty, Progress, Space, Tag, Typography } from 'antd'
import { ClockCircleOutlined, FireOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { useCallback, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { projectApi } from '@/api/project'
import TaskCard from '@/components/TaskCard'
import { useAppStore } from '@/store/useAppStore'
import type { Task } from '@/api/types'

const { Text, Title } = Typography

export default function TasksPage() {
  const navigate = useNavigate()
  const project = useAppStore((state) => state.project)
  const setProject = useAppStore((state) => state.setProject)
  const activeTaskId = useAppStore((state) => state.activeTaskId)
  const setActiveTaskId = useAppStore((state) => state.setActiveTaskId)
  // 从「项目总览」的时间线跳转过来时携带的定位意图
  const location = useLocation()
  const focusTaskId = (location.state as { focusTaskId?: number } | null)?.focusTaskId

  /**
   * 滚动定位到目标任务并短暂高亮，让用户立刻看到自己点的是哪一条。
   *
   * 依赖里带上 location.key：即使连续两次点击同一个任务，也会重新定位。
   * 这里刻意不使用「先标记已消费再执行」的写法 —— React StrictMode 在开发环境会
   * 双调用 effect（第一次立即被 cleanup），那种写法会导致第二次直接跳过、定位失效。
   */
  useEffect(() => {
    if (!focusTaskId) return

    // 等卡片渲染完成再滚动
    const timer = window.setTimeout(() => {
      const el = document.getElementById(`task-${focusTaskId}`)
      if (!el) return
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      el.classList.add('task-card-flash')
      window.setTimeout(() => el.classList.remove('task-card-flash'), 1600)
    }, 150)

    return () => window.clearTimeout(timer)
  }, [focusTaskId, location.key])

  /** 任务状态变化后重新拉取项目详情，保证进度与统计同步 */
  const reload = useCallback(async () => {
    if (!project) return
    const detail = await projectApi.detail(project.id)
    setProject(detail)
    if (activeTaskId && !detail.tasks.some((task) => task.id === activeTaskId)) {
      setActiveTaskId(detail.progress?.current_task_id ?? null)
    }
  }, [project, setProject, activeTaskId, setActiveTaskId])

  if (!project) {
    return <Empty description="请先选择或创建一个学习项目" />
  }

  const progress = project.progress
  const currentTask = project.tasks.find((task) => task.status === 'in_progress')
  const nextTask = project.tasks.find((task) => task.status === 'todo')

  // 逾期任务提醒
  const overdueTasks = project.tasks.filter(
    (task) => task.status !== 'done' && task.due_date && dayjs(task.due_date).isBefore(dayjs(), 'day'),
  )

  /** 全局任务序号（跨阶段连续编号） */
  const indexOf = (task: Task) => project.tasks.findIndex((item) => item.id === task.id) + 1

  return (
    <div className="page">
      <Card size="small" className="tasks-header">
        <Space direction="vertical" size={10} style={{ width: '100%' }}>
          <Space size={12} wrap style={{ width: '100%', justifyContent: 'space-between' }}>
            <Title level={4} style={{ margin: 0 }}>
              任务列表
            </Title>
            <Space size={8}>
              <Text type="secondary">
                {progress ? `${progress.done}/${progress.total} 已完成` : ''}
              </Text>
              <Progress
                percent={progress?.percent ?? 0}
                size="small"
                style={{ width: 160, marginBottom: 0 }}
              />
            </Space>
          </Space>

          <Space size={8} wrap>
            {currentTask ? (
              <Tag color="processing" icon={<FireOutlined />}>
                当前任务：{currentTask.name}
              </Tag>
            ) : nextTask ? (
              <Tag color="blue">下一步：{nextTask.name}</Tag>
            ) : (
              <Tag color="success">全部任务已完成，可以进入项目复盘</Tag>
            )}
            {overdueTasks.length > 0 && (
              <Tag color="error" icon={<ClockCircleOutlined />}>
                {overdueTasks.length} 个任务已逾期
              </Tag>
            )}
          </Space>

          <Text type="secondary" style={{ fontSize: 12 }}>
            推荐按顺序推进，但你可以根据实际情况跳着做 —— 任意任务都能直接开始。
            点击任务卡片可让右侧答疑窗口绑定该任务上下文。
          </Text>
        </Space>
      </Card>

      {progress?.all_completed && (
        <Alert
          type="success"
          showIcon
          message="全部任务已完成"
          description="可以进入「项目复盘」，用费曼学习法输出项目总结，AI 会帮你纠错补全，完成知识闭环。"
          className="tasks-alert"
          action={
            <Button size="small" type="primary" onClick={() => navigate(`/project/${project.id}/review`)}>
              进入项目复盘
            </Button>
          }
        />
      )}

      {project.stages.length === 0 ? (
        <Empty description="暂无任务拆解结果" />
      ) : (
        project.stages.map((stage) => {
          const done = stage.tasks.filter((task) => task.status === 'done').length
          const stagePercent = stage.tasks.length
            ? Math.round((done / stage.tasks.length) * 100)
            : 0

          return (
            <div key={stage.id} className="stage-group">
              <div className="stage-group-head">
                <Space size={10} wrap>
                  <span className="stage-group-index">{stage.order_index + 1}</span>
                  <span className="stage-group-name">{stage.name}</span>
                  <span className="stage-group-count">
                    {done}/{stage.tasks.length} 已完成
                  </span>
                </Space>
                <Progress
                  percent={stagePercent}
                  size="small"
                  style={{ width: 140, marginBottom: 0 }}
                  strokeColor={stagePercent === 100 ? '#52c41a' : undefined}
                />
              </div>

              {stage.description && (
                <Text type="secondary" className="stage-group-desc">
                  {stage.description}
                </Text>
              )}

              <div className="stage-group-tasks">
                {stage.tasks.map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    index={indexOf(task)}
                    active={activeTaskId === task.id}
                    onChanged={reload}
                  />
                ))}
              </div>
            </div>
          )
        })
      )}
    </div>
  )
}
