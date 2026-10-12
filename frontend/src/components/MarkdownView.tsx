/** Markdown 渲染组件：统一处理 AI 回答、任务描述、复盘文档的格式化展示。 */

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import 'highlight.js/styles/github.css'
import { Typography } from 'antd'

interface MarkdownViewProps {
  content: string
  /** 紧凑模式：用于卡片内的简短描述 */
  compact?: boolean
}

/**
 * 渲染 Markdown 文本，支持 GFM 表格、代码高亮。
 * 说明：不启用 raw HTML，避免 XSS 风险。
 */
export default function MarkdownView({ content, compact = false }: MarkdownViewProps) {
  return (
    <div className={compact ? 'markdown-body markdown-compact' : 'markdown-body'}>
      <Typography>
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeHighlight]}
          components={{
            // 让代码块可横向滚动，避免撑破分栏布局
            pre: ({ children }) => <pre className="md-pre">{children}</pre>,
            a: ({ children, href }) => (
              <a href={href} target="_blank" rel="noreferrer noopener">
                {children}
              </a>
            ),
          }}
        >
          {content}
        </ReactMarkdown>
      </Typography>
    </div>
  )
}
