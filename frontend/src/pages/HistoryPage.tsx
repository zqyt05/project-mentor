/**
 * 历史学习项目页（PRD 模块 5 · 数据持久化）。
 * 展示本机 SQLite 中保存的全部学习项目，支持继续学习与删除。
 */

import { useCallback, useEffect, useState } from 'react'
import {
  App,
  Button,
  Card,
  Empty,
  List,
  Popconfirm,
  Progress,
  Space,
  Spin,
  Tag,
  Typography,
} from 'antd'
import {
  BookOutlined,
  DeleteOutlined,
  GithubOutlined,
  PlayCircleOutlined,
  StarFilled,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { useNavigate } from 'react-router-dom'
import { projectApi } from '@/api/project'
import type { ProjectBrief, ProjectStatus } from '@/api/types'

const { Paragraph, Text, Title } = Typography

/** 项目状态 → 标签样式 */
const STATUS_META: Record<ProjectStatus, { label: string; color: string }> = {
  learning: { label: '学习中', color: 'processing' },
  reviewing: { label: '待复盘', color: 'warning' },
  completed: { label: '已闭环', color: 'success' },
}

export default function HistoryPage() {
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [projects, setProjects] = useState<ProjectBrief[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setProjects(await projectApi.list())
    } catch {
      /* 错误提示已由 axios 拦截器统一处理 */
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const handleDelete = async (project: ProjectBrief) => {
    try {
      await projectApi.remove(project.id)
      message.success(`已删除「${project.name}」`)
      void load()
    } catch {
      /* 错误提示已由 axios 拦截器统一处理 */
    }
  }

  return (
    <div className="page">
      <Card size="small" className="history-header">
        <Space size={12} wrap style={{ justifyContent: 'space-between', width: '100%' }}>
          <Space direction="vertical" size={2}>
            <Title level={4} style={{ margin: 0 }}>
              历史学习项目
            </Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              所有项目、任务、对话与复盘数据都保存在本机 SQLite 中
            </Text>
          </Space>
          <Tag color="blue">共 {projects.length} 个项目</Tag>
        </Space>
      </Card>

      {loading ? (
        <div className="history-loading">
          <Spin size="large" tip="正在加载历史项目…">
            <div style={{ height: 80 }} />
          </Spin>
        </div>
      ) : projects.length === 0 ? (
        <Empty description="还没有学习项目">
          <Button type="primary" onClick={() => navigate('/')}>
            去创建第一个项目
          </Button>
        </Empty>
      ) : (
        <List
          className="history-list"
          itemLayout="vertical"
          dataSource={projects}
          renderItem={(project) => {
            const meta = STATUS_META[project.status] ?? STATUS_META.learning
            const progress = project.progress

            return (
              <List.Item key={project.id}>
                <Card size="small" hoverable className="history-card">
                  <Space direction="vertical" size={10} style={{ width: '100%' }}>
                    <Space size={8} wrap style={{ justifyContent: 'space-between', width: '100%' }}>
                      <Space size={8} wrap>
                        <Text strong style={{ fontSize: 15 }}>
                          {project.name}
                        </Text>
                        {project.source === 'github' ? (
                          <Tag icon={<GithubOutlined />} color="geekblue">
                            GitHub
                          </Tag>
                        ) : (
                          <Tag icon={<BookOutlined />} color="purple">
                            定制
                          </Tag>
                        )}
                        <Tag color="cyan">{project.difficulty}</Tag>
                        <Tag color={meta.color}>{meta.label}</Tag>
                      </Space>

                      <Space size={8}>
                        <Button
                          type="primary"
                          size="small"
                          icon={<PlayCircleOutlined />}
                          onClick={() =>
                            navigate(
                              project.status === 'reviewing' || project.status === 'completed'
                                ? `/project/${project.id}/review`
                                : `/project/${project.id}/overview`,
                            )
                          }
                        >
                          {project.status === 'learning' ? '继续学习' : '查看复盘'}
                        </Button>
                        <Popconfirm
                          title="删除这个项目？"
                          description="会同时删除它的任务、答疑记录与复盘内容，且不可恢复。"
                          okText="删除"
                          cancelText="取消"
                          okButtonProps={{ danger: true }}
                          onConfirm={() => handleDelete(project)}
                        >
                          <Button size="small" danger icon={<DeleteOutlined />} />
                        </Popconfirm>
                      </Space>
                    </Space>

                    {project.summary && (
                      <Paragraph
                        type="secondary"
                        style={{ margin: 0, fontSize: 13 }}
                        ellipsis={{ rows: 2 }}
                      >
                        {project.summary}
                      </Paragraph>
                    )}

                    <Space size={16} wrap>
                      <Space size={6}>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          学习方向
                        </Text>
                        <Tag>{project.domain}</Tag>
                      </Space>

                      {project.source === 'github' && project.stars != null && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          <StarFilled style={{ color: '#faad14' }} /> {project.stars.toLocaleString()}
                          {project.language ? ` · ${project.language}` : ''}
                        </Text>
                      )}

                      <Text type="secondary" style={{ fontSize: 12 }}>
                        创建于 {dayjs(project.created_at).format('YYYY-MM-DD HH:mm')}
                      </Text>
                    </Space>

                    <Space size={12} style={{ width: '100%' }}>
                      <Progress
                        percent={progress?.percent ?? 0}
                        size="small"
                        style={{ width: 220, marginBottom: 0 }}
                        strokeColor={
                          (progress?.percent ?? 0) === 100 ? '#52c41a' : undefined
                        }
                      />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {progress ? `${progress.done}/${progress.total} 个任务已完成` : '暂无任务'}
                      </Text>
                    </Space>
                  </Space>
                </Card>
              </List.Item>
            )
          }}
        />
      )}
    </div>
  )
}
