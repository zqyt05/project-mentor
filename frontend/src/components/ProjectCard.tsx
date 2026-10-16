/**
 * 项目卡片（PRD 模块 1 · 输出）。
 *
 * 新闻纸风格：以字体排印建立层级，仅在「仓库地址 / Star 数」这类
 * 有实际信息价值的地方保留图标，其余位置一律纯文字。
 *
 * 说明：不展示 AI 的适配度打分 —— 适配度只用于后端排序，
 * 呈现给用户的是按适配度排好序的结果本身。
 */

import { useState } from 'react'
import { Button, Card, Space, Tag, Typography } from 'antd'
import { GithubOutlined, StarFilled } from '@ant-design/icons'
import DeliverableList from '@/components/DeliverableList'
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
  const [showMore, setShowMore] = useState(false)

  /** 背景 / 适配人群 / 常见误区默认折叠，让卡片首屏保持清爽 */
  const hasMore = Boolean(project.background || project.target_audience || project.pitfalls)

  return (
    <Card
      className="project-card"
      title={
        <Space size={10} wrap>
          <Title level={4} style={{ margin: 0, fontFamily: 'var(--font-display)' }}>
            {project.name}
          </Title>
          <Tag>{isGithub ? 'GitHub 开源' : 'AI 定制'}</Tag>
          <Tag>{project.difficulty}</Tag>
        </Space>
      }
      extra={
        isGithub && project.stars != null ? (
          <Text className="np-meta">
            <StarFilled style={{ color: 'var(--accent)' }} /> {project.stars.toLocaleString()}
          </Text>
        ) : null
      }
    >
      <Paragraph className="project-card-summary np-justify" style={{ marginBottom: 12 }}>
        {project.summary || '暂无简介'}
      </Paragraph>

      {project.core_points.length > 0 && (
        <div className="project-card-block">
          <span className="np-label np-label-ink">核心学习点</span>
          <div className="project-card-tags">
            {project.core_points.map((point) => (
              <Tag key={point}>{point}</Tag>
            ))}
          </div>
        </div>
      )}

      {project.deliverables.length > 0 && (
        <div className="project-card-block" style={{ marginTop: 10 }}>
          <span className="np-label np-label-ink">最终交付物</span>
          <DeliverableList items={project.deliverables} />
        </div>
      )}

      {/* 次要信息默认折叠：卡片首屏只保留决策必需的内容 */}
      {hasMore && (
        <div style={{ marginTop: 10 }}>
          <button
            type="button"
            className="readme-toggle-inline"
            onClick={() => setShowMore((open) => !open)}
            aria-expanded={showMore}
          >
            {showMore ? '收起' : '更多信息'}
            <span className={`readme-toggle-icon ${showMore ? 'readme-toggle-icon-open' : ''}`}>
              +
            </span>
          </button>

          <div className={`readme-body ${showMore ? 'readme-body-open' : 'readme-body-closed'}`}>
            <div className="readme-body-inner">
              <div className="project-card-extra">
                {project.background && (
                  <div>
                    <span className="np-label">项目背景</span>
                    <Paragraph type="secondary" style={{ margin: '4px 0 0', fontSize: '0.82rem' }}>
                      {project.background}
                    </Paragraph>
                  </div>
                )}
                {project.target_audience && (
                  <div>
                    <span className="np-label">适配人群</span>
                    <Paragraph type="secondary" style={{ margin: '4px 0 0', fontSize: '0.82rem' }}>
                      {project.target_audience}
                    </Paragraph>
                  </div>
                )}
                {project.pitfalls && (
                  <div>
                    <span className="np-label">常见误区</span>
                    <Paragraph type="secondary" style={{ margin: '4px 0 0', fontSize: '0.82rem' }}>
                      {project.pitfalls}
                    </Paragraph>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="project-card-footer">
        <Space size={12} wrap>
          {isGithub && project.repo_url && (
            <a
              className="project-card-repo"
              href={project.repo_url}
              target="_blank"
              rel="noreferrer noopener"
            >
              <GithubOutlined /> {project.repo_full_name ?? project.repo_url}
            </a>
          )}
          {isGithub && project.language && <Tag>{project.language}</Tag>}
        </Space>

        <Button
          type="primary"
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
