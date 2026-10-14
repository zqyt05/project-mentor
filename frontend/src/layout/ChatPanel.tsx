/**
 * 右侧独立答疑子窗口（PRD 模块 3 · 双窗口隔离式场景化答疑）。
 *
 * 隔离设计：
 * - 本组件所有状态（消息、加载中、输入框）都独立于左侧主窗口，
 *   提问 / 刷新 / 清空都不会触发主窗口内容变化。
 * - 顶部始终显示当前绑定的任务名称，让用户明确「现在在问哪个任务」。
 * - 切换任务时按 task_id 重新加载该任务独立的对话历史，上下文互不干扰。
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Alert, App, Button, Empty, Input, Spin, Tag, Typography } from 'antd'
import { ClearOutlined, SendOutlined } from '@ant-design/icons'
import { chatApi } from '@/api/chat'
import MessageBubble from '@/components/MessageBubble'
import { useAppStore } from '@/store/useAppStore'
import type { ChatScope } from '@/api/types'

const { Text } = Typography

export default function ChatPanel() {
  const { message: toast, modal } = App.useApp()
  const project = useAppStore((state) => state.project)
  const mainView = useAppStore((state) => state.mainView)
  const activeTaskId = useAppStore((state) => state.activeTaskId)

  const messages = useAppStore((state) => state.messages)
  const chatLoading = useAppStore((state) => state.chatLoading)
  const quickPrompts = useAppStore((state) => state.quickPrompts)
  const setMessages = useAppStore((state) => state.setMessages)
  const appendMessages = useAppStore((state) => state.appendMessages)
  const setChatLoading = useAppStore((state) => state.setChatLoading)
  const setQuickPrompts = useAppStore((state) => state.setQuickPrompts)
  const resetChat = useAppStore((state) => state.resetChat)

  const [question, setQuestion] = useState('')
  const [historyLoading, setHistoryLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // 复盘页使用 review 作用域，其余页面绑定具体任务
  const scope: ChatScope = mainView === 'review' ? 'review' : 'task'
  const taskId = scope === 'task' ? activeTaskId : null
  const projectId = project?.id ?? null

  /** 当前绑定的任务（用于顶部标题展示） */
  const activeTask = useMemo(
    () => project?.tasks.find((task) => task.id === activeTaskId) ?? null,
    [project, activeTaskId],
  )

  const canChat = Boolean(projectId) && (scope === 'review' || Boolean(taskId))

  // ------------------------------------------------------------------
  // 加载对应任务 / 复盘的独立对话历史
  // ------------------------------------------------------------------
  useEffect(() => {
    let cancelled = false

    if (!projectId || !canChat) {
      resetChat()
      return
    }

    setHistoryLoading(true)
    resetChat()
    chatApi
      .history(projectId, scope, taskId)
      .then((history) => {
        if (cancelled) return
        setMessages(history.messages)
        setQuickPrompts(history.quick_prompts)
      })
      .catch(() => {
        /* 错误提示已由 axios 拦截器统一处理 */
      })
      .finally(() => {
        if (!cancelled) setHistoryLoading(false)
      })

    return () => {
      cancelled = true
    }
    // 任务切换 / 项目切换 / 作用域变化时重新加载上下文
  }, [projectId, taskId, scope, canChat, resetChat, setMessages, setQuickPrompts])

  // 新消息到达时滚动到底部
  useEffect(() => {
    const node = scrollRef.current
    if (node) {
      node.scrollTop = node.scrollHeight
    }
  }, [messages, chatLoading])

  // ------------------------------------------------------------------
  // 发送提问
  // ------------------------------------------------------------------
  const handleSend = useCallback(
    async (text: string) => {
      const content = text.trim()
      if (!content || !projectId || !canChat) return

      setQuestion('')
      setChatLoading(true)
      // 乐观展示用户提问，保证输入后立刻有反馈
      const optimistic = {
        id: Date.now(),
        role: 'user' as const,
        content,
        created_at: new Date().toISOString(),
      }
      appendMessages([optimistic])

      try {
        const result = await chatApi.ask({
          project_id: projectId,
          task_id: taskId,
          scope,
          question: content,
        })
        // 用服务端返回的真实消息替换乐观消息，保证 id / 时间戳准确
        setMessages([
          ...useAppStore.getState().messages.filter((item) => item.id !== optimistic.id),
          ...result.messages,
        ])
      } catch {
        // 失败时移除乐观消息，避免出现「问了但没有回答」的错觉
        setMessages(useAppStore.getState().messages.filter((item) => item.id !== optimistic.id))
        setQuestion(content)
      } finally {
        setChatLoading(false)
      }
    },
    [
      projectId,
      taskId,
      scope,
      canChat,
      appendMessages,
      setMessages,
      setChatLoading,
    ],
  )

  const handleClear = useCallback(() => {
    if (!projectId) return
    modal.confirm({
      title: '清空当前对话？',
      content: '仅清空当前任务的答疑记录，其他任务与左侧学习进度不受影响。',
      okText: '清空',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        await chatApi.clear(projectId, scope, taskId)
        setMessages([])
        toast.success('已清空当前任务的对话')
      },
    })
  }, [projectId, scope, taskId, modal, setMessages, toast])

  // ------------------------------------------------------------------
  // 渲染
  // ------------------------------------------------------------------
  return (
    <aside className="chat-panel">
      <div className="chat-header">
        <div className="chat-header-main">
          <span className="chat-title">答疑窗口</span>
          <Button
            type="text"
            size="small"
            icon={<ClearOutlined />}
            onClick={handleClear}
            disabled={!canChat || messages.length === 0}
            title="清空当前任务的对话"
            aria-label="清空当前任务的对话"
          />
        </div>
        <div className="chat-header-context">
          {scope === 'review' ? (
            <Tag color="purple" style={{ marginInlineEnd: 0 }}>
              上下文：项目复盘
            </Tag>
          ) : activeTask ? (
            <Tag color="blue" style={{ marginInlineEnd: 0, maxWidth: '100%' }}>
              <span className="chat-context-name">上下文：{activeTask.name}</span>
            </Tag>
          ) : (
            <Tag style={{ marginInlineEnd: 0 }}>未绑定任务</Tag>
          )}
        </div>
      </div>

      <div className="chat-body" ref={scrollRef}>
        {!canChat ? (
          <div className="chat-empty">
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={
                <span>
                  请先在左侧选择一个项目与任务
                  <br />
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    答疑会自动绑定当前任务的项目背景与技术栈
                  </Text>
                </span>
              }
            />
          </div>
        ) : historyLoading ? (
          <div className="chat-empty">
            <Spin tip="正在加载该任务的对话记录…">
              <div style={{ height: 60 }} />
            </Spin>
          </div>
        ) : messages.length === 0 ? (
          <div className="chat-empty">
            <Alert
              type="info"
              showIcon
              message="导师已就位"
              description={
                scope === 'review'
                  ? '针对你的复盘内容提问，我会帮你把知识点讲透。'
                  : `已加载「${activeTask?.name ?? ''}」的项目背景、任务要求与交付标准，遇到问题随时问我。`
              }
            />
          </div>
        ) : (
          messages.map((item) => <MessageBubble key={item.id} message={item} />)
        )}

        {chatLoading && (
          <div className="msg-row msg-row-assistant">
            <div className="msg-bubble msg-bubble-assistant">
              <Spin size="small" /> <Text type="secondary">导师正在思考…</Text>
            </div>
          </div>
        )}
      </div>

      <div className="chat-footer">
        {canChat && quickPrompts.length > 0 && (
          <div className="chat-quick">
            {quickPrompts.map((prompt) => (
              <Button
                key={prompt}
                size="small"
                className="chat-quick-btn"
                disabled={chatLoading}
                onClick={() => handleSend(prompt)}
              >
                {prompt}
              </Button>
            ))}
          </div>
        )}

        <div className="chat-input">
          <Input.TextArea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder={
              canChat
                ? scope === 'review'
                  ? '就复盘内容提问，例如：我哪部分理解得不对？'
                  : '描述你遇到的问题，例如：这一步报错了…'
                : '请先在左侧选择任务'
            }
            autoSize={{ minRows: 2, maxRows: 5 }}
            disabled={!canChat || chatLoading}
            onPressEnter={(event) => {
              // Enter 发送，Shift+Enter 换行
              if (!event.shiftKey) {
                event.preventDefault()
                void handleSend(question)
              }
            }}
          />
          <div className="chat-input-actions">
            <Text type="secondary" style={{ fontSize: 11 }}>
              Enter 发送 · Shift+Enter 换行
            </Text>
            <Button
              type="primary"
              icon={<SendOutlined />}
              loading={chatLoading}
              disabled={!canChat || !question.trim()}
              onClick={() => void handleSend(question)}
              aria-label="发送"
              title="发送"
            />
          </div>
        </div>
      </div>
    </aside>
  )
}
