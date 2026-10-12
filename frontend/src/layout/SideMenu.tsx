/**
 * 左侧主窗口的内置侧边菜单（PRD 模块 5）。
 * 三个分区：项目总览 / 任务列表 / 项目复盘。
 */

import { Menu } from 'antd'
import {
  CheckCircleOutlined,
  DashboardOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'
import { useAppStore, type MainView } from '@/store/useAppStore'

interface SideMenuProps {
  /** 是否已进入某个项目（未进入时隐藏菜单） */
  hasProject: boolean
}

export default function SideMenu({ hasProject }: SideMenuProps) {
  const navigate = useNavigate()
  const { projectId } = useParams<{ projectId: string }>()
  const mainView = useAppStore((state) => state.mainView)
  const project = useAppStore((state) => state.project)

  if (!hasProject) {
    return null
  }

  const allCompleted = project?.progress?.all_completed ?? false

  const items: { key: MainView; icon: React.ReactNode; label: React.ReactNode }[] = [
    { key: 'overview', icon: <DashboardOutlined />, label: '项目总览' },
    { key: 'tasks', icon: <UnorderedListOutlined />, label: '任务列表' },
    {
      key: 'review',
      icon: <CheckCircleOutlined />,
      label: allCompleted ? '项目复盘' : <span style={{ opacity: 0.55 }}>项目复盘</span>,
    },
  ]

  return (
    <nav className="app-sidemenu">
      <Menu
        mode="inline"
        selectedKeys={[mainView]}
        style={{ height: '100%', borderInlineEnd: 'none' }}
        onClick={({ key }) => {
          const view = key as MainView
          // 复盘页在未完成全部任务时允许进入，但页面内会给出提示，避免用户困惑
          navigate(`/project/${projectId}/${view}`)
        }}
        items={items}
      />
    </nav>
  )
}
