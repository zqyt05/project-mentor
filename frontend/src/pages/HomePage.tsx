/**
 * 首页（PRD 模块 1 · 输入）。
 *
 * 极简全屏 Hero：页面只有居中的匹配栏，不呈现任何其他功能板块。
 * 用户输入方向并点击「开始匹配项目」后，才进入左右双窗口布局。
 *
 * 视觉要点：
 * - 标志性渐变出现在 CTA 按钮与标题的强调词上
 * - 区块标签使用「胶囊 + 脉冲圆点 + 等宽大写」的统一模式
 * - 背景装饰（径向辉光 + 缓慢旋转的虚线环 + 浮动几何体）纯装饰、不拦截交互
 *
 * 功能约束（保持不变）：
 * - 必须点击按钮才会匹配，输入框不响应 Enter（避免误触）
 * - 难度选择与示例标签仍可用，它们属于搜索区整体而非独立板块
 */

import { useState } from 'react'
import { Alert, App, Radio, Typography } from 'antd'
import { ArrowRightOutlined, HistoryOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { projectApi } from '@/api/project'
import { useMatchStore } from '@/store/useMatchStore'
import Reveal from '@/components/Reveal'
import type { Difficulty } from '@/api/types'

const { Text } = Typography

/** 示例方向：覆盖技术类与通用类，帮助用户理解产品能力边界 */
const EXAMPLES: { label: string; difficulty: Difficulty }[] = [
  { label: 'React 前端入门', difficulty: '入门' },
  { label: 'Python 爬虫', difficulty: '初级' },
  { label: '财务报表分析', difficulty: '入门' },
  { label: '新媒体运营', difficulty: '入门' },
  { label: 'PPT 制作', difficulty: '入门' },
  { label: '机器学习实战', difficulty: '中级' },
]

export default function HomePage() {
  const { message } = App.useApp()
  const navigate = useNavigate()

  const domain = useMatchStore((state) => state.domain)
  const difficulty = useMatchStore((state) => state.difficulty)
  const setDomain = useMatchStore((state) => state.setDomain)
  const setDifficulty = useMatchStore((state) => state.setDifficulty)
  const setResult = useMatchStore((state) => state.setResult)
  const setLoading = useMatchStore((state) => state.setLoading)

  const [localDomain, setLocalDomain] = useState(domain)
  const [localDifficulty, setLocalDifficulty] = useState<Difficulty>(difficulty)
  const [loading, setLocalLoading] = useState(false)

  const handleSubmit = async () => {
    const value = localDomain.trim()
    if (!value) {
      message.warning('请先输入你想学习的方向')
      return
    }

    setLocalLoading(true)
    setLoading(true)
    try {
      const result = await projectApi.match(value, localDifficulty)
      setDomain(value)
      setDifficulty(localDifficulty)
      setResult(result)
      navigate('/match')
    } catch {
      /* 错误提示已由 axios 拦截器统一处理 */
    } finally {
      setLocalLoading(false)
      setLoading(false)
    }
  }

  return (
    <div className="home-shell">
      {/* ---------- 装饰层（纯视觉，不拦截交互） ---------- */}
      <div className="home-decor" aria-hidden="true">
        <span className="glow home-glow-1" />
        <span className="glow home-glow-2" />
        <span className="home-ring spin-slow" />
        <span className="home-ring-inner" />
        <span className="home-shape home-shape-1 float-slow" />
        <span className="home-shape home-shape-2 float-slow-alt" />
      </div>

      {/* ---------- 历史项目入口（保留功能，但不构成板块） ---------- */}
      <nav className="home-corner-nav">
        <button type="button" className="ant-btn ant-btn-text" onClick={() => navigate('/history')}>
          <HistoryOutlined /> 历史项目
        </button>
      </nav>

      {/* ---------- 居中的搜索 Hero ---------- */}
      <main className="home-hero">
        <Reveal className="home-hero-badge">
          <span className="section-badge">
            <span className="pulse-dot" />
            <span className="section-badge-text">PBL 项目制 AI 实战导师</span>
          </span>
        </Reveal>

        <Reveal delay={1}>
          <h1 className="display-1 home-title">
            你想学点
            <span className="gradient-text">什么</span>？
          </h1>
        </Reveal>

        <Reveal delay={2}>
          <p className="home-subtitle">
            输入任意学习方向，我会帮你匹配一个能真正上手做完的实战项目 ——
            不是给你一份课程大纲，而是直接丢给你一个项目，陪你拆任务、定 DDL、随时答疑。
          </p>
        </Reveal>

        <Reveal delay={3} className="home-search-reveal">
          <div className="home-search">
            <input
              className="home-search-input"
              placeholder="例如：React 前端入门 / 财务报表分析 / 新媒体运营"
              value={localDomain}
              onChange={(event) => setLocalDomain(event.target.value)}
              disabled={loading}
              aria-label="学习方向"
            />
            <button
              type="button"
              className="home-search-btn"
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading ? '匹配中…' : '开始匹配项目'}
              {!loading && <ArrowRightOutlined />}
            </button>
          </div>

          {/* 难度与示例属于搜索区整体，不是独立板块 */}
          <div className="home-search-meta">
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
              <span className="mono-label">难度</span>
              <Radio.Group
                value={localDifficulty}
                onChange={(event) => setLocalDifficulty(event.target.value as Difficulty)}
                optionType="button"
                buttonStyle="solid"
                disabled={loading}
                size="small"
              >
                <Radio.Button value="入门">入门</Radio.Button>
                <Radio.Button value="初级">初级</Radio.Button>
                <Radio.Button value="中级">中级</Radio.Button>
              </Radio.Group>
            </span>

            <span className="home-search-examples">
              <span className="mono-label">试试</span>
              {EXAMPLES.map((example) => (
                <button
                  key={example.label}
                  type="button"
                  className="home-example-chip"
                  onClick={() => {
                    setLocalDomain(example.label)
                    setLocalDifficulty(example.difficulty)
                  }}
                >
                  {example.label}
                </button>
              ))}
            </span>
          </div>

          {loading && (
            <Alert
              className="home-loading"
              type="info"
              showIcon
              message="正在为你规划学习路径"
              description="技术类方向会检索 GitHub 开源项目并逐条评估适配度，通常需要 20–60 秒，请稍候。"
            />
          )}
        </Reveal>

        <Reveal delay={4} className="home-footnote">
          <Text style={{ fontSize: '0.78rem', color: 'var(--muted-foreground)' }}>
            单用户本地使用 · 数据保存在本机 · 不涉及账号与云端同步
          </Text>
        </Reveal>
      </main>
    </div>
  )
}
