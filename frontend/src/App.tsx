/**
 * 应用根组件：路由配置 + 全局主题。
 *
 * 主题对应「电光蓝 + 双字体」设计系统：主色 #0052FF、圆角 12/16、柔和分层阴影。
 * 具体的视觉细节（渐变、纹理、动画等）在 index.css 中实现，
 * 此处只设置 Ant Design 的 token，避免全局样式散落两处。
 *
 * 同时承担演示门禁的入口判断：门禁开启且未验证时渲染登录页。
 */

import { useEffect } from 'react'
import { App as AntdApp, ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { Navigate, Route, Routes } from 'react-router-dom'
import { BrowserRouter } from 'react-router-dom'
import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'
import MainLayout from '@/layout/MainLayout'
import HomePage from '@/pages/HomePage'
import LoginPage from '@/pages/LoginPage'
import { useAuthStore } from '@/store/useAuthStore'
import MatchPage from '@/pages/MatchPage'
import OverviewPage from '@/pages/OverviewPage'
import TasksPage from '@/pages/TasksPage'
import ReviewPage from '@/pages/ReviewPage'
import HistoryPage from '@/pages/HistoryPage'

dayjs.locale('zh-cn')

/** 设计令牌（与 index.css 中的 CSS 变量保持一致） */
const BACKGROUND = '#FAFAFA'
const FOREGROUND = '#0F172A'
const MUTED_FOREGROUND = '#64748B'
const ACCENT = '#0052FF'
const BORDER = '#E2E8F0'
const CARD = '#FFFFFF'

const FONT_SANS = "'Inter', system-ui, -apple-system, 'PingFang SC', sans-serif"

export default function App() {
  const ready = useAuthStore((state) => state.ready)
  const authenticated = useAuthStore((state) => state.authenticated)
  const bootstrap = useAuthStore((state) => state.bootstrap)

  // 启动时探测门禁状态（未开启门禁时一次请求即完成，不影响本地体验）
  useEffect(() => {
    void bootstrap()
  }, [bootstrap])

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: ACCENT,
          colorInfo: ACCENT,
          colorLink: ACCENT,
          colorText: FOREGROUND,
          colorTextHeading: FOREGROUND,
          colorTextSecondary: MUTED_FOREGROUND,
          colorBgBase: BACKGROUND,
          colorBgContainer: CARD,
          colorBgElevated: CARD,
          colorBorder: BORDER,
          colorBorderSecondary: BORDER,
          colorError: '#EF4444',
          colorSuccess: '#10B981',
          colorWarning: '#F59E0B',
          // 圆角：modern soft UI
          borderRadius: 12,
          borderRadiusLG: 16,
          borderRadiusSM: 8,
          borderRadiusXS: 6,
          // 分层阴影交给 CSS，这里只保证 AntD 默认不带重描边
          fontFamily: FONT_SANS,
          fontSize: 15,
          lineHeight: 1.625,
          controlHeight: 38,
          wireframe: false,
        },
        components: {
          Card: { borderRadiusLG: 16, paddingLG: 22 },
          Button: {
            borderRadius: 12,
            borderRadiusLG: 12,
            borderRadiusSM: 8,
            primaryShadow: 'none',
            defaultShadow: 'none',
            dangerShadow: 'none',
            fontWeight: 500,
          },
          Input: { borderRadius: 12, activeShadow: 'none' },
          Progress: { defaultColor: ACCENT, remainingColor: '#F1F5F9' },
          Tag: { borderRadiusSM: 999 },
          Menu: {
            itemBorderRadius: 12,
            itemSelectedBg: ACCENT,
            itemSelectedColor: '#FFFFFF',
            itemHoverBg: '#F1F5F9',
            itemColor: MUTED_FOREGROUND,
          },
          Modal: { borderRadiusLG: 20 },
          Alert: { borderRadiusLG: 12 },
          Segmented: { borderRadius: 12, itemSelectedBg: CARD, itemSelectedColor: ACCENT },
          Collapse: { borderRadiusLG: 12, headerPadding: '12px 16px' },
        },
      }}
    >
      {/* AntdApp 提供 message / modal 的静态方法上下文 */}
      <AntdApp>
        {!ready ? (
          // 探测期间什么都不渲染，避免先闪登录页再跳走
          <div style={{ height: '100vh', background: 'var(--background)' }} />
        ) : !authenticated ? (
          <LoginPage />
        ) : (
        <BrowserRouter>
          <Routes>
            {/* 首页：极简全屏，不套双窗口外壳 */}
            <Route path="/" element={<HomePage />} />

            {/* 其余页面：左右双窗口布局 */}
            <Route element={<MainLayout />}>
              <Route path="/match" element={<MatchPage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/project/:projectId" element={<Navigate to="overview" replace />} />
              <Route path="/project/:projectId/overview" element={<OverviewPage />} />
              <Route path="/project/:projectId/tasks" element={<TasksPage />} />
              <Route path="/project/:projectId/review" element={<ReviewPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
        )}
      </AntdApp>
    </ConfigProvider>
  )
}
