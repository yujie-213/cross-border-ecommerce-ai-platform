import { request } from '../api/client'
export interface Asset { id: string; kind: string; revision: number; state: string; sourceNature: string; scope: Record<string, any>; body: Record<string, any>; history?: { version: number; body: Record<string, any>; actor: string; createdAt: string; hash: string }[] }
export interface Index { items: Asset[]; nextCursor: string | null }
export interface Workbench { case: Index; dataset: Index; policy: Index; report: Index; investigation: Index; risk: Index; binding: Index }
export interface Workspace { workspaceId: string; modelEnabled: boolean; sourceStores: string[]; trackedProducts?:number; trackingScope?:string }
export function get<T>(path: string, signal?: AbortSignal) { return request<T>(path, {}, signal, 15000, '/api/b/v1') }
export function post<T = Asset>(path: string, body: unknown, key: string) { return request<T>(path, { method: 'POST', headers: { 'Idempotency-Key': key }, body: JSON.stringify(body) }, undefined, 15000, '/api/b/v1') }
export function change<T = Asset>(path: string, revision: number, data: unknown, key: string) { return post<T>(path, { expectedRevision: revision, data }, key) }
export const stateNames: Record<string, string> = { OPEN: '待处理', NEEDS_CLARIFICATION: '待澄清', EVIDENCE_PENDING: '待补证', REVIEW_PENDING: '待人工审核', HANDLED: '内部处理完成', ESCALATED: '优先人工升级', DRAFT: '草稿', SEALED: '待校验', IN_REVIEW: '待发布审核', PUBLISHED: '已发布', REVOKED: '已撤销', READBACK_VERIFIED: '已校验并回读', ACTIVE: '使用中', INACTIVE: '已停用', QUARANTINED: '资料已隔离', READY: '可查看', SUSPECTED: '疑似风险', CONFIRMED: '已人工确认', REJECTED: '已驳回', CLOSED: '已关闭', SUPPORTED: '调查支持', NEEDS_EVIDENCE: '需补证', EXPIRED: '已过期' }
export const labelNames: Record<string, string> = { SIZE: '尺码', DESCRIPTION: '描述', DAMAGE: '破损', LOGISTICS: '物流', FUNCTION: '功能', COMPATIBILITY: '兼容', SAFETY: '安全', OTHER: '其他', UNKNOWN: '未分类' }
export function effectiveState(asset: Asset) { return asset.state === 'CONFIRMED' && Date.parse(asset.body.validUntil) <= Date.now() ? 'EXPIRED' : asset.state }
