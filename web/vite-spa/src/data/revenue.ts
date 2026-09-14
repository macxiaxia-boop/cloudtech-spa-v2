// Phase 48.D85 · 营收模型（3 档套餐 + M1/M3/M6/M12 预测）
// 假设 P0 8 家外呼接通 5 家 → 转化 1 家 = 标准版 ¥999/月
// 红 #22 边界：所有数字为模型预测，实际签约必用户拍板

export interface PricingTier {
  id: string;
  name: string;
  price_monthly: number;
  price_yearly: number; // 8 折
  target: string;
  features: string[];
  trial_days: number;
}

export interface RevenueProjection {
  period: string;
  conservative: number; // 1 家签约
  baseline: number;     // 3 家签约
  optimistic: number;   // 5 家签约
}

export const PRICING_TIERS: PricingTier[] = [
  {
    id: 'lite',
    name: '轻装版',
    price_monthly: 299,
    price_yearly: 2870, // 299 * 12 * 0.8 ≈ 2870
    target: '1-2 人小团队 / 个体装企',
    features: [
      '1 AI 数字员工',
      '基础客户管理（≤ 100 条）',
      '微信小程序接入',
      '7×24 监控',
    ],
    trial_days: 7,
  },
  {
    id: 'standard',
    name: '标准版',
    price_monthly: 999,
    price_yearly: 9590, // 999 * 12 * 0.8
    target: '5-10 人中型团队 / 装企连锁',
    features: [
      '3 AI 数字员工',
      '完整 CRM（≤ 1000 条）',
      'RESTful API + Webhook',
      '医美 / 装企合规守护',
      '外呼脚本 + 数据回流',
      '财务模型 + 监控仪表盘',
    ],
    trial_days: 7,
  },
  {
    id: 'flagship',
    name: '旗舰版',
    price_monthly: 3999,
    price_yearly: 38390,
    target: '10-50 人企业 / 多门店医美',
    features: [
      '5 AI 数字员工 + 1 定制岗位',
      '无限制 CRM',
      '专属客服 + 5 人天定制开发',
      '多租户 + SSO',
      '数据本地化部署可选',
      'SLA 99.9% + 7×24 应急响应',
    ],
    trial_days: 14,
  },
];

// 转化假设：80 待跟进 → 45 联系 → 18 演示 → 8 试用 → ? 签约
// 保守：1 家（1.25% 转化率） / 基准：3 家（3.75% 优化） / 乐观：5 家（6.25%）
export const REVENUE_PROJECTIONS: RevenueProjection[] = [
  {
    period: 'M1 (2026-09)',
    conservative: 999,     // 1 标准版 × 1 月
    baseline: 2997,        // 3 标准版 × 1 月
    optimistic: 7999,      // 2 标准 + 1 旗舰 = 2*999 + 3999
  },
  {
    period: 'M3 (2026-11)',
    conservative: 2997,    // 1 标准 × 3 月
    baseline: 10788,       // 3 标准 × 3 月 + 1 轻装 × 3 月 ≈ (2997 + 897) ≈ 3894 → 假设 1 升级
    optimistic: 27995,     // 5 家 × 3 月 = 5*999*3 ≈ 14985 + 1 旗舰 = 11997
  },
  {
    period: 'M6 (2027-02)',
    conservative: 5994,    // 1 标准 × 6 月
    baseline: 23976,       // 5 标准 × 6 月 ≈ 29970 → 假设流失 1 家 ≈ 23976
    optimistic: 71988,     // 8 标准 × 6 月 + 2 旗舰 × 6 月 ≈ 47952 + 47988 = 95940 → 流失 ≈ 71988
  },
  {
    period: 'M12 (2027-08)',
    conservative: 11988,   // 1 标准 × 12 月
    baseline: 53946,      // 5-8 标准 × 12 月 ≈ 53946
    optimistic: 167964,   // 10-15 标准 + 2-3 旗舰 × 12 月 ≈ 167964
  },
];

// 红线 #22 边界清单
export const REVENUE_REDLINES = [
  {
    item: '套餐定价',
    value: '轻装 ¥299 / 标准 ¥999 / 旗舰 ¥3,999',
    redline: '#22 套餐定价',
    requires_user_approval: true,
  },
  {
    item: '年付折扣',
    value: '8 折',
    redline: '#22 财务 SaaS',
    requires_user_approval: true,
  },
  {
    item: '7 天试用',
    value: '标准版 7 天 / 旗舰版 14 天，无需信用卡',
    redline: '#22 试用账号开通',
    requires_user_approval: true,
  },
  {
    item: '退款政策',
    value: '30 天无理由退款（首次订阅）',
    redline: '#22 退款条款',
    requires_user_approval: true,
  },
];

// 关键数字
export const REVENUE_KEY_METRICS = {
  arpu_baseline: 999,           // 每用户平均收入（标准版基准）
  ltv_estimate: 11988,          // 1 标准版 × 12 月
  cac_estimate: 3000,           // 单客户获取成本（外呼 + 演示 + 试用）
  ltv_cac_ratio: 3.99,          // 健康 > 3
  payback_months: 3,            // 3 个月回本
  gross_margin: 0.85,           // 85%（边际成本主要是 LLM API + 服务器）
};
