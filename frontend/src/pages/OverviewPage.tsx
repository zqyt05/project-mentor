/**
 * 项目总览页（PRD 模块 2 · 输出）。
 *
 * 左侧主窗口的默认内容，展示：项目基本信息、学习目标、最终交付物、
 * 整体进度条、阶段化任务时间线。内容静态稳定，不受右侧聊天影响。
 */

import { Card, Col, Descriptions, Empty, Progress, Row, Space, Statistic, Tag, Typography } from 'antd'
import {
  BookOutlined,
  CheckCircleOutlined,
  GithubOutlined,
  StarFilled,
  StarOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { useAppStore } from '@/store/useAppStore'
import StageTimeline from '@/components/StageTimeline'
import MarkdownView from '@/components/MarkdownView'

const { Paragraph, Text, Title } = Typography

export default function OverviewPage() {
  const project = useAppStore((state) => state.project)

  if (!project) {
    return <Empty description="请先选择或创建一个学习项目" />
  }

  const progress = project.progress
  const isGithub = project.source === 'github'

  return (
    <div className="page">
      <Card className="overview-hero">
        <Row gutter={[24, 16]} align="middle">
          <Col flex="auto">
            <Space direction="vertical" size={6} style={{ width: '100%' }}>
              <Space size={8} wrap>
                <Title level={3} style={{ margin: 0 }}>
                  {project.name}
                </Title>
                {isGithub ? (
                  <Tag icon={<GithubOutlined />} color="geekblue">
                    GitHub 开源项目
                  </Tag>
                ) : (
                  <Tag icon={<BookOutlined />} color="purple">
                    AI 定制项目
                  </Tag>
                )}
                <Tag color="cyan">{project.difficulty}</Tag>
                <Tag color="blue">{project.domain}</Tag>
              </Space>

              {isGithub && project.repo_url && (
                <Space size={12} wrap>
                  <a href={project.repo_url} target="_blank" rel="noreferrer noopener">
                    <GithubOutlined /> {project.repo_full_name}
                  </a>
                  {project.stars != null && (
                    <Text type="secondary">
                      <StarFilled style={{ color: '#faad14' }} /> {project.stars.toLocaleString()}
                    </Text>
                  )}
                  {project.language && <Tag>{project.language}</Tag>}
                </Space>
              )}

              <Text type="secondary">
                创建于 {dayjs(project.created_at).format('YYYY-MM-DD HH:mm')}
              </Text>
            </Space>
          </Col>

          <Col>
            <div className="overview-progress">
              <Progress
                type="dashboard"
                percent={progress?.percent ?? 0}
                strokeColor={{ '0%': '#108ee9', '100%': '#87d068' }}
                format={(percent) => (
                  <span className="overview-progress-label">
                    {percent}
                    <span className="overview-progress-unit">%</span>
                  </span>
                )}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {progress ? `${progress.done}/${progress.total} 个任务已完成` : ''}
              </Text>
            </div>
          </Col>
        </Row>
      </Card>

      <Row gutter={[16, 16]} className="overview-stats">
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="总任务" value={progress?.total ?? 0} suffix="个" />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="已完成"
              value={progress?.done ?? 0}
              suffix="个"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="进行中"
              value={progress?.in_progress ?? 0}
              suffix="个"
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="未开始" value={progress?.todo ?? 0} suffix="个" />
          </Card>
        </Col>
      </Row>

      <Card title="项目简介" size="small" className="overview-block">
        {project.summary ? (
          <Paragraph style={{ marginBottom: 0 }}>{project.summary}</Paragraph>
        ) : (
          <Text type="secondary">暂无简介</Text>
        )}
        {project.background && (
          <>
            <Title level={5} style={{ marginTop: 16 }}>
              项目背景
            </Title>
            <MarkdownView content={project.background} compact />
          </>
        )}
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <CheckCircleOutlined /> 学习目标
              </Space>
            }
            size="small"
            className="overview-block overview-block-full"
          >
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
          <Card
            title={
              <Space>
                <StarOutlined /> 核心学习点
              </Space>
            }
            size="small"
            className="overview-block overview-block-full"
          >
            {project.core_points.length > 0 ? (
              <div className="project-card-tags">
                {project.core_points.map((point) => (
                  <Tag key={point} color="blue">
                    {point}
                  </Tag>
                ))}
              </div>
            ) : (
              <Text type="secondary">暂无核心学习点</Text>
            )}
          </Card>
        </Col>
      </Row>

      <Card title="最终交付物" size="small" className="overview-block">
        {project.deliverable ? (
          <Paragraph style={{ marginBottom: 0 }}>{project.deliverable}</Paragraph>
        ) : (
          <Text type="secondary">暂无交付物说明</Text>
        )}
      </Card>

      {(project.target_audience || project.pitfalls) && (
        <Card size="small" className="overview-block">
          <Descriptions
            column={1}
            size="small"
            items={[
              ...(project.target_audience
                ? [{ key: 'audience', label: '适配人群', children: project.target_audience }]
                : []),
              ...(project.pitfalls
                ? [
                    {
                      key: 'pitfalls',
                      label: (
                        <Space size={4}>
                          <WarningOutlined /> 常见学习误区
                        </Space>
                      ),
                      children: project.pitfalls,
                    },
                  ]
                : []),
            ]}
          />
        </Card>
      )}

      <Card
        title="阶段化任务时间线"
        size="small"
        className="overview-block"
        extra={
          <Text type="secondary" style={{ fontSize: 12 }}>
            点击任务即可让右侧答疑窗口绑定该任务上下文
          </Text>
        }
      >
        <StageTimeline stages={project.stages} />
      </Card>
    </div>
  )
}
