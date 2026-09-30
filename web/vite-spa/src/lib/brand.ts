/**
 * CloudTech Brand SSOT · V23 设计重写 (2026-09-30)
 *
 * 单一 brand 字符串源头 · 全 Vite SPA import 自此 · 不再硬编码 brand 字面量
 *
 * 背景:
 *   - dist-v45/index.html = "CloudTech · 企业级 AI 工作空间" (R337/R321)
 *   - PWA dist = "CloudTech · 灵策 AI 数字营销中台" (R293 rebrand)
 *   - 老 landing-page/admin.html = "云数科技 · 统一驾驶舱" (V20 老)
 *
 * SSOT:
 *   - 短名: CloudTech (V22 SaaS 主品牌)
 *   - 全名: CloudTech · 企业级 AI 工作空间
 *   - 法律名: 灵策智算 / LynxceAI (V22 SaaS 业务品牌)
 *   - 公众号: 云数时代的变革 (lynxce-ai)
 *
 * 使用:
 *   import { BRAND } from '@/lib/brand';
 *   <title>{BRAND.fullName} · Dashboard</title>
 */
export const BRAND = {
  shortName: 'CloudTech',
  fullName: 'CloudTech · 企业级 AI 工作空间',
  legalName: '灵策智算 / LynxceAI',
  publisher: '云数时代的变革',
  wechatId: 'lynxce-ai',
  tagline: 'AI 时代企业增长顾问',
  description: 'CloudTech 是企业级 AI 数字员工 SaaS 平台，集成对话、智能体、工作流、任务执行、知识管理的一体化 AI 工作空间。让 AI 成为团队的 5 位数字员工，像一支完整团队跑。',
  keywords: 'CloudTech,AI 工作空间,智能体,工作流,任务管理,知识库,AI 对话,数字员工,SaaS',
  industries: ['装修/建材/装企', '教育', '制造', '服务'] as const,
  version: '23.0.0',
  pricing: {
    basicYuan: 199,
    proYuan: 1999,
    enterpriseYuan: 2999,
  },
} as const;

export type Brand = typeof BRAND;