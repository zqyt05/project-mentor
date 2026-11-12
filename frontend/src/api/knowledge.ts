/** 项目知识库（RAG）接口。 */

import { http } from './client'

export interface KnowledgeDocument {
  id: number
  filename: string
  file_type: string
  char_count: number
  chunk_count: number
  /** 是否成功向量化；false 表示当前走关键词检索（降级） */
  embedded: boolean
  created_at: string
}

export interface KnowledgeOverview {
  documents: KnowledgeDocument[]
  /** 语义检索是否可用（向量模型加载成功） */
  semantic_search: boolean
  supported_types: string[]
  max_size_mb: number
}

export const knowledgeApi = {
  list: (projectId: number) => http.get<KnowledgeOverview>(`/knowledge/${projectId}`),

  upload: async (projectId: number, file: File) => {
    const form = new FormData()
    form.append('file', file)
    // 上传要解析 + 向量化，比普通接口慢，但远快于 LLM 调用
    return http.post<KnowledgeDocument>(`/knowledge/${projectId}/upload`, form, true)
  },

  remove: (projectId: number, documentId: number) =>
    http.delete<{ id: number }>(`/knowledge/${projectId}/${documentId}`),

  search: (projectId: number, query: string, topK = 4) =>
    http.get<{ query: string; sources: { filename: string; chunk_index: number; score: number; content: string }[] }>(
      `/knowledge/${projectId}/search`,
      { q: query, top_k: topK },
    ),
}
