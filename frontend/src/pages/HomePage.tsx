/**
 * 首页：输入学习方向 + 选择难度（PRD 模块 1 · 输入）。
 *
 * 提交后系统自动判断领域类型，选择最优路径生成实战项目选项。
 */

import { useState } from 'react'
import { Alert, App, Button, Card, Col, Radio, Row, Space, Tag, Typography } from 'antd'
import { ExperimentOutlined, RocketOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { projectApi } from '@/api/project'
import { useMatchStore } from '@/store/useMatchStore'
import type { Difficulty } from '@/api/types'

const { Paragraph, Text, Title } = Typography

/** 示例方向：覆盖技术类与通用类，帮助用户理解产品能力边界 */
const EXAMPLES: { label: string; difficulty: Difficulty }[] = [
  { label: 'React 前端入门', difficulty: '入门' },
  { label: 'Python 爬虫', difficulty: '初级' },
  { label: '财务报表分析', difficulty: '入门' },
  { label: '新媒体运营', difficulty: '入门' },
  { label: 'PPT 制作', difficulty: '入门' },
  { label: '机器学习实战', difficulty: '中级' },
]

const FLOW_STEPS = [
  { title: '项目匹配', desc: '技术类检索 GitHub 优质开源项目；通用类由 AI 定制实战项目' },
  { title: '任务拆解 + DDL', desc: '拆成 4-6 个阶段任务，每个任务带知识点、交付标准和截止日期' },
  { title: '双窗口答疑', desc: '右侧导师窗口自动绑定当前任务，答疑不会冲掉左侧任务记录' },
  { title: '费曼复盘', desc: '用自己的话讲一遍，AI 纠错补全并生成可展示的复盘文档' },
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
    <div className="page home-page">
      <Card className="home-hero">
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <div className="home-title-block">
            <ThunderboltOutlined className="home-title-icon" />
            <div>
              <Title level={2} style={{ margin: 0 }}>
                你想学点什么？
              </Title>
              <Paragraph type="secondary" style={{ margin: 0, fontSize: 15 }}>
                输入任意学习方向，我会帮你匹配一个能真正上手做完的实战项目
              </Paragraph>
            </div>
          </div>

          <div className="home-input">
            <input
              className="home-input-field"
              placeholder="例如：React 前端入门 / 财务报表分析 / 新媒体运营"
              value={localDomain}
              onChange={(event) => setLocalDomain(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') void handleSubmit()
              }}
              disabled={loading}
            />
          </div>

          <Space size={12} wrap align="center">
            <Space size={8}>
              <Text strong>难度</Text>
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
            </Space>

            <Button
              type="primary"
              size="large"
              icon={<RocketOutlined />}
              loading={loading}
              onClick={handleSubmit}
            >
              {loading ? 'AI 正在匹配项目…' : '开始匹配项目'}
            </Button>
          </Space>

          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              试试这些方向：
            </Text>
            <div className="home-examples">
              {EXAMPLES.map((example) => (
                <Tag
                  key={example.label}
                  className="home-example-tag"
                  onClick={() => {
                    setLocalDomain(example.label)
                    setLocalDifficulty(example.difficulty)
                  }}
                >
                  {example.label}
                </Tag>
              ))}
            </div>
          </div>

          {loading && (
            <Alert
              type="info"
              showIcon
              message="正在为你规划学习路径"
              description="技术类方向会检索 GitHub 开源项目并逐条评估适配度，通常需要 20-60 秒，请稍候。"
            />
          )}
        </Space>
      </Card>

      <Row gutter={[16, 16]} className="home-flow">
        {FLOW_STEPS.map((step, index) => (
          <Col xs={24} sm={12} lg={6} key={step.title}>
            <Card size="small" className="home-flow-card">
              <Space direction="vertical" size={6}>
                <Space size={8}>
                  <span className="home-flow-index">{index + 1}</span>
                  <Text strong>{step.title}</Text>
                </Space>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {step.desc}
                </Text>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>

      <Card size="small" className="home-note">
        <Space direction="vertical" size={4}>
          <Text strong>
            <ExperimentOutlined /> 关于这个工具
          </Text>
          <Text type="secondary" style={{ fontSize: 13 }}>
            它复刻的是企业导师带教的逻辑：不是给你一份系统性的课程大纲，而是直接丢给你一个项目，
            陪你拆任务、定 DDL、随时答疑，最后逼你用自己的话讲一遍。
            单用户本地使用，所有数据保存在本机 SQLite，不涉及账号与云端同步。
          </Text>
        </Space>
      </Card>
    </div>
  )
}
