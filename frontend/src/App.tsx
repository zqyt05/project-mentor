/**
 * 应用根组件：路由配置 + 全局主题。
 *
 * 主题对应「新闻纸」设计系统：零圆角、墨黑为唯一强调色、无柔和阴影。
 * 具体的视觉细节（纹理、硬阴影、全大写标签等）在 index.css 中实现，
 * 此处只设置 Ant Design 的 token，避免全局样式散落两处。
 */

import { App as AntdApp, ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { Navigate, Route, Routes } from 'react-router-dom'
import { BrowserRouter } from 'react-router-dom'
import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'
import MainLayout from '@/layout/MainLayout'
import HomePage from '@/pages/HomePage'
import MatchPage from '@/pages/MatchPage'
import OverviewPage from '@/pages/OverviewPage'
import TasksPage from '@/pages/TasksPage'
import ReviewPage from '@/pages/ReviewPage'
import HistoryPage from '@/pages/HistoryPage'

dayjs.locale('zh-cn')

/** 新闻纸调色板（与 index.css 中的 CSS 变量保持一致） */
const PAPER = '#F9F9F7'
const INK = '#111111'
const SOFT = '#E5E5E0'

export default function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        // 不使用 AntD 的默认/紧凑算法做视觉决策，全部交给 token + CSS
        token: {
          colorPrimary: INK,
          colorInfo: INK,
          colorLink: INK,
          colorText: INK,
          colorTextHeading: INK,
          colorTextSecondary: '#525252',
          colorBgBase: PAPER,
          colorBgContainer: PAPER,
          colorBgElevated: PAPER,
          colorBorder: INK,
          colorBorderSecondary: SOFT,
          // 纯粹几何：处处零圆角
          borderRadius: 0,
          borderRadiusLG: 0,
          borderRadiusSM: 0,
          borderRadiusXS: 0,
          // 扁平设计：无柔和投影
          boxShadow: 'none',
          boxShadowSecondary: 'none',
          boxShadowTertiary: 'none',
          fontFamily:
            "'Inter', 'Helvetica Neue', 'PingFang SC', 'Microsoft YaHei', sans-serif",
          fontSize: 14,
          lineHeight: 1.625,
          wireframe: false,
        },
        components: {
          Card: {
            borderRadiusLG: 0,
            paddingLG: 16,
            boxShadowTertiary: 'none',
            colorBorderSecondary: INK,
          },
          Button: {
            borderRadius: 0,
            borderRadiusLG: 0,
            borderRadiusSM: 0,
            primaryShadow: 'none',
            defaultShadow: 'none',
            dangerShadow: 'none',
          },
          Input: { borderRadius: 0, activeShadow: 'none' },
          Progress: { defaultColor: INK, remainingColor: SOFT },
          Tag: { borderRadiusSM: 0, defaultBg: 'transparent' },
          Menu: {
            itemBorderRadius: 0,
            itemSelectedBg: INK,
            itemSelectedColor: PAPER,
            itemHoverBg: SOFT,
            itemColor: INK,
          },
          Modal: { borderRadiusLG: 0 },
          Alert: { borderRadiusLG: 0 },
          Segmented: { borderRadius: 0, itemSelectedBg: INK, itemSelectedColor: PAPER },
          Collapse: { borderRadiusLG: 0, headerPadding: '11px 14px' },
        },
      }}
    >
      {/* AntdApp 提供 message / modal 的静态方法上下文 */}
      <AntdApp>
        <BrowserRouter>
          <Routes>
            <Route element={<MainLayout />}>
              <Route path="/" element={<HomePage />} />
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
      </AntdApp>
    </ConfigProvider>
  )
}
