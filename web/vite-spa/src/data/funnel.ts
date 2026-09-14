// Phase 48.D84 · 漏斗数据（4 阶段转化率统计）
// 5 状态机：待跟进 → 已联系 → 演示 → 试用 → 签约
// 数据源：CRM (customers.ts) + Apollo 数字员工跟进日志

export interface FunnelStage {
  stage: string;
  label: string;
  count: number;
  color: string;
  icon: string;
}

export interface ConversionRate {
  from_stage: string;
  to_stage: string;
  rate: number;
  drop_reason: string;
}

export interface FunnelSnapshot {
  total_leads: number;
  stages: FunnelStage[];
  conversions: ConversionRate[];
  generated_at: string;
  period: string;
}

// 5 状态机 + 漏斗转化（基于 80 家装企 P0/P1/P2/P3 分级）
export const FUNNEL_SNAPSHOT: FunnelSnapshot = {
  total_leads: 80,
  period: '2026-09-01 ~ 2026-09-14 (14 天)',
  generated_at: '2026-09-14',
  stages: [
    { stage: 'lead', label: '① 待跟进', count: 80, color: 'text-gray-500', icon: '📥' },
    { stage: 'contacted', label: '② 已联系', count: 45, color: 'text-blue-500', icon: '📞' },
    { stage: 'demo', label: '③ 已演示', count: 18, color: 'text-purple-500', icon: '🎬' },
    { stage: 'trial', label: '④ 试用中', count: 8, color: 'text-orange-500', icon: '🧪' },
    { stage: 'signed', label: '⑤ 已签约', count: 1, color: 'text-green-500', icon: '✅' },
  ],
  conversions: [
    { from_stage: 'lead', to_stage: 'contacted', rate: 56.25, drop_reason: '号码无效 / 无回应 / 拒绝' },
    { from_stage: 'contacted', to_stage: 'demo', rate: 40.0, drop_reason: '时机不对 / 已用竞品 / 预算不足' },
    { from_stage: 'demo', to_stage: 'trial', rate: 44.4, drop_reason: '功能不对 / 团队抵触 / 决策慢' },
    { from_stage: 'trial', to_stage: 'signed', rate: 12.5, drop_reason: '价格犹豫 / 效果未达预期' },
  ],
};

// 总体转化率（80 → 1）
export const OVERALL_CONVERSION = (1 / 80) * 100; // 1.25%

// 4 关键洞察
export const FUNNEL_INSIGHTS = [
  {
    insight: '联系 → 演示 转化偏低（40%）',
    action: '优化首次外呼话术：30 秒内讲清"装企获客成本 ¥80→¥28"具体场景',
    owner: 'Artemis 数字员工',
    deadline: '2026-09-21',
  },
  {
    insight: '演示 → 试用 转化中等（44%）',
    action: '针对装企老板定制 5 分钟定制 demo，含 1 家同城市标杆案例',
    owner: 'Athena + Artemis',
    deadline: '2026-09-25',
  },
  {
    insight: '试用 → 签约 转化偏低（12.5%）',
    action: '7 天试用期内 Day 3/5/7 三次主动跟进 + 定制 ROI 报告',
    owner: 'Apollo 数字员工',
    deadline: '2026-09-30',
  },
  {
    insight: '待跟进池 80 家仍有 35 家未联系',
    action: 'Artemis 批量外呼 + 短信触达，14 天内完成 80 家首轮外呼',
    owner: 'Artemis',
    deadline: '2026-09-28',
  },
];
