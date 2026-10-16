/**
 * 项目总览页（PRD 模块 2 · 输出）。
 *
 * 新闻纸风格：以统一的区块标题建立层级，正文使用衬线体便于长文阅读，
 * 统计数字用等宽字体，区块之间通过边框而非阴影分隔。
 *
 * 按需求调整：
 * - 「项目简介 / 项目背景 / README 摘要」统一使用 Card 标题，字号一致
 * - README 摘要默认折叠，展开后首行展示 GitHub 仓库地址，可点击跳转原文
 * - 进度由环形改为线性，与整体的矩形几何语言保持一致
 */

import { useState } from 'react'
import { Card, Col, Descriptions, Empty, Progress, Row, Space, Tag, Typography } from 'antd'
import { GithubOutlined, StarFilled } from '@ant-design/icons'
import dayjs from 'dayjs'
import { useAppStore } from '@/store/useAppStore'
import StageTimeline from '@/components/StageTimeline'
import DeliverableList from '@/components/DeliverableList'
import MarkdownView from '@/components/MarkdownView'

const { Paragraph, Text } = Typography

export default function OverviewPage() {
  const project = useAppStore((state) => state.project)
  const [readmeOpen, setReadmeOpen] = useState(false)

  if (!project) {
    return <Empty description="请先选择或创建一个学习项目" />
  }

  const progress = project.progress
  const isGithub = project.source === 'github'
  const hasReadme = Boolean(project.readme_digest)

  return (
    <div className="page">
      {/* ---------- 报头式项目信息 ---------- */}
      <section className="overview-hero newsprint-texture">
        <Row gutter={[24, 16]} align="middle" style={{ padding: '20px 22px' }}>
          <Col flex="auto">
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              <div className="home-kicker" style={{ marginBottom: 0 }}>
                <span className="np-label np-label-red">
                  {isGithub ? 'GitHub 开源项目' : 'AI 定制项目'}
                </span>
                <span className="np-label">
                  {dayjs(project.created_at).format('YYYY.MM.DD')} · {project.difficulty}
                </span>
              </div>

              <h1 className="np-h2" style={{ margin: 0 }}>
                {project.name}
              </h1>

              <Space size={12} wrap>
                <Tag>{project.domain}</Tag>
                {isGithub && project.repo_url && (
                  <a
                    className="project-card-repo"
                    href={project.repo_url}
                    target="_blank"
                    rel="noreferrer noopener"
                  >
                    <GithubOutlined /> {project.repo_full_name}
                  </a>
                )}
                {project.stars != null && (
                  <Text className="np-meta">
                    <StarFilled /> {project.stars.toLocaleString()}
                  </Text>
                )}
                {project.language && <Tag>{project.language}</Tag>}
              </Space>
            </Space>
          </Col>

          <Col flex="0 0 210px">
            <div className="overview-progress">
              <span className="np-label">学习进度</span>
              <span className="overview-progress-label">
                {progress?.percent ?? 0}
                <span className="overview-progress-unit">%</span>
              </span>
              <Progress
                percent={progress?.percent ?? 0}
                showInfo={false}
                strokeColor="var(--accent)"
                trailColor="#F1F5F9"
                style={{ marginBottom: 0 }}
              />
              <Text className="np-meta">
                {progress ? `${progress.done}/${progress.total} 个任务已完成` : ''}
              </Text>
            </div>
          </Col>
        </Row>
      </section>

      {/* ---------- 统计条：合并网格 ---------- */}
      <section className="overview-stats">
        {[
          { label: '总任务', value: progress?.total ?? 0 },
          { label: '已完成', value: progress?.done ?? 0 },
          { label: '进行中', value: progress?.in_progress ?? 0 },
          { label: '未开始', value: progress?.todo ?? 0 },
        ].map((item) => (
          <div className="overview-stat" key={item.label}>
            <div className="overview-stat-value">{item.value}</div>
            <div className="overview-stat-label">{item.label}</div>
          </div>
        ))}
      </section>

      {/* ---------- 项目简介 ---------- */}
      <Card size="small" title="项目简介" className="overview-block">
        {project.summary ? (
          <Paragraph className="np-justify" style={{ marginBottom: 0 }}>
            {project.summary}
          </Paragraph>
        ) : (
          <Text type="secondary">暂无简介</Text>
        )}
      </Card>

      {/* ---------- 项目背景 ---------- */}
      <Card size="small" title="项目背景" className="overview-block">
        {project.background ? (
          <MarkdownView content={project.background} compact />
        ) : (
          <Text type="secondary">暂无背景说明</Text>
        )}
      </Card>

      {/* ---------- README 摘要：默认折叠，展开后首行回链仓库 ---------- */}
      {hasReadme && (
        <Card
          size="small"
          title="README 摘要"
          className="overview-block readme-card"
          extra={
            <button
              type="button"
              className="readme-toggle-inline"
              onClick={() => setReadmeOpen((open) => !open)}
              aria-expanded={readmeOpen}
            >
              {readmeOpen ? '收起' : '展开'}
              <span className={`readme-toggle-icon ${readmeOpen ? 'readme-toggle-icon-open' : ''}`}>
                +
              </span>
            </button>
          }
        >
          <div className={`readme-body ${readmeOpen ? 'readme-body-open' : 'readme-body-closed'}`}>
            <div className="readme-body-inner">
              <div className="readme-content">
                {/* 展开后首行再次给出仓库地址，方便直接跳转看原文 */}
                {project.repo_url && (
                  <div className="readme-repo-line">
                    <span className="np-label np-label-ink">仓库原文</span>
                    <a
                      className="readme-repo-link"
                      href={project.repo_url}
                      target="_blank"
                      rel="noreferrer noopener"
                    >
                      <GithubOutlined /> {project.repo_url}
                    </a>
                  </div>
                )}
                <div className="readme-text">{project.readme_digest}</div>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* ---------- 学习目标 / 核心学习点 ---------- */}
      <Row gutter={[0, 0]}>
        <Col xs={24} lg={12} className="overview-split-left">
          <Card size="small" title="学习目标" className="overview-block overview-block-full">
            {project.goals.length > 0 ? (
              <ul className="overview-list">
                {project.goals.map((goal) => (
                  <li key={goal}>{goal}</li>
                ))}
              </ul>
            ) : (
              <Text type="secondary">暂无学习目标</Text>
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card size="small" title="核心学习点" className="overview-block overview-block-full">
            {project.core_points.length > 0 ? (
              <div className="project-card-tags">
                {project.core_points.map((point) => (
                  <Tag key={point}>{point}</Tag>
                ))}
              </div>
            ) : (
              <Text type="secondary">暂无核心学习点</Text>
            )}
          </Card>
        </Col>
      </Row>

      {/* ---------- 最终交付物 ---------- */}
      <Card size="small" title="最终交付物" className="overview-block">
        {project.deliverables.length > 0 ? (
          <DeliverableList items={project.deliverables} />
        ) : (
          <Text type="secondary">暂无交付物说明</Text>
        )}
      </Card>

      {/* ---------- 适配人群 / 常见误区 ---------- */}
      {(project.target_audience || project.pitfalls) && (
        <Card size="small" title="适用说明" className="overview-block">
          <Descriptions
            column={1}
            size="small"
            colon={false}
            items={[
              ...(project.target_audience
                ? [{ key: 'audience', label: '适配人群', children: project.target_audience }]
                : []),
              ...(project.pitfalls
                ? [{ key: 'pitfalls', label: '常见误区', children: project.pitfalls }]
                : []),
            ]}
          />
        </Card>
      )}

      {/* ---------- 阶段化任务时间线 ---------- */}
      <Card
        size="small"
        title="阶段化任务时间线"
        className="overview-block"
        extra={
          <span className="np-label">点击任务即可让答疑窗口绑定该任务</span>
        }
      >
        <StageTimeline stages={project.stages} />
      </Card>
    </div>
  )
}
