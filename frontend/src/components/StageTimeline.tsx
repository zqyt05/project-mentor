/**
 * 阶段化任务时间线（PRD 模块 2 · 输出）。
 *
 * 点击某个任务会做两件事：
 *   1. 把它绑定为右侧答疑窗口的上下文
 *   2. 跳转到「任务列表」页并滚动定位到该任务卡片
 *
 * 说明：任务之间没有顺序门禁 —— 推荐按顺序推进，但允许学习者按自身情况跳着做。
 */

import { Empty, Progress, Space, Timeline, Tooltip, Typography } from 'antd'
import { CheckCircleFilled, ClockCircleOutlined, PlayCircleFilled } from '@ant-design/icons'
import dayjs from 'dayjs'
import { useNavigate, useParams } from 'react-router-dom'
import type { Stage, Task } from '@/api/types'
import { useAppStore } from '@/store/useAppStore'

const { Text } = Typography

interface StageTimelineProps {
  stages: Stage[]
}

/** 单个任务在时间线上的图标（状态色跟随新闻纸主题） */
function taskIcon(status: Task['status']) {
  if (status === 'done') return <CheckCircleFilled style={{ color: 'var(--success)' }} />
  if (status === 'in_progress') return <PlayCircleFilled style={{ color: 'var(--accent)' }} />
  return <ClockCircleOutlined style={{ color: '#94A3B8' }} />
}

export default function StageTimeline({ stages }: StageTimelineProps) {
  const navigate = useNavigate()
  const { projectId } = useParams<{ projectId: string }>()
  const activeTaskId = useAppStore((state) => state.activeTaskId)
  const setActiveTaskId = useAppStore((state) => state.setActiveTaskId)

  /**
   * 绑定答疑上下文 + 跳转到任务列表并定位到该任务。
   *
   * 定位意图通过 router state 传递而不是全局 store：
   * 它是「一次性、随这次导航生效」的语义，放在 URL 状态里天然不会被重复消费，
   * 也不会受 React StrictMode 双调用 effect 的影响。
   */
  const openTaskInList = (taskId: number) => {
    setActiveTaskId(taskId)
    navigate(`/project/${projectId}/tasks`, { state: { focusTaskId: taskId } })
  }

  if (stages.length === 0) {
    return <Empty description="暂无任务拆解结果" />
  }

  return (
    <Timeline
      mode="left"
      items={stages.map((stage) => {
        const done = stage.tasks.filter((task) => task.status === 'done').length
        const percent = stage.tasks.length ? Math.round((done / stage.tasks.length) * 100) : 0

        return {
          color: percent === 100 ? 'green' : stage.order_index === 0 ? 'blue' : 'gray',
          children: (
            <div className="timeline-stage">
              <div className="timeline-stage-head">
                <Space size={10} wrap>
                  <span className="timeline-stage-name">{stage.name}</span>
                  <span className="timeline-stage-count">
                    {done}/{stage.tasks.length} 已完成
                  </span>
                </Space>
                <Progress
                  percent={percent}
                  size="small"
                  style={{ width: 120, marginBottom: 0 }}
                  strokeColor={percent === 100 ? 'var(--success)' : undefined}
                />
              </div>

              {stage.description && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {stage.description}
                </Text>
              )}

              <div className="timeline-tasks">
                {stage.tasks.map((task) => {
                  const overdue =
                    task.status !== 'done' && task.due_date
                      ? dayjs(task.due_date).isBefore(dayjs(), 'day')
                      : false

                  return (
                    <div
                      key={task.id}
                      className={[
                        'timeline-task',
                        activeTaskId === task.id ? 'timeline-task-active' : '',
                      ]
                        .filter(Boolean)
                        .join(' ')}
                      onClick={() => openTaskInList(task.id)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault()
                          openTaskInList(task.id)
                        }
                      }}
                      role="button"
                      tabIndex={0}
                      title="点击查看该任务的详情与交付标准"
                    >
                      {taskIcon(task.status)}
                      <span className="timeline-task-name">{task.name}</span>
                      <Tooltip title="DDL 截止日期">
                        <span className={`timeline-task-due ${overdue ? 'task-overdue' : ''}`}>
                          {task.due_date ? dayjs(task.due_date).format('MM-DD') : '—'}
                          {overdue ? ' 逾期' : ''}
                        </span>
                      </Tooltip>
                    </div>
                  )
                })}
              </div>
            </div>
          ),
        }
      })}
    />
  )
}
