/**
 * 应用根组件：路由配置 + 全局主题。
 */

import { App as AntdApp, ConfigProvider, theme } from 'antd'
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

export default function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: '#1677ff',
          borderRadius: 8,
          fontSize: 14,
        },
        components: {
          Card: { paddingLG: 16 },
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
