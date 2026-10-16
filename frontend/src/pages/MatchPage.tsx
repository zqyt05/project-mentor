/**
 * 项目匹配结果页（PRD 模块 1 · 输出）。
 *
 * 展示路由说明与项目卡片列表，用户点击「开始学习」初始化项目。
 *
 * 关于进度条：任务拆解是一次 LLM 长请求（通常 20–40 秒），接口不提供
 * 中间进度，因此这里用「缓动逼近 94% 并停住」的方式给出持续的视觉反馈，
 * 让等待过程可感知、不焦虑；请求成功后会直接跳转，无需补到 100%。
 */

import { useEffect, useRef, useState } from 'react'
import { Alert, App, Button, Card, Empty, Progress, Space, Tag, Typography } from 'antd'
import { ArrowLeftOutlined, GithubOutlined, RobotOutlined, SearchOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { projectApi } from '@/api/project'
import ProjectCard from '@/components/ProjectCard'
import { useMatchStore } from '@/store/useMatchStore'
import type { ProjectCandidate } from '@/api/types'

const { Paragraph, Title } = Typography

/** 进度条缓动上限：留出余量，避免长时间停在 100% 却还没完成 */
const PROGRESS_CEILING = 94

export default function MatchPage() {
  const { message } = App.useApp()
  const navigate = useNavigate()

  const domain = useMatchStore((state) => state.domain)
  const difficulty = useMatchStore((state) => state.difficulty)
  const result = useMatchStore((state) => state.result)
  const startingName = useMatchStore((state) => state.startingName)
  const setStartingName = useMatchStore((state) => state.setStartingName)

  const [starting, setStarting] = useState(false)
  const [progress, setProgress] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const elapsedTimer = useRef<number | null>(null)

  // 拆解进行中：驱动进度条缓动与已用时计数
  useEffect(() => {
    if (!starting) {
      setProgress(0)
      setElapsed(0)
      return
    }

    setProgress(8)
    const progressTimer = window.setInterval(() => {
      setProgress((current) =>
        current >= PROGRESS_CEILING ? PROGRESS_CEILING : current + (PROGRESS_CEILING - current) * 0.07,
      )
    }, 380)
    elapsedTimer.current = window.setInterval(() => setElapsed((s) => s + 1), 1000)

    return () => {
      window.clearInterval(progressTimer)
      if (elapsedTimer.current) window.clearInterval(elapsedTimer.current)
    }
  }, [starting])

  /** 点击「开始学习」：落库项目 + 拆解任务，然后进入项目总览页 */
  const handleStart = async (project: ProjectCandidate) => {
    setStartingName(project.name)
    setStarting(true)
    try {
      const detail = await projectApi.start(domain, difficulty, project)
      setProgress(100)
      message.success('项目已初始化，开始学习吧')
      navigate(`/project/${detail.id}/overview`)
    } catch {
      /* 错误提示已由 axios 拦截器统一处理 */
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
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Space size={10} wrap>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')} size="small">
              重新输入
            </Button>
            <Title level={3} style={{ margin: 0, fontFamily: 'var(--font-display)' }}>
              「{domain}」的学习项目
            </Title>
            <Tag>{difficulty}</Tag>
            <Tag icon={isGithub ? <GithubOutlined /> : <RobotOutlined />}>
              {isGithub ? '路径 A · GitHub 开源项目' : '路径 B · AI 定制项目'}
            </Tag>
          </Space>

          <Alert
            type={isGithub ? 'info' : 'success'}
            showIcon
            icon={isGithub ? <SearchOutlined /> : <RobotOutlined />}
            message={result.route_reason}
            description={
              isGithub
                ? '筛选条件：Star > 500、近一年有更新、README 完整；已按适配度从高到低排序。'
                : '每个项目都有明确交付物，可在 1–2 周内完成，适合拆解为 4–6 个阶段性任务。'
            }
          />

          <span className="np-label">
            共 {result.projects.length} 个推荐项目 · 点击「开始学习」后 AI 会把它拆解为带 DDL 的阶段任务
          </span>
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

      {/* 拆解进度：给等待过程一个可见的、持续推进的反馈 */}
      {starting && (
        <Card size="small" className="match-starting">
          <Space direction="vertical" size={10} style={{ width: '100%' }}>
            <Space size={10} wrap style={{ justifyContent: 'space-between', width: '100%' }}>
              <span className="np-label np-label-ink">正在拆解任务</span>
              <span className="np-meta">
                已用时 {elapsed}s · 通常需要 20–40s
              </span>
            </Space>

            <Progress
              percent={Math.round(progress)}
              strokeColor="var(--accent)"
              trailColor="#F1F5F9"
              format={(percent) => (
                <span className="np-mono" style={{ fontSize: '0.72rem' }}>
                  {percent}%
                </span>
              )}
            />

            <Paragraph style={{ margin: 0, fontSize: '0.84rem' }}>
              AI 正在把「{startingName}」拆解为 4–6 个学习阶段，并为每个任务计算知识点、
              交付标准与 DDL 截止日期。请保持页面打开。
            </Paragraph>
          </Space>
        </Card>
      )}
    </div>
  )
}
