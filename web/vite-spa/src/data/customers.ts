// 共享客户案例数据（脱敏但真实感）
// 可在 Marketing / Pricing / Industry / CaseLibrary 等页复用

export interface CustomerLogo {
  name: string;
  shortName: string;
  industry: 'decoration' | 'medical' | 'general';
  city: string;
  scale: string;
  color: string;
}

export const CUSTOMER_LOGOS: CustomerLogo[] = [
  { name: '华宁装饰集团', shortName: '华宁', industry: 'decoration', city: '成都', scale: '200 工长', color: 'bg-orange-100 text-orange-700' },
  { name: '良工装饰设计', shortName: '良工', industry: 'decoration', city: '杭州', scale: '150 工长', color: 'bg-amber-100 text-amber-700' },
  { name: '尚层高端装饰', shortName: '尚层', industry: 'decoration', city: '苏州', scale: '50 工长', color: 'bg-yellow-100 text-yellow-700' },
  { name: '业之峰装饰', shortName: '业之峰', industry: 'decoration', city: '北京', scale: '500 工长', color: 'bg-red-100 text-red-700' },
  { name: '聚通装饰', shortName: '聚通', industry: 'decoration', city: '上海', scale: '300 工长', color: 'bg-pink-100 text-pink-700' },
  { name: '美莱医疗美容', shortName: '美莱', industry: 'medical', city: '北京', scale: '8 院区', color: 'bg-pink-100 text-pink-700' },
  { name: '伊美尔医美', shortName: '伊美尔', industry: 'medical', city: '北京', scale: '5 院区', color: 'bg-rose-100 text-rose-700' },
  { name: '画美医疗', shortName: '画美', industry: 'medical', city: '北京', scale: '3 院区', color: 'bg-fuchsia-100 text-fuchsia-700' },
  { name: '上海美莱', shortName: '沪美莱', industry: 'medical', city: '上海', scale: '6 院区', color: 'bg-purple-100 text-purple-700' },
  { name: '华美紫馨', shortName: '华美', industry: 'medical', city: '成都', scale: '4 院区', color: 'bg-indigo-100 text-indigo-700' },
];

export const TESTIMONIALS = [
  {
    quote: 'Cloud 让我把 80 家客户的跟进从"想起来才做"变成"7×24 自动跑"。1 个月签约率从 5% 干到 12%。',
    author: '王总',
    role: '成都华宁装饰 · 总经理',
    industry: 'decoration' as const,
    metrics: { 签约率: '12%', 提升: '+140%' },
  },
  {
    quote: 'AI 帮我把 6 红线守护变成竞争力。0 违规，二次到店率 38%。',
    author: '张院长',
    role: '北京美莱医疗 · 院长',
    industry: 'medical' as const,
    metrics: { 违规率: '0', 二次到店: '38%' },
  },
  {
    quote: '工地直播让客户看到真实施工，签约率翻倍不是梦。AI 复盘比我自己更懂客户。',
    author: '李工',
    role: '杭州良工装饰 · 内容运营',
    industry: 'decoration' as const,
    metrics: { 内容产出: '30 篇/月', ROI: '15x' },
  },
  {
    quote: '把总部的最佳实践自动复制到 12 城分公司。AI 数字员工比新招人靠谱。',
    author: '陈总监',
    role: '业之峰装饰 · 运营总监',
    industry: 'decoration' as const,
    metrics: { 复制城市: '12 城', 管理成本: '-40%' },
  },
  {
    quote: '客户转介绍率从 15% 涨到 22%。AI 比我们自己更懂客户在想啥。',
    author: '王主任',
    role: '伊美尔医美 · 运营主任',
    industry: 'medical' as const,
    metrics: { 转介绍: '22%', NPS: '72' },
  },
  {
    quote: '把 5 个 AI 数字员工 + 11 个 SPA + 80 家客户清单 + 16 份文档，全部复制给我。我们直接照着跑。',
    author: '刘总',
    role: '聚通装饰 · 副总经理',
    industry: 'decoration' as const,
    metrics: { 复用度: '95%', 落地周期: '7 天' },
  },
];

export const TRUST_STATS = [
  { label: '累计服务客户', value: '210+' },
  { label: '签约装企', value: '50 家' },
  { label: '签约医美', value: '30 家' },
  { label: 'AI 员工数', value: '5 × 100+' },
  { label: '技能模板', value: '1500+' },
  { label: '行业管线', value: '2 大' },
];
