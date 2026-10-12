/**
 * Axios 客户端封装。
 *
 * 统一处理：
 * - 后端 `{code, message, data}` 响应格式的解包
 * - 业务错误与网络错误的友好提示（通过 antd message 展示）
 * - 请求超时（AI 接口耗时较长，单独放宽）
 */

import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios'
import { message } from 'antd'
import type { ApiResponse } from './types'

/** AI 相关接口的响应可能长达数分钟（推理模型 + 长文生成） */
const AI_TIMEOUT = 5 * 60 * 1000
/** 普通数据接口超时 */
const DEFAULT_TIMEOUT = 20 * 1000

const instance: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: DEFAULT_TIMEOUT,
  headers: { 'Content-Type': 'application/json' },
})

/** 是否已经弹过错误提示，避免并发请求时刷屏 */
let lastErrorAt = 0
const notifyError = (text: string) => {
  const now = Date.now()
  if (now - lastErrorAt > 1500) {
    lastErrorAt = now
    message.error(text)
  }
}

/**
 * 发起请求并解包 `data` 字段。
 * @param config axios 请求配置
 * @param aiCall 是否为 AI 接口（使用更长的超时时间）
 */
export async function request<T>(config: AxiosRequestConfig, aiCall = false): Promise<T> {
  try {
    const response = await instance.request<ApiResponse<T>>({
      timeout: aiCall ? AI_TIMEOUT : DEFAULT_TIMEOUT,
      ...config,
    })
    const body = response.data
    // 后端业务错误仍以 HTTP 200 返回，通过 code 判断
    if (body.code !== 0) {
      notifyError(body.message || '请求失败')
      throw new Error(body.message || '请求失败')
    }
    return body.data
  } catch (error) {
    const axiosError = error as AxiosError<ApiResponse<unknown>>
    // 业务错误已在上面提示过，这里只处理网络层错误
    if (axiosError.response) {
      const payload = axiosError.response.data
      if (payload && typeof payload === 'object' && 'message' in payload) {
        throw error
      }
      notifyError(`服务返回错误（HTTP ${axiosError.response.status}）`)
    } else if (axiosError.code === 'ECONNABORTED') {
      notifyError('请求超时。AI 生成较慢，请稍后重试')
    } else {
      notifyError('无法连接后端服务，请确认后端已启动（127.0.0.1:8000）')
    }
    throw error
  }
}

export const http = {
  get: <T>(url: string, params?: Record<string, unknown>, aiCall = false) =>
    request<T>({ method: 'GET', url, params }, aiCall),
  post: <T>(url: string, data?: unknown, aiCall = false) =>
    request<T>({ method: 'POST', url, data }, aiCall),
  patch: <T>(url: string, data?: unknown, aiCall = false) =>
    request<T>({ method: 'PATCH', url, data }, aiCall),
  delete: <T>(url: string, params?: Record<string, unknown>, aiCall = false) =>
    request<T>({ method: 'DELETE', url, params }, aiCall),
}
