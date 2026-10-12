/**
 * 阶段化任务时间线（PRD 模块 2 · 输出）。
 * 按顺序展示阶段与任务，点击任务即可让右侧答疑窗口绑定该任务上下文。
 */

import { Empty, Progress, Space, Tag, Timeline, Tooltip, Typography } from 'antd'
import {
  CheckCircleFilled,
  ClockCircleOutlined,
  LockOutlined,
  PlayCircleFilled,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import type { Stage, Task } from '@/api/types'
import { useAppStore } from '@/store/useAppStore'

const { Text } = Typography

interface StageTimelineProps {
  stages: Stage[]
}

/** 单个任务在时间线上的图标与配色 */
function taskIcon(status: Task['status'], locked: boolean) {
  if (status === 'done') return <CheckCircleFilled style={{ color: '#52c41a' }} />
  if (status === 'in_progress') return <PlayCircleFilled style={{ color: '#1677ff' }} />
  if (locked) return <LockOutlined style={{ color: '#bfbfbf' }} />
  return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />
}

export default function StageTimeline({ stages }: StageTimelineProps) {
  const activeTaskId = useAppStore((state) => state.activeTaskId)
  const setActiveTaskId = useAppStore((state) => state.setActiveTaskId)

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
                <Space size={8} wrap>
                  <Text strong>{stage.name}</Text>
                  {stage.is_milestone && <Tag color="gold">里程碑</Tag>}
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {done}/{stage.tasks.length} 已完成
                  </Text>
                </Space>
                <Progress
                  percent={percent}
                  size="small"
                  style={{ width: 120, marginBottom: 0 }}
                  strokeColor={percent === 100 ? '#52c41a' : undefined}
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
                        task.locked ? 'timeline-task-locked' : '',
                      ]
                        .filter(Boolean)
                        .join(' ')}
                      onClick={() => !task.locked && setActiveTaskId(task.id)}
                      role="button"
                      tabIndex={0}
                      title={task.locked ? '完成前面的任务后自动解锁' : '点击绑定到右侧答疑窗口'}
                    >
                      {taskIcon(task.status, task.locked)}
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
