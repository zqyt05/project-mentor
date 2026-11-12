/**
 * 项目资料库（RAG 的资料管理）。
 *
 * 作用：把课程讲义、行业报告、自己的笔记上传到项目里，
 * 右侧答疑窗口回答时会先检索这些资料，并标注引用了哪一份。
 *
 * 设计说明：
 * - 上传后立即解析 + 分块 + 向量化，所以列表能看到「N 个片段」
 * - 向量模型不可用时自动降级为关键词检索，界面如实提示，功能不中断
 * - 检索预览让用户自己确认「AI 到底看到了什么」，避免 RAG 变成黑盒
 */

import { useCallback, useEffect, useState } from 'react'
import { Alert, App, Button, Empty, Popconfirm, Space, Table, Tag, Typography, Upload } from 'antd'
import {
  DeleteOutlined,
  FileTextOutlined,
  InboxOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import { useParams } from 'react-router-dom'
import { knowledgeApi, type KnowledgeOverview } from '@/api/knowledge'

const { Text, Title } = Typography

interface SearchHit {
  filename: string
  chunk_index: number
  score: number
  content: string
}

export default function KnowledgePage() {
  const { message } = App.useApp()
  const { projectId: rawProjectId } = useParams<{ projectId: string }>()
  const projectId = Number(rawProjectId)

  const [overview, setOverview] = useState<KnowledgeOverview | null>(null)
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)

  // 检索预览
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState<SearchHit[] | null>(null)
  const [searching, setSearching] = useState(false)

  const load = useCallback(async () => {
    if (!projectId) return
    setLoading(true)
    try {
      setOverview(await knowledgeApi.list(projectId))
    } catch {
      /* 错误提示由 axios 拦截器统一处理 */
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    void load()
  }, [load])

  const handleUpload = async (file: File) => {
    setUploading(true)
    try {
      await knowledgeApi.upload(projectId, file)
      message.success(`已索引：${file.name}`)
      await load()
    } catch {
      /* 已提示 */
    } finally {
      setUploading(false)
    }
    return false // 阻止 antd 默认上传行为
  }

  const handleDelete = async (documentId: number) => {
    await knowledgeApi.remove(projectId, documentId)
    message.success('已删除')
    setHits(null)
    await load()
  }

  const handleSearch = async () => {
    if (!query.trim()) return
    setSearching(true)
    try {
      const result = await knowledgeApi.search(projectId, query.trim())
      setHits(result.sources)
    } catch {
      /* 已提示 */
    } finally {
      setSearching(false)
    }
  }

  const docs = overview?.documents ?? []
  const semantic = overview?.semantic_search ?? false

  return (
    <div className="page">
      <div className="tasks-header">
        <Space direction="vertical" size={4} style={{ width: '100%' }}>
          <Title level={4} style={{ margin: 0 }}>
            项目资料库
          </Title>
          <Text type="secondary" style={{ fontSize: '0.86rem' }}>
            把课程讲义、行业报告或自己的笔记放进来。右侧答疑窗口回答前会先检索这些资料，
            并在回答里标注引用了哪一份 —— 让回答从「凭印象」变成「有据可查」。
          </Text>
        </Space>
      </div>

      {/* 检索方式提示：降级时如实告知，不让用户以为在语义检索 */}
      <Alert
        type={semantic ? 'info' : 'warning'}
        showIcon
        message={
          semantic
            ? '语义检索已启用：按意思匹配，问法和原文不一样也能找到'
            : '当前为关键词检索：向量模型未就绪（需联网下载约 91MB），按字面匹配，效果弱一些'
        }
        description={
          semantic
            ? undefined
            : '不影响使用。若想启用语义检索，确认能访问 hf-mirror.com 后重启后端即可自动下载模型。'
        }
      />

      {/* 上传区 */}
      <Upload.Dragger
        multiple={false}
        showUploadList={false}
        disabled={uploading}
        accept={(overview?.supported_types ?? []).map((type) => `.${type}`).join(',')}
        beforeUpload={(file) => handleUpload(file as File)}
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">
          {uploading ? '正在解析并建立索引…' : '点击或拖拽文件到这里上传'}
        </p>
        <p className="ant-upload-hint">
          支持 {(overview?.supported_types ?? []).join(' / ')}，
          单个文件不超过 {overview?.max_size_mb ?? 5} MB。扫描版 PDF（纯图片）需要先做 OCR。
        </p>
      </Upload.Dragger>

      {/* 资料列表 */}
      {docs.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={loading ? '正在加载…' : '还没有上传资料'}
        />
      ) : (
        <Table
          size="small"
          rowKey="id"
          pagination={false}
          dataSource={docs}
          columns={[
            {
              title: '文件',
              dataIndex: 'filename',
              render: (name: string, row) => (
                <Space size={8}>
                  <FileTextOutlined />
                  <Text>{name}</Text>
                  <Tag>{row.file_type}</Tag>
                  {!row.embedded && <Tag>关键词检索</Tag>}
                </Space>
              ),
            },
            {
              title: '内容量',
              width: 160,
              render: (_, row) => (
                <Text type="secondary" style={{ fontSize: '0.82rem' }}>
                  {row.char_count.toLocaleString()} 字 · {row.chunk_count} 个片段
                </Text>
              ),
            },
            {
              title: '',
              width: 60,
              align: 'right' as const,
              render: (_, row) => (
                <Popconfirm
                  title="删除这份资料？"
                  description="它会从检索库中移除，已生成的回答不受影响。"
                  okText="删除"
                  cancelText="取消"
                  okButtonProps={{ danger: true }}
                  onConfirm={() => handleDelete(row.id)}
                >
                  <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              ),
            },
          ]}
        />
      )}

      {/* 检索预览：让用户确认 AI 到底能检索到什么 */}
      {docs.length > 0 && (
        <div className="tasks-header">
          <Space direction="vertical" size={10} style={{ width: '100%' }}>
            <Space.Compact style={{ width: '100%' }}>
              <input
                className="home-search-input"
                style={{
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius) 0 0 var(--radius)',
                  padding: '0 14px',
                  height: 42,
                }}
                placeholder="输入一个问题，看看会检索到哪些片段（不会调用 AI）"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => event.key === 'Enter' && handleSearch()}
              />
              <Button
                type="primary"
                icon={<SearchOutlined />}
                loading={searching}
                onClick={handleSearch}
              >
                检索预览
              </Button>
            </Space.Compact>

            {hits !== null &&
              (hits.length === 0 ? (
                <Text type="secondary">
                  没有匹配到内容。相关度低于阈值时不会硬塞进上下文，避免干扰回答。
                </Text>
              ) : (
                <Space direction="vertical" size={10} style={{ width: '100%' }}>
                  {hits.map((hit, index) => (
                    <div key={`${hit.filename}-${hit.chunk_index}`} className="task-criteria">
                      <Space size={8} style={{ marginBottom: 6 }}>
                        <Text strong style={{ fontSize: '0.82rem' }}>
                          资料{index + 1}
                        </Text>
                        <Tag>{hit.filename}</Tag>
                        <Text type="secondary" style={{ fontSize: '0.76rem' }}>
                          片段 {hit.chunk_index + 1} · 相关度 {hit.score}
                        </Text>
                      </Space>
                      <div style={{ fontSize: '0.84rem', lineHeight: 1.7 }}>{hit.content}</div>
                    </div>
                  ))}
                </Space>
              ))}
          </Space>
        </div>
      )}
    </div>
  )
}
