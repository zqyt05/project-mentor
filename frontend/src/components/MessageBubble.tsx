/**
 * 对话气泡组件。
 * 区分用户 / 导师两种角色，导师回答使用 Markdown 渲染并支持代码高亮。
 */

import { Avatar, Space, Tag, Typography } from 'antd'
import { RobotOutlined, UserOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import MarkdownView from '@/components/MarkdownView'
import type { ChatMessage } from '@/api/types'

const { Text } = Typography

interface MessageBubbleProps {
  message: ChatMessage
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`msg-row ${isUser ? 'msg-row-user' : 'msg-row-assistant'}`}>
      <Avatar
        size={28}
        icon={isUser ? <UserOutlined /> : <RobotOutlined />}
        className={isUser ? 'msg-avatar-user' : 'msg-avatar-assistant'}
      />
      <div className="msg-body">
        <Space size={6} className="msg-meta">
          <Text strong style={{ fontSize: 12 }}>
            {isUser ? '我' : '带教导师'}
          </Text>
          {!isUser && (
            <Tag color="blue" style={{ marginInlineEnd: 0, fontSize: 10, lineHeight: '16px' }}>
              场景化答疑
            </Tag>
          )}
          <Text type="secondary" style={{ fontSize: 11 }}>
            {dayjs(message.created_at).format('HH:mm')}
          </Text>
        </Space>
        <div className={`msg-bubble ${isUser ? 'msg-bubble-user' : 'msg-bubble-assistant'}`}>
          {isUser ? (
            <span className="msg-plain-text">{message.content}</span>
          ) : (
            <MarkdownView content={message.content} />
          )}
        </div>
      </div>
    </div>
  )
}
