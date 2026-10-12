/**
 * 项目卡片（PRD 模块 1 · 输出）。
 * 展示：项目名称、来源标签、难度标签、简介/推荐理由、核心学习点、
 * 最终交付物；GitHub 项目额外展示仓库地址、Star 数、主要语言。
 */

import { Button, Card, Divider, Space, Tag, Tooltip, Typography } from 'antd'
import {
  BookOutlined,
  CheckCircleOutlined,
  ExperimentOutlined,
  GithubOutlined,
  RocketOutlined,
  StarFilled,
  WarningOutlined,
} from '@ant-design/icons'
import type { ProjectCandidate } from '@/api/types'

const { Paragraph, Text, Title } = Typography

interface ProjectCardProps {
  project: ProjectCandidate
  /** 点击「开始学习」 */
  onStart: (project: ProjectCandidate) => void
  /** 该项目正在初始化（拆解任务中） */
  starting?: boolean
  /** 是否有其他项目正在初始化，此时禁用按钮避免并发拆解 */
  disabled?: boolean
}

export default function ProjectCard({
  project,
  onStart,
  starting = false,
  disabled = false,
}: ProjectCardProps) {
  const isGithub = project.source === 'github'

  return (
    <Card
      className="project-card"
      hoverable
      title={
        <Space size={8} wrap>
          <Title level={5} style={{ margin: 0 }}>
            {project.name}
          </Title>
          {isGithub ? (
            <Tag icon={<GithubOutlined />} color="geekblue">
              GitHub 开源
            </Tag>
          ) : (
            <Tag icon={<BookOutlined />} color="purple">
              AI 定制
            </Tag>
          )}
          <Tag color="cyan">{project.difficulty}</Tag>
        </Space>
      }
      extra={
        isGithub && project.stars != null ? (
          <Tooltip title="GitHub Star 数">
            <Text type="secondary">
              <StarFilled style={{ color: '#faad14' }} /> {project.stars.toLocaleString()}
            </Text>
          </Tooltip>
        ) : null
      }
    >
      <Paragraph type="secondary" className="project-card-summary" ellipsis={{ rows: 3 }}>
        {project.summary || '暂无简介'}
      </Paragraph>

      {project.background && (
        <Paragraph className="project-card-block" ellipsis={{ rows: 2 }}>
          <Text strong>项目背景：</Text>
          {project.background}
        </Paragraph>
      )}

      <div className="project-card-block">
        <Text strong>
          <ExperimentOutlined /> 核心学习点
        </Text>
        <div className="project-card-tags">
          {project.core_points.length > 0 ? (
            project.core_points.map((point) => (
              <Tag key={point} color="blue">
                {point}
              </Tag>
            ))
          ) : (
            <Text type="secondary">暂无</Text>
          )}
        </div>
      </div>

      {project.deliverable && (
        <Paragraph className="project-card-block" ellipsis={{ rows: 3 }}>
          <Text strong>
            <CheckCircleOutlined /> 最终交付物：
          </Text>
          {project.deliverable}
        </Paragraph>
      )}

      {project.target_audience && (
        <Paragraph className="project-card-block" type="secondary" ellipsis={{ rows: 2 }}>
          <Text strong>适配人群：</Text>
          {project.target_audience}
        </Paragraph>
      )}

      {project.pitfalls && (
        <Paragraph className="project-card-block" type="warning" ellipsis={{ rows: 2 }}>
          <Text strong>
            <WarningOutlined /> 常见误区：
          </Text>
          {project.pitfalls}
        </Paragraph>
      )}

      <Divider style={{ margin: '12px 0' }} />

      <div className="project-card-footer">
        <Space size={8} wrap>
          {isGithub && project.repo_url && (
            <a href={project.repo_url} target="_blank" rel="noreferrer noopener">
              <GithubOutlined /> {project.repo_full_name ?? '查看仓库'}
            </a>
          )}
          {isGithub && project.language && <Tag>{project.language}</Tag>}
          {project.match_reason && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {project.match_reason}
            </Text>
          )}
        </Space>

        <Button
          type="primary"
          icon={<RocketOutlined />}
          loading={starting}
          disabled={disabled}
          onClick={() => onStart(project)}
        >
          开始学习
        </Button>
      </div>
    </Card>
  )
}
