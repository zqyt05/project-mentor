/**
 * 首页（PRD 模块 1 · 输入）。
 *
 * 极简全屏 Hero：页面只有居中的匹配栏，不呈现任何功能板块。
 * 用户输入方向并点击「开始匹配项目」后，才进入左右双窗口布局。
 *
 * 视觉要点：
 * - 标志性渐变出现在 CTA 按钮、标题强调词与步骤序号上
 * - 四步产品介绍用「渐变序号 + 箭头连接器」横向铺开，替代原先的大段说明
 * - 背景装饰（径向辉光 + 缓慢旋转的虚线环 + 浮动几何体）纯装饰、不拦截交互
 *
 * 功能约束（保持不变）：
 * - 必须点击按钮才会匹配，输入框不响应 Enter（避免误触）
 * - 难度选择与示例标签仍可用，它们属于搜索区整体而非独立板块
 */

import { useEffect, useState } from 'react'
import { App, Progress, Radio } from 'antd'
import { ArrowRightOutlined, HistoryOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { projectApi } from '@/api/project'
import { useMatchStore } from '@/store/useMatchStore'
import Reveal from '@/components/Reveal'
import type { Difficulty } from '@/api/types'

/** 示例方向：覆盖技术类与通用类，帮助用户理解产品能力边界 */
const EXAMPLES: { label: string; difficulty: Difficulty }[] = [
  { label: 'React 前端入门', difficulty: '入门' },
  { label: 'Python 爬虫', difficulty: '初级' },
  { label: '财务报表分析', difficulty: '入门' },
  { label: '新媒体运营', difficulty: '入门' },
  { label: 'PPT 制作', difficulty: '入门' },
  { label: '机器学习实战', difficulty: '中级' },
]

/** 四步产品介绍：与「工作方式」保持同一套说法，描述精简到一行 */
const STEPS = [
  { name: '项目匹配', desc: '技术类检索 GitHub 项目，通用类由 AI 定制' },
  { name: '任务拆解 + DDL', desc: '拆成 4–6 个阶段，带交付标准与截止日' },
  { name: '双窗口答疑', desc: '右侧随时提问，自动绑定当前任务的上下文' },
  { name: '费曼复盘', desc: '用自己的话讲一遍，AI 批错补漏并生成文档' },
]

/** 进度条缓动上限：留出余量，避免长时间停在 100% 却还没完成 */
const PROGRESS_CEILING = 94

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
  const [progress, setProgress] = useState(0)
  const [elapsed, setElapsed] = useState(0)

  // 匹配进行中：驱动进度条缓动与已用时计数。
  // 匹配是 20–60 秒的黑盒请求，没有中间进度，因此用「缓动逼近 94% 并停住」
  // 给出持续的视觉反馈，而不是让进度条卡在某个假数字上。
  useEffect(() => {
    if (!loading) {
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
    const elapsedTimer = window.setInterval(() => setElapsed((s) => s + 1), 1000)

    return () => {
      window.clearInterval(progressTimer)
      window.clearInterval(elapsedTimer)
    }
  }, [loading])

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
      setProgress(100)
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

      {/* ---------- 四角导航：左上品牌标识（与功能界面一致）、右上历史项目 ---------- */}
      <div
        className="brand home-corner-brand"
        onClick={() => navigate('/')}
        role="button"
        tabIndex={0}
        onKeyDown={(event) => event.key === 'Enter' && navigate('/')}
      >
        <span className="brand-name">ProjectMentor</span>
        <span className="brand-slogan">按照需求去学习</span>
      </div>

      <nav className="home-corner-nav">
        <button type="button" className="ant-btn ant-btn-text" onClick={() => navigate('/history')}>
          <HistoryOutlined /> 历史项目
        </button>
      </nav>

      {/* ---------- 居中的搜索 Hero ---------- */}
      <main className="home-hero">
        <Reveal>
          <h1 className="display-1 home-title">
            你想学点
            <span className="gradient-text">什么</span>？
          </h1>
        </Reveal>

        {/* 四步产品介绍：替代原先的大段说明文字 */}
        <Reveal delay={1}>
          <ol className="home-steps">
            {STEPS.map((step, index) => (
              <li className="home-step" key={step.name}>
                <span className="home-step-index">{index + 1}</span>
                <span className="home-step-name">{step.name}</span>
                <span className="home-step-desc">{step.desc}</span>
              </li>
            ))}
          </ol>
        </Reveal>

        <Reveal delay={2} className="home-search-reveal">
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
        </Reveal>

        {/* 匹配中：可视化进度条，替代原先的静态提示栏 */}
        {loading && (
          <div className="home-progress">
            <div className="home-progress-head">
              <span className="mono-label mono-label-accent">正在规划学习路径</span>
              <span className="home-progress-meta">
                {Math.round(progress)}% · 已用 {elapsed}s
              </span>
            </div>
            <Progress percent={Math.round(progress)} showInfo={false} />
            <p className="home-progress-hint">
              技术类方向会检索 GitHub 开源项目并逐条评估适配度，通常需要 20–60 秒，请稍候
            </p>
          </div>
        )}
      </main>
    </div>
  )
}
