/**
 * 全局页面框架（PRD 模块 5 · 全局导航与状态管理）。
 *
 * 固定左右分栏，全站保持一致：
 * - 左侧主任务窗口（约 70%）：侧边菜单 + 内容区，纯展示与任务操作，内容静态稳定
 * - 右侧独立答疑窗口（约 30%）：全局常驻，随主窗口内容自动切换上下文
 *
 * 同时负责把路由参数与全局 store 对齐（当前项目、当前分区）。
 */

import { useEffect } from 'react'
import { Outlet, useLocation, useParams } from 'react-router-dom'
import { Spin } from 'antd'
import TopBar from '@/layout/TopBar'
import SideMenu from '@/layout/SideMenu'
import ChatPanel from '@/layout/ChatPanel'
import { useAppStore, type MainView } from '@/store/useAppStore'
import { projectApi } from '@/api/project'

/** 从 URL 路径推导左侧分区 */
function resolveMainView(pathname: string): MainView {
  if (pathname.endsWith('/tasks')) return 'tasks'
  if (pathname.endsWith('/review')) return 'review'
  return 'overview'
}

export default function MainLayout() {
  const { projectId } = useParams<{ projectId: string }>()
  const location = useLocation()

  const project = useAppStore((state) => state.project)
  const setProject = useAppStore((state) => state.setProject)
  const setMainView = useAppStore((state) => state.setMainView)
  const setActiveTaskId = useAppStore((state) => state.setActiveTaskId)

  const parsedId = projectId ? Number(projectId) : null

  // 路由中的项目 ID 变化时加载项目详情
  useEffect(() => {
    let cancelled = false

    if (!parsedId) {
      setProject(null)
      setActiveTaskId(null)
      return
    }
    // 同一个项目内切换分区时无需重复拉取
    if (project?.id === parsedId) return

    projectApi
      .detail(parsedId)
      .then((detail) => {
        if (cancelled) return
        setProject(detail)
        // 进入项目时默认绑定当前应做的任务，让答疑窗口立刻有上下文
        setActiveTaskId(detail.progress?.current_task_id ?? detail.tasks[0]?.id ?? null)
      })
      .catch(() => {
        /* 错误提示已由 axios 拦截器统一处理 */
      })

    return () => {
      cancelled = true
    }
  }, [parsedId, project?.id, setProject, setActiveTaskId])

  // 路由 → 左侧分区同步
  useEffect(() => {
    setMainView(resolveMainView(location.pathname))
  }, [location.pathname, setMainView])

  const hasProject = Boolean(parsedId)

  return (
    <div className="app-shell">
      <TopBar />

      <div className="app-body">
        {/* 左侧：主任务窗口（约 70%） */}
        <main className="pane-main">
          <SideMenu hasProject={hasProject} />
          <section className="pane-main-content">
            {hasProject && !project ? (
              <div className="pane-loading">
                <Spin size="large" tip="正在加载项目数据…">
                  <div style={{ height: 80 }} />
                </Spin>
              </div>
            ) : (
              <Outlet />
            )}
          </section>
        </main>

        {/* 右侧：独立答疑子窗口（约 30%），全局常驻 */}
        <ChatPanel />
      </div>
    </div>
  )
}
