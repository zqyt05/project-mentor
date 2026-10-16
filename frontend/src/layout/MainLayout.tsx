/**
 * 全局页面框架（PRD 模块 5 · 全局导航与状态管理）。
 *
 * 左右分栏，全站保持一致：
 * - 左侧主任务窗口（默认约 70%）：侧边菜单 + 内容区，纯展示与任务操作，内容静态稳定
 * - 右侧独立答疑窗口（默认约 30%）：全局常驻，随主窗口内容自动切换上下文
 *
 * 分栏比例可通过中间的把手拖拽调整，并记住用户的选择（localStorage）。
 * 窄屏（≤1100px）下改为上下堆叠，此时把手隐藏、宽度设置不生效。
 *
 * 同时负责把路由参数与全局 store 对齐（当前项目、当前分区）。
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { Outlet, useLocation, useNavigate, useParams } from 'react-router-dom'
import { Button, Result, Spin } from 'antd'
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

/** 左侧窗口宽度的取值范围（百分比）与默认值 */
const PANE_MIN = 40
const PANE_MAX = 82
const PANE_DEFAULT = 70
const PANE_STORAGE_KEY = 'projectmentor.pane-left-percent'

/** 读取用户上次设定的分栏比例 */
function loadPanePercent(): number {
  const raw = window.localStorage.getItem(PANE_STORAGE_KEY)
  const value = raw ? Number(raw) : Number.NaN
  if (Number.isNaN(value)) return PANE_DEFAULT
  return Math.min(PANE_MAX, Math.max(PANE_MIN, value))
}

export default function MainLayout() {
  const { projectId } = useParams<{ projectId: string }>()
  const location = useLocation()
  const navigate = useNavigate()

  const project = useAppStore((state) => state.project)
  const setProject = useAppStore((state) => state.setProject)
  const setMainView = useAppStore((state) => state.setMainView)
  const setActiveTaskId = useAppStore((state) => state.setActiveTaskId)

  // ---------- 可拖拽分栏 ----------
  const [leftPercent, setLeftPercent] = useState(loadPanePercent)
  const [dragging, setDragging] = useState(false)
  // 项目详情加载失败时的提示（避免页面永远停在 loading）
  const [loadError, setLoadError] = useState<string | null>(null)
  const draggingRef = useRef(false)

  // 拖拽期间监听全局鼠标事件：指针移出把手甚至移出窗口时也能继续跟手
  useEffect(() => {
    const onMove = (event: MouseEvent) => {
      if (!draggingRef.current) return
      const percent = (event.clientX / window.innerWidth) * 100
      setLeftPercent(Math.min(PANE_MAX, Math.max(PANE_MIN, percent)))
    }
    const onUp = () => {
      if (!draggingRef.current) return
      draggingRef.current = false
      setDragging(false)
      document.body.classList.remove('pane-resizing')
    }

    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
      document.body.classList.remove('pane-resizing')
    }
  }, [])

  // 记住用户偏好
  useEffect(() => {
    window.localStorage.setItem(PANE_STORAGE_KEY, String(Math.round(leftPercent)))
  }, [leftPercent])

  const startDrag = useCallback(() => {
    draggingRef.current = true
    setDragging(true)
    document.body.classList.add('pane-resizing')
  }, [])

  /** 双击把手恢复默认比例 */
  const resetDrag = useCallback(() => setLeftPercent(PANE_DEFAULT), [])

  const parsedId = projectId ? Number(projectId) : null

  // 路由中的项目 ID 变化时加载项目详情
  useEffect(() => {
    let cancelled = false

    if (!parsedId) {
      setProject(null)
      setActiveTaskId(null)
      setLoadError(null)
      return
    }
    // 同一个项目内切换分区时无需重复拉取
    if (project?.id === parsedId) return

    setLoadError(null)
    projectApi
      .detail(parsedId)
      .then((detail) => {
        if (cancelled) return
        setProject(detail)
        // 进入项目时默认绑定当前应做的任务，让答疑窗口立刻有上下文
        setActiveTaskId(detail.progress?.current_task_id ?? detail.tasks[0]?.id ?? null)
      })
      .catch(() => {
        // 必须落一个错误态：否则页面会永远停在 loading，
        // 用户既看不到失败原因，也没有回到首页的出口
        if (!cancelled) setLoadError('项目加载失败，可能已被删除')
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

      {/* --pane-main 由 .pane-main 的 flex-basis/max-width 读取；
          变量名必须与 index.css 中的定义完全一致，否则拖拽不会生效 */}
      <div className="app-body" style={{ '--pane-main': `${leftPercent}%` } as React.CSSProperties}>
        {/* 左侧：主任务窗口（约 70%） */}
        <main className="pane-main">
          <SideMenu hasProject={hasProject} />
          <section className="pane-main-content">
            {hasProject && loadError ? (
              <div className="pane-loading">
                <Result
                  status="warning"
                  title={loadError}
                  subTitle="请返回首页重新选择，或从历史项目中打开一个存在的项目。"
                  extra={
                    <Button type="primary" onClick={() => navigate('/history')}>
                      查看历史项目
                    </Button>
                  }
                />
              </div>
            ) : hasProject && !project ? (
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

        {/* 可拖拽分栏把手 */}
        <div
          className={`pane-resizer ${dragging ? 'pane-resizer-dragging' : ''}`}
          onMouseDown={(event) => {
            event.preventDefault()
            startDrag()
          }}
          onDoubleClick={resetDrag}
          role="separator"
          aria-orientation="vertical"
          aria-label="拖拽调整左右窗口宽度，双击恢复默认"
          title="拖拽调整宽度 · 双击恢复默认"
        />

        {/* 右侧：独立答疑子窗口（约 30%），全局常驻 */}
        <ChatPanel />
      </div>
    </div>
  )
}
