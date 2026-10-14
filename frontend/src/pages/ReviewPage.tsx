/**
 * 费曼学习法复盘页（PRD 模块 4）。
 *
 * 触发条件：全部任务完成后进入。
 * 流程：选择复盘形式 → 依据引导问题输出自己的理解 → AI 纠错补全 →
 * 生成可一键复制的最终复盘文档；右侧答疑窗口可继续就复盘内容提问。
 */

import { useCallback, useEffect, useState } from 'react'
import {
  Alert,
  App,
  Button,
  Card,
  Col,
  Collapse,
  Empty,
  Input,
  List,
  Radio,
  Row,
  Segmented,
  Space,
  Spin,
  Tag,
  Tooltip,
  Typography,
} from 'antd'
import {
  CopyOutlined,
  QuestionCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { useAppStore } from '@/store/useAppStore'
import { reviewApi } from '@/api/review'
import MarkdownView from '@/components/MarkdownView'
import type { Review, ReviewForm, ReviewGuide } from '@/api/types'

const { Paragraph, Text, Title } = Typography

export default function ReviewPage() {
  const { message } = App.useApp()
  const project = useAppStore((state) => state.project)

  const [guide, setGuide] = useState<ReviewGuide | null>(null)
  const [guideLoading, setGuideLoading] = useState(true)
  const [form, setForm] = useState<ReviewForm>('structured')
  const [content, setContent] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [review, setReview] = useState<Review | null>(null)
  const [resultTab, setResultTab] = useState<'document' | 'feedback'>('document')

  const projectId = project?.id ?? null
  const allCompleted = project?.progress?.all_completed ?? false

  // 加载复盘引导信息
  useEffect(() => {
    reviewApi
      .guide()
      .then(setGuide)
      .catch(() => undefined)
      .finally(() => setGuideLoading(false))
  }, [])

  // 进入页面时读取已有复盘记录
  useEffect(() => {
    if (!projectId) return
    reviewApi
      .latest(projectId)
      .then((data) => {
        if (data) {
          setReview(data)
          setForm(data.form)
          setContent(data.user_content)
        } else {
          setReview(null)
        }
      })
      .catch(() => undefined)
  }, [projectId])

  /** 把引导问题追加到输入框，降低用户起步难度 */
  const appendQuestion = useCallback((question: string) => {
    setContent((prev) => (prev ? `${prev}\n\n${question}\n` : `${question}\n`))
  }, [])

  const handleSubmit = useCallback(async () => {
    if (!projectId) return
    if (content.trim().length < 50) {
      message.warning('复盘内容太短了，至少写 50 字，尽量用自己的话讲清楚')
      return
    }
    setSubmitting(true)
    try {
      const result = await reviewApi.generate(projectId, form, content)
      setReview(result)
      setResultTab('document')
      message.success('复盘文档已生成')
    } catch {
      /* 错误提示已由 axios 拦截器统一处理 */
    } finally {
      setSubmitting(false)
    }
  }, [projectId, form, content, message])

  const handleCopy = useCallback(async () => {
    if (!review?.final_content) return
    try {
      await navigator.clipboard.writeText(review.final_content)
      message.success('复盘文档已复制到剪贴板')
    } catch {
      message.error('复制失败，请手动选中文本复制')
    }
  }, [review, message])

  if (!project) {
    return <Empty description="请先选择或创建一个学习项目" />
  }

  const progress = project.progress

  return (
    <div className="page">
      <Card size="small" className="review-header">
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          <Space size={10} wrap>
            <Title level={4} style={{ margin: 0 }}>
              费曼学习法 · 项目复盘
            </Title>
            <Tag>知识闭环</Tag>
            <Text type="secondary" style={{ fontSize: 12 }}>
              用自己的话讲清楚，才是真的学会了
            </Text>
          </Space>

          {!allCompleted && progress && (
            <Alert
              type="warning"
              showIcon
              message={`还有 ${progress.total - progress.done} 个任务未完成（当前进度 ${progress.percent}%）`}
              description="建议先完成全部任务再复盘，这样能讲到的内容更完整。你也可以先提前撰写复盘草稿。"
            />
          )}

          {allCompleted && (
            <Alert
              type="success"
              showIcon
              message="全部任务已完成，开始复盘吧"
              description="AI 会从「纠正理解偏差 → 补充遗漏知识点 → 优化逻辑结构 → 给出深化建议」四个维度帮你完善。"
            />
          )}
        </Space>
      </Card>

      <Row gutter={[16, 16]}>
        {/* 左：用户编辑输入区 */}
        <Col xs={24} xl={12}>
          <Card
            size="small"
            title={
              <Space>
                我的复盘
              </Space>
            }
            className="review-editor-card"
            extra={
              <Text type="secondary" style={{ fontSize: 12 }}>
                {content.length} 字
              </Text>
            }
          >
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <div>
                <Text strong style={{ fontSize: 13 }}>
                  1. 选择复盘形式
                </Text>
                {guideLoading ? (
                  <Spin size="small" />
                ) : (
                  <Radio.Group
                    value={form}
                    onChange={(event) => setForm(event.target.value as ReviewForm)}
                    style={{ display: 'block', marginTop: 8 }}
                    disabled={submitting}
                  >
                    <Space direction="vertical" size={6}>
                      {(guide?.forms ?? []).map((item) => (
                        <Radio key={item.value} value={item.value}>
                          <Space size={6}>
                            <Text>{item.label}</Text>
                            <Tooltip title={item.description}>
                              <QuestionCircleOutlined style={{ color: '#bfbfbf' }} />
                            </Tooltip>
                          </Space>
                        </Radio>
                      ))}
                    </Space>
                  </Radio.Group>
                )}
              </div>

              <div>
                <Text strong style={{ fontSize: 13 }}>
                  2. 引导问题（点击可插入到输入框）
                </Text>
                <div className="review-questions">
                  {(guide?.questions ?? []).map((question) => (
                    <Button
                      key={question}
                      size="small"
                      className="review-question-btn"
                      onClick={() => appendQuestion(question)}
                      disabled={submitting}
                    >
                      + {question}
                    </Button>
                  ))}
                </div>
              </div>

              <div>
                <Text strong style={{ fontSize: 13 }}>
                  3. 用大白话讲一遍
                </Text>
                <Input.TextArea
                  value={content}
                  onChange={(event) => setContent(event.target.value)}
                  placeholder={
                    '不要复制粘贴文档，就像给朋友讲一样写下你的理解：\n' +
                    '· 这个项目是做什么的？整体逻辑是什么？\n' +
                    '· 最难的部分是什么？你怎么攻克的？\n' +
                    '· 踩过哪些坑？有什么经验教训？\n' +
                    '· 用到哪些核心知识？分别解决了什么问题？'
                  }
                  autoSize={{ minRows: 14, maxRows: 26 }}
                  style={{ marginTop: 8 }}
                  disabled={submitting}
                />
              </div>

              <Space>
                <Button
                  type="primary"
                  loading={submitting}
                  onClick={handleSubmit}
                  disabled={!content.trim()}
                >
                  {submitting ? 'AI 正在批改…' : review ? '重新生成复盘文档' : '提交给 AI 批改'}
                </Button>
                {review && (
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={() => {
                      setContent('')
                      setReview(null)
                    }}
                    disabled={submitting}
                  >
                    重新开始
                  </Button>
                )}
              </Space>

              {submitting && (
                <Alert
                  type="info"
                  showIcon
                  message="AI 正在分析你的复盘内容"
                  description="将生成完整复盘文档，通常需要 30-90 秒，请勿关闭页面。"
                />
              )}
            </Space>
          </Card>
        </Col>

        {/* 右：AI 优化后的结果 */}
        <Col xs={24} xl={12}>
          <Card
            size="small"
            title={
              <Space>
                AI 优化后的复盘文档
              </Space>
            }
            className="review-result-card"
            extra={
              review && (
                <Space size={6}>
                  <Segmented
                    size="small"
                    value={resultTab}
                    onChange={(value) => setResultTab(value as 'document' | 'feedback')}
                    options={[
                      { label: '最终文档', value: 'document' },
                      { label: '批改意见', value: 'feedback' },
                    ]}
                  />
                  <Button
                    size="small"
                    type="primary"
                    icon={<CopyOutlined />}
                    onClick={handleCopy}
                  >
                    一键复制
                  </Button>
                </Space>
              )
            }
          >
            {!review ? (
              <div className="review-empty">
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={
                    <span>
                      还没有复盘结果
                      <br />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        在左侧写下你的理解，提交后 AI 会在这里生成完整文档
                      </Text>
                    </span>
                  }
                />
              </div>
            ) : resultTab === 'document' ? (
              <div className="review-document">
                <MarkdownView content={review.final_content} />
              </div>
            ) : (
              <div className="review-feedback">
                <Collapse
                  defaultActiveKey={['corrections', 'supplements', 'next']}
                  ghost
                  items={[
                    {
                      key: 'corrections',
                      label: (
                        <Space>
                          <Text strong>理解纠错</Text>
                          <Tag>{review.corrections.length}</Tag>
                        </Space>
                      ),
                      children:
                        review.corrections.length > 0 ? (
                          <List
                            size="small"
                            dataSource={review.corrections}
                            renderItem={(item) => <List.Item>{item}</List.Item>}
                          />
                        ) : (
                          <Text type="secondary">没有发现明显的理解错误</Text>
                        ),
                    },
                    {
                      key: 'supplements',
                      label: (
                        <Space>
                          <Text strong>知识点补全</Text>
                          <Tag>{review.supplements.length}</Tag>
                        </Space>
                      ),
                      children:
                        review.supplements.length > 0 ? (
                          <List
                            size="small"
                            dataSource={review.supplements}
                            renderItem={(item) => <List.Item>{item}</List.Item>}
                          />
                        ) : (
                          <Text type="secondary">暂无补充</Text>
                        ),
                    },
                    {
                      key: 'structure',
                      label: (
                        <Space>
                          <Text strong>结构与表达建议</Text>
                        </Space>
                      ),
                      children: (
                        <Paragraph style={{ marginBottom: 0 }}>
                          {review.structure_advice || '暂无建议'}
                        </Paragraph>
                      ),
                    },
                    {
                      key: 'next',
                      label: (
                        <Space>
                          <Text strong>下一步深化学习</Text>
                          <Tag>{review.next_steps.length}</Tag>
                        </Space>
                      ),
                      children: (
                        <List
                          size="small"
                          dataSource={review.next_steps}
                          renderItem={(item) => <List.Item>{item}</List.Item>}
                        />
                      ),
                    },
                  ]}
                />
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}
