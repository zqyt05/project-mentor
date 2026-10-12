/**
 * 顶部导航栏（PRD 模块 5）。
 * 展示：产品标识、当前项目名与来源标签、整体进度条、全局导航入口。
 */

import { Badge, Button, Progress, Space, Tag, Tooltip, Typography } from 'antd'
import {
  BookOutlined,
  GithubOutlined,
  HistoryOutlined,
  HomeOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAppStore } from '@/store/useAppStore'

const { Text } = Typography

export default function TopBar() {
  const navigate = useNavigate()
  const location = useLocation()
  const project = useAppStore((state) => state.project)
  const progress = project?.progress

  const onHome = location.pathname === '/'
  const onHistory = location.pathname === '/history'

  return (
    <header className="app-topbar">
      <div className="topbar-left">
        <div className="brand" onClick={() => navigate('/')} role="button" tabIndex={0}>
          <ThunderboltOutlined className="brand-icon" />
          <div className="brand-text">
            <span className="brand-name">ProjectMentor</span>
            <span className="brand-slogan">按照需求去学习，而不是系统性学习</span>
          </div>
        </div>
      </div>

      <div className="topbar-center">
        {project ? (
          <Space size={12} align="center">
            <Text strong ellipsis style={{ maxWidth: 280 }}>
              {project.name}
            </Text>
            {project.source === 'github' ? (
              <Tag icon={<GithubOutlined />} color="geekblue">
                GitHub
              </Tag>
            ) : (
              <Tag icon={<BookOutlined />} color="purple">
                定制项目
              </Tag>
            )}
            <Tag color="cyan">{project.difficulty}</Tag>
            {project.status === 'reviewing' && <Tag color="orange">待复盘</Tag>}
            {project.status === 'completed' && <Tag color="green">已闭环</Tag>}
            <div className="topbar-progress">
              <Progress
                percent={progress?.percent ?? 0}
                size="small"
                strokeColor={{ from: '#108ee9', to: '#87d068' }}
                style={{ width: 180, marginBottom: 0 }}
              />
              <Text type="secondary" className="topbar-progress-text">
                {progress ? `${progress.done}/${progress.total} 任务` : ''}
              </Text>
            </div>
          </Space>
        ) : (
          <Text type="secondary">项目匹配 → 任务拆解 + DDL → 双窗口答疑 → 费曼复盘</Text>
        )}
      </div>

      <div className="topbar-right">
        <Tooltip title="首页：输入学习方向">
          <Button
            type={onHome ? 'primary' : 'text'}
            icon={<HomeOutlined />}
            onClick={() => navigate('/')}
          >
            开始学习
          </Button>
        </Tooltip>
        <Badge dot={false}>
          <Button
            type={onHistory ? 'primary' : 'text'}
            icon={<HistoryOutlined />}
            onClick={() => navigate('/history')}
          >
            历史项目
          </Button>
        </Badge>
      </div>
    </header>
  )
}
