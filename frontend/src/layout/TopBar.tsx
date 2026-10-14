/**
 * 报头（PRD 模块 5 · 顶部导航栏）。
 *
 * 新闻纸风格：左侧为刊名，中间为版次元数据或当前项目信息，右侧为全局导航。
 * 报头用 4px 粗线压底，是整份「报纸」的视觉锚点。
 *
 * 设计取舍：
 * - 按需求去掉了刊名前的闪电图标，也不再展示「项目匹配 → 任务拆解 → …」流程文案
 * - 不设置跑马灯：报头已经承载了刊名、版次、项目名、进度与导航，
 *   再加一条滚动的说明文字会与页面正文的 STEP 1–4 重复，反而增加噪音。
 *   跑马灯样式仍保留在 CSS 中（.np-marquee），需要时可随时启用。
 */

import { Button, Progress, Tag } from 'antd'
import { GithubOutlined, HistoryOutlined, HomeOutlined } from '@ant-design/icons'
import { useLocation, useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import { useAppStore } from '@/store/useAppStore'

export default function TopBar() {
  const navigate = useNavigate()
  const location = useLocation()
  const project = useAppStore((state) => state.project)
  const progress = project?.progress

  const onHome = location.pathname === '/'
  const onHistory = location.pathname === '/history'

  return (
    <header className="app-topbar">
      <div className="topbar-inner">
        <div className="topbar-left">
          {/* 刊名：无图标，纯字体排印 */}
          <div
            className="brand"
            onClick={() => navigate('/')}
            role="button"
            tabIndex={0}
            onKeyDown={(event) => event.key === 'Enter' && navigate('/')}
          >
            <span className="brand-name">ProjectMentor</span>
            <span className="brand-slogan">按照需求去学习</span>
          </div>
        </div>

        <div className="topbar-center">
          {project ? (
            <div className="topbar-project">
              <span className="np-label">本期项目</span>
              <span className="topbar-project-name">{project.name}</span>
              {project.source === 'github' ? (
                <Tag icon={<GithubOutlined />}>GitHub</Tag>
              ) : (
                <Tag>定制</Tag>
              )}
              <Tag>{project.difficulty}</Tag>
              {project.status === 'reviewing' && <Tag>待复盘</Tag>}
              {project.status === 'completed' && <Tag>已闭环</Tag>}
              <div className="topbar-progress">
                <Progress
                  percent={progress?.percent ?? 0}
                  size="small"
                  showInfo={false}
                  style={{ width: 130, marginBottom: 0 }}
                />
                <span className="topbar-progress-text">
                  {progress ? `${progress.done}/${progress.total}` : ''}
                </span>
              </div>
            </div>
          ) : (
            /* 版次元数据：报纸式的出版信息，替代原先的流程说明文案 */
            <div className="edition-meta">
              <span>第 1 卷</span>
              <span className="edition-sep">|</span>
              <span>{dayjs().format('YYYY 年 MM 月 DD 日')}</span>
              <span className="edition-sep">|</span>
              <span>本地版</span>
              <span className="edition-sep">|</span>
              <span>免费发行</span>
            </div>
          )}
        </div>

        <div className="topbar-right">
          <Button
            type={onHome ? 'primary' : 'text'}
            icon={<HomeOutlined />}
            onClick={() => navigate('/')}
          >
            开始学习
          </Button>
          <Button
            type={onHistory ? 'primary' : 'text'}
            icon={<HistoryOutlined />}
            onClick={() => navigate('/history')}
          >
            历史项目
          </Button>
        </div>
      </div>
    </header>
  )
}
