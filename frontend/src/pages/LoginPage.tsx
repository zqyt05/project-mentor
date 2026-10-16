/**
 * 演示口令登录页。
 *
 * 仅在开启演示门禁（后端配置了 DEMO_PASSWORD）时出现。
 * 视觉沿用首页那套：径向辉光 + 旋转装饰环 + 渐变 CTA。
 */

import { useState } from 'react'
import { Alert } from 'antd'
import { ArrowRightOutlined, LockOutlined } from '@ant-design/icons'
import { useAuthStore } from '@/store/useAuthStore'

export default function LoginPage() {
  const login = useAuthStore((state) => state.login)
  const error = useAuthStore((state) => state.error)

  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async () => {
    if (!password.trim() || submitting) return
    setSubmitting(true)
    await login(password.trim())
    setSubmitting(false)
  }

  return (
    <div className="home-shell">
      <div className="home-decor" aria-hidden="true">
        <span className="glow home-glow-1" />
        <span className="glow home-glow-2" />
        <span className="home-ring spin-slow" />
        <span className="home-ring-inner" />
      </div>

      <div className="brand home-corner-brand">
        <span className="brand-name">ProjectMentor</span>
        <span className="brand-slogan">按照需求去学习</span>
      </div>

      <main className="home-hero">
        <span className="section-badge" style={{ marginBottom: 24 }}>
          <span className="pulse-dot" />
          <span className="section-badge-text">小范围试用</span>
        </span>

        <h1 className="display-1 home-title" style={{ marginBottom: 16 }}>
          请输入
          <span className="gradient-text">试用口令</span>
        </h1>

        <p className="home-subtitle" style={{ marginBottom: 32 }}>
          这是分享给朋友的试用环境。输入口令后，你的项目会独立保存，
          不会与其他试用者互相看到。
        </p>

        <div className="home-search" style={{ maxWidth: 480 }}>
          <span style={{ color: 'var(--muted-foreground)', display: 'flex' }}>
            <LockOutlined />
          </span>
          <input
            className="home-search-input"
            type="password"
            placeholder="请输入口令"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            onKeyDown={(event) => event.key === 'Enter' && handleSubmit()}
            autoFocus
            aria-label="试用口令"
          />
          <button
            type="button"
            className="home-search-btn"
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? '验证中…' : '进入试用'}
            {!submitting && <ArrowRightOutlined />}
          </button>
        </div>

        {error && (
          <Alert
            style={{ marginTop: 20, maxWidth: 480, width: '100%', textAlign: 'left' }}
            type="error"
            showIcon
            message={error}
          />
        )}

        <p className="home-progress-hint" style={{ marginTop: 28, maxWidth: 480 }}>
          提示：试用环境由分享者的本机提供，AI 生成一次完整项目需要 1–2 分钟。
          清除浏览器 Cookie 会失去对自己项目的访问。
        </p>
      </main>
    </div>
  )
}
