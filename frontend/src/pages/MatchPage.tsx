/**
 * 项目匹配结果页（PRD 模块 1 · 输出）。
 * 展示路由说明与项目卡片列表，用户点击「开始学习」初始化项目。
 */

import { Alert, App, Button, Card, Empty, Space, Spin, Tag, Typography } from 'antd'
import { ArrowLeftOutlined, GithubOutlined, RobotOutlined, SearchOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { projectApi } from '@/api/project'
import ProjectCard from '@/components/ProjectCard'
import { useMatchStore } from '@/store/useMatchStore'
import type { ProjectCandidate } from '@/api/types'

const { Paragraph, Text, Title } = Typography

export default function MatchPage() {
  const { message } = App.useApp()
  const navigate = useNavigate()

  const domain = useMatchStore((state) => state.domain)
  const difficulty = useMatchStore((state) => state.difficulty)
  const result = useMatchStore((state) => state.result)
  const startingName = useMatchStore((state) => state.startingName)
  const setStartingName = useMatchStore((state) => state.setStartingName)

  const [starting, setStarting] = useState(false)

  /** 点击「开始学习」：落库项目 + 拆解任务，然后进入项目总览页 */
  const handleStart = async (project: ProjectCandidate) => {
    setStartingName(project.name)
    setStarting(true)
    try {
      message.loading({ content: `正在拆解「${project.name}」的阶段任务与 DDL…`, key: 'start', duration: 0 })
      const detail = await projectApi.start(domain, difficulty, project)
      message.success({ content: '项目已初始化，开始学习吧', key: 'start' })
      navigate(`/project/${detail.id}/overview`)
    } catch {
      message.destroy('start')
    } finally {
      setStarting(false)
      setStartingName(null)
    }
  }

  if (!result) {
    return (
      <div className="page">
        <Empty description="还没有匹配结果">
          <Button type="primary" onClick={() => navigate('/')}>
            去输入学习方向
          </Button>
        </Empty>
      </div>
    )
  }

  const isGithub = result.path === 'github'

  return (
    <div className="page">
      <Card size="small" className="match-header">
        <Space direction="vertical" size={10} style={{ width: '100%' }}>
          <Space size={10} wrap>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')} size="small">
              重新输入
            </Button>
            <Title level={4} style={{ margin: 0 }}>
              「{domain}」的学习项目
            </Title>
            <Tag color="cyan">{difficulty}</Tag>
            {isGithub ? (
              <Tag icon={<GithubOutlined />} color="geekblue">
                路径 A · GitHub 开源项目
              </Tag>
            ) : (
              <Tag icon={<RobotOutlined />} color="purple">
                路径 B · AI 定制项目
              </Tag>
            )}
          </Space>

          <Alert
            type={isGithub ? 'info' : 'success'}
            showIcon
            icon={isGithub ? <SearchOutlined /> : <RobotOutlined />}
            message={result.route_reason}
            description={
              isGithub
                ? '筛选条件：Star > 500、近一年有更新、README 完整；已由 AI 按难度匹配度排序。'
                : '每个项目都有明确交付物，可在 1-2 周内完成，适合拆解为 4-6 个阶段性任务。'
            }
          />

          <Text type="secondary" style={{ fontSize: 12 }}>
            共 {result.projects.length} 个推荐项目 · 点击「开始学习」后 AI 会把它拆解为带 DDL 的阶段任务
          </Text>
        </Space>
      </Card>

      {result.projects.length === 0 ? (
        <Empty description="没有匹配到合适的项目，请换个方向或难度试试" />
      ) : (
        <div className="match-list">
          {result.projects.map((project) => (
            <ProjectCard
              key={`${project.source}-${project.name}`}
              project={project}
              onStart={handleStart}
              starting={starting && startingName === project.name}
              disabled={starting && startingName !== project.name}
            />
          ))}
        </div>
      )}

      {starting && (
        <Card size="small" className="match-starting">
          <Space>
            <Spin size="small" />
            <Paragraph style={{ margin: 0 }}>
              AI 正在把「{startingName}」拆解为 4-6 个学习阶段与 DDL 任务，通常需要 20-40 秒…
            </Paragraph>
          </Space>
        </Card>
      )}
    </div>
  )
}
