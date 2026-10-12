/**
 * 任务卡片（PRD 模块 2）。
 * 展示任务名称、描述、知识点标签、交付标准、DDL；
 * 支持「开始当前任务」「标记完成」「重置」，以及手动调整 DDL 日期。
 */

import { useState } from 'react'
import { App, Button, DatePicker, Popconfirm, Space, Tag, Tooltip, Typography } from 'antd'
import {
  CheckOutlined,
  ClockCircleOutlined,
  LockOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  UndoOutlined,
} from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'
import { taskApi } from '@/api/task'
import { useAppStore } from '@/store/useAppStore'
import type { CompleteTaskResult, Task } from '@/api/types'

const { Paragraph, Text } = Typography

interface TaskCardProps {
  task: Task
  /** 任务序号（从 1 开始，用于展示） */
  index: number
  /** 是否为当前选中的任务（决定高亮与答疑绑定） */
  active: boolean
  /** 数据变化后通知父组件刷新 */
  onChanged: () => void
}

/** 状态 → 展示样式 */
const STATUS_META: Record<Task['status'], { label: string; color: string }> = {
  todo: { label: '未开始', color: 'default' },
  in_progress: { label: '进行中', color: 'processing' },
  done: { label: '已完成', color: 'success' },
}

export default function TaskCard({ task, index, active, onChanged }: TaskCardProps) {
  const { message } = App.useApp()
  const setActiveTaskId = useAppStore((state) => state.setActiveTaskId)
  const [busy, setBusy] = useState(false)
  const [editingDue, setEditingDue] = useState(false)

  const meta = STATUS_META[task.status]
  const overdue =
    task.status !== 'done' && task.due_date ? dayjs(task.due_date).isBefore(dayjs(), 'day') : false

  /** 统一包装异步操作，避免重复点击并统一错误提示 */
  const run = async (action: () => Promise<unknown>, successText?: string) => {
    setBusy(true)
    try {
      await action()
      if (successText) message.success(successText)
      onChanged()
    } catch {
      /* 错误提示已由 axios 拦截器统一处理 */
    } finally {
      setBusy(false)
    }
  }

  const handleStart = () =>
    run(async () => {
      await taskApi.start(task.id)
      // 开始任务后，右侧答疑窗口自动切换到该任务上下文
      setActiveTaskId(task.id)
    }, '任务已开始，右侧答疑窗口已切换到该任务')

  const handleComplete = () =>
    run(async () => {
      const result = (await taskApi.complete(task.id)) as CompleteTaskResult
      message.success(
        result.progress.all_completed
          ? '全部任务已完成，已进入费曼复盘环节'
          : result.unlocked_task
            ? `任务完成！已解锁「${result.unlocked_task.name}」`
            : '任务已完成',
      )
    })

  const handleReset = () => run(() => taskApi.reset(task.id), '任务已重置为未开始')

  const handleDueChange = (value: Dayjs | null) =>
    run(async () => {
      await taskApi.update(task.id, { due_date: value ? value.format('YYYY-MM-DD') : null })
      setEditingDue(false)
    }, 'DDL 已更新')

  return (
    <div
      className={[
        'task-card',
        `task-card-${task.status}`,
        active ? 'task-card-active' : '',
        task.locked ? 'task-card-locked' : '',
      ]
        .filter(Boolean)
        .join(' ')}
      onClick={() => !task.locked && setActiveTaskId(task.id)}
      role="button"
      tabIndex={0}
    >
      <div className="task-card-head">
        <Space size={8} align="center" wrap>
          <span className="task-index">{index}</span>
          <Text strong className="task-name">
            {task.name}
          </Text>
          <Tag color={meta.color}>{meta.label}</Tag>
          {task.locked && (
            <Tooltip title="完成前面的任务后自动解锁">
              <Tag icon={<LockOutlined />}>待解锁</Tag>
            </Tooltip>
          )}
          {active && <Tag color="blue">答疑已绑定</Tag>}
        </Space>

        <Space size={6} className="task-card-actions" onClick={(event) => event.stopPropagation()}>
          {/* DDL 展示与手动调整 */}
          {editingDue ? (
            <DatePicker
              size="small"
              defaultValue={task.due_date ? dayjs(task.due_date) : undefined}
              onChange={handleDueChange}
              onOpenChange={(open) => !open && setEditingDue(false)}
              open
              allowClear={false}
              disabledDate={(current) => current && current < dayjs().startOf('day')}
            />
          ) : (
            <Tooltip title="点击调整 DDL 日期">
              <Button
                size="small"
                type="text"
                icon={<ClockCircleOutlined />}
                danger={overdue}
                onClick={() => setEditingDue(true)}
              >
                <span className={overdue ? 'task-overdue' : ''}>
                  {task.due_date ? dayjs(task.due_date).format('MM-DD') : '设置 DDL'}
                  {overdue ? '（已逾期）' : ''}
                </span>
              </Button>
            </Tooltip>
          )}
        </Space>
      </div>

      {task.description && (
        <Paragraph type="secondary" className="task-desc" ellipsis={{ rows: 2, expandable: true }}>
          {task.description}
        </Paragraph>
      )}

      {task.knowledge_points.length > 0 && (
        <div className="task-points">
          {task.knowledge_points.map((point) => (
            <Tag key={point} color="geekblue">
              {point}
            </Tag>
          ))}
        </div>
      )}

      {task.deliverable_criteria && (
        <div className="task-criteria">
          <Text strong style={{ fontSize: 12 }}>
            交付标准：
          </Text>
          <Text style={{ fontSize: 12 }}>{task.deliverable_criteria}</Text>
        </div>
      )}

      <div className="task-card-footer" onClick={(event) => event.stopPropagation()}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          建议 {task.ddl_days} 天
        </Text>
        <Space size={6}>
          {task.status === 'todo' && (
            <Button
              type="primary"
              size="small"
              icon={<PlayCircleOutlined />}
              loading={busy}
              disabled={task.locked}
              onClick={handleStart}
            >
              开始当前任务
            </Button>
          )}
          {task.status === 'in_progress' && (
            <Button
              type="primary"
              size="small"
              icon={<CheckOutlined />}
              loading={busy}
              onClick={handleComplete}
            >
              标记完成
            </Button>
          )}
          {task.status === 'done' && (
            <Popconfirm
              title="把任务退回未开始？"
              onConfirm={handleReset}
              okText="确认"
              cancelText="取消"
            >
              <Button size="small" icon={<UndoOutlined />} loading={busy}>
                重置
              </Button>
            </Popconfirm>
          )}
          {task.status === 'in_progress' && (
            <Popconfirm
              title="把任务退回未开始？"
              onConfirm={handleReset}
              okText="确认"
              cancelText="取消"
            >
              <Button size="small" type="text" icon={<ReloadOutlined />} loading={busy} />
            </Popconfirm>
          )}
        </Space>
      </div>
    </div>
  )
}
