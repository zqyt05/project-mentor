/**
 * 最终交付物列表。
 *
 * 交付物由 LLM 拆成多条产出（数组），这里以分点形式呈现，比一整段文字更直观。
 * 只有一条时不画项目符号，避免出现「孤零零一个方块」的视觉噪音。
 */

interface DeliverableListProps {
  /** 交付物清单 */
  items: string[]
}

export default function DeliverableList({ items }: DeliverableListProps) {
  const points = items.filter((item) => item && item.trim())
  if (points.length === 0) return null

  return (
    <ul className={`deliverable-list ${points.length === 1 ? 'deliverable-list-single' : ''}`}>
      {points.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  )
}
