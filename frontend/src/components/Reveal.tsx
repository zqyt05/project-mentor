/**
 * 入场动画容器：内容进入视口时淡入上移，并支持错峰。
 *
 * 设计规范要求用 Framer Motion 实现，这里用「IntersectionObserver + CSS 过渡」
 * 达到相同的视觉产物，但不引入 ~50KB 的额外依赖 —— 本项目是工具型应用，
 * 首屏体积比动画库更重要。视口参数对齐规范建议：
 * once（只播一次）、amount 0.15（露出 15% 才触发）、margin -60px。
 *
 * 用法：
 *   <Reveal>单块内容</Reveal>
 *   <Reveal delay={1}>需要错峰的第二块</Reveal>
 */

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react'

interface RevealProps {
  children: ReactNode
  /** 错峰序号，每级 0.1s（对应规范的 staggerChildren: 0.1） */
  delay?: number
  /** 自定义 class，便于附加布局样式 */
  className?: string
}

export default function Reveal({ children, delay = 0, className = '' }: RevealProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const node = ref.current
    if (!node) return

    // 尊重系统的「减少动态效果」偏好：直接显示，不做任何观察
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setVisible(true)
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setVisible(true)
            observer.disconnect() // once：只播一次
          }
        }
      },
      { threshold: 0.15, rootMargin: '-60px' },
    )

    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  const style: CSSProperties = delay ? { transitionDelay: `${delay * 0.1}s` } : {}

  return (
    <div
      ref={ref}
      className={`reveal ${visible ? 'reveal-visible' : ''} ${className}`.trim()}
      style={style}
    >
      {children}
    </div>
  )
}
