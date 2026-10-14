/**
 * 首页（PRD 模块 1 · 输入）。
 *
 * 新闻纸风格：巨大的衬线标题主导视口，下方是「报头式」的输入区，
 * 再往下是以 STEP 1–4 竖向排列的流程说明。
 *
 * 按需求调整：去掉了标题前的闪电图标与「开始匹配项目」的火箭图标，
 * 减少了口号式的堆砌文案，四个环节改为竖排并明确标注 STEP 编号。
 */

import { useState } from 'react'
import { Alert, App, Radio, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import { projectApi } from '@/api/project'
import { useMatchStore } from '@/store/useMatchStore'
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

/** 四个环节：竖向排版，明确编号 */
const FLOW_STEPS = [
  {
    step: 'STEP 1',
    title: '项目匹配',
    desc: '技术类方向检索 GitHub 优质开源项目并按适配度排序；通用类方向由 AI 定制有明确交付物的实战项目。',
  },
  {
    step: 'STEP 2',
    title: '任务拆解 + DDL',
    desc: '拆成 4–6 个阶段任务，每个任务带需掌握的知识点、可判断的交付标准和截止日期。',
  },
  {
    step: 'STEP 3',
    title: '双窗口答疑',
    desc: '右侧答疑窗口自动绑定当前任务的项目背景，且永远不会冲掉左侧的任务记录。',
  },
  {
    step: 'STEP 4',
    title: '费曼复盘',
    desc: '用自己的话讲一遍项目，AI 从纠错、补全、结构、深化四个维度批改并生成可展示的复盘文档。',
  },
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
    <div className="page">
      {/* ---------- 报头式主标题区 ---------- */}
      <section className="home-masthead newsprint-texture">
        <div className="home-kicker">
          <span className="np-label np-label-red">实战学习</span>
          <span className="np-label">
            {dayjs().format('YYYY.MM.DD')} · 第 1 卷
          </span>
        </div>

        <h1 className="np-h1">你想学点什么？</h1>

        <p className="home-lede">
          输入任意学习方向，我会帮你匹配一个能真正上手做完的实战项目 ——
          不是给你一份课程大纲，而是直接丢给你一个项目，陪你拆任务、定 DDL、随时答疑。
        </p>

        {/* 输入区：2px 墨框 + 黑色动作块 */}
        <div className="home-input-row">
          <input
            className="home-input-field"
            placeholder="例如：React 前端入门 / 财务报表分析 / 新媒体运营"
            value={localDomain}
            onChange={(event) => setLocalDomain(event.target.value)}
            disabled={loading}
            aria-label="学习方向"
          />
          <button className="home-go" onClick={handleSubmit} disabled={loading} type="button">
            {loading ? '匹配中…' : '开始匹配项目'}
          </button>
        </div>

        <div className="home-examples">
          <span className="np-label" style={{ marginRight: 10, alignSelf: 'center' }}>
            试试
          </span>
          {EXAMPLES.map((example) => (
            <span
              key={example.label}
              className="home-example-tag"
              role="button"
              tabIndex={0}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  setLocalDomain(example.label)
                  setLocalDifficulty(example.difficulty)
                }
              }}
              onClick={() => {
                setLocalDomain(example.label)
                setLocalDifficulty(example.difficulty)
              }}
            >
              {example.label}
            </span>
          ))}
        </div>

        <div style={{ marginTop: 18, display: 'flex', alignItems: 'center', gap: 12 }}>
          <span className="np-label">难度</span>
          <Radio.Group
            value={localDifficulty}
            onChange={(event) => setLocalDifficulty(event.target.value as Difficulty)}
            optionType="button"
            buttonStyle="solid"
            disabled={loading}
          >
            <Radio.Button value="入门">入门</Radio.Button>
            <Radio.Button value="初级">初级</Radio.Button>
            <Radio.Button value="中级">中级</Radio.Button>
          </Radio.Group>
        </div>

        {loading && (
          <Alert
            style={{ marginTop: 16 }}
            type="info"
            showIcon
            message="正在为你规划学习路径"
            description="技术类方向会检索 GitHub 开源项目并逐条评估适配度，通常需要 20–60 秒，请稍候。"
          />
        )}
      </section>

      {/* ---------- STEP 1–4：竖向排版 ---------- */}
      <section>
        <div className="np-block-head" style={{ border: '1px solid #111111', borderBottom: 'none' }}>
          <span className="np-label np-label-ink">工作方式</span>
          <span className="np-label">四个环节</span>
        </div>
        <div className="step-list">
          {FLOW_STEPS.map((item) => (
            <div className="step-item" key={item.step}>
              <div className="step-item-index">{item.step}</div>
              <div className="step-item-body">
                <span className="step-item-title">{item.title}</span>
                <span className="step-item-desc">{item.desc}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ---------- 反转区域：关于这个工具 ---------- */}
      <section className="np-inverted home-about">
        <div className="home-about-title">关于这个工具</div>
        <p className="home-about-text">
          它复刻的是企业导师带教的逻辑：不是给你一份系统性的课程大纲，而是直接丢给你一个项目，
          陪你拆任务、定 DDL、随时答疑，最后逼你用自己的话讲一遍。
        </p>
        <p className="home-about-text" style={{ marginTop: 8 }}>
          <Text style={{ color: '#A3A3A3', fontSize: '0.8rem' }}>
            单用户本地使用 · 所有数据保存在本机 SQLite · 不涉及账号与云端同步
          </Text>
        </p>
      </section>
    </div>
  )
}
