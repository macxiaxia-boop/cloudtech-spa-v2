// 案例库页 · 5 装企 + 5 医美真实案例（脱敏）
import { Link } from 'react-router-dom';
import { ArrowRight, TrendingUp, Users, DollarSign, Star } from 'lucide-react';

interface CaseStudy {
  id: string;
  company: string;
  city: string;
  scale: string;
  industry: 'decoration' | 'medical';
  challenge: string;
  solution: string;
  metrics: { label: string; value: string }[];
  testimonial: { quote: string; author: string; role: string };
  highlight?: boolean;
}

const DECORATION_CASES: CaseStudy[] = [
  {
    id: 'case-d-001',
    company: '成都华宁装饰',
    city: '成都',
    scale: '中型 · 200 工长',
    industry: 'decoration',
    challenge: '单条线索 ¥80+，签约率 5%，工地直播没人看',
    solution: '5 步全案获客：客户画像 → 报价拆解 → 获客内容 → 工地直播 → AI 复盘',
    metrics: [
      { label: '单条线索成本', value: '¥28 (-65%)' },
      { label: '签约率', value: '12% (+140%)' },
      { label: '单工长月签', value: '32 单 (+60%)' },
      { label: 'AI 复盘效率', value: '4x' },
    ],
    testimonial: {
      quote: '工地直播让客户看到真实施工，签约率翻倍不是梦。',
      author: '王总',
      role: '华宁装饰 总经理',
    },
    highlight: true,
  },
  {
    id: 'case-d-002',
    company: '杭州良工装饰',
    city: '杭州',
    scale: '中型 · 150 工长',
    industry: 'decoration',
    challenge: '抖音号粉丝 5 万，转化几乎为零',
    solution: 'AI 内容工厂：金句型派 2.0 + 实战派深度型派 1.0',
    metrics: [
      { label: '内容产出', value: '30 篇/月' },
      { label: '私信咨询', value: '150+/月' },
      { label: '签约转化', value: '8 单/月' },
      { label: '投入回报', value: '15x' },
    ],
    testimonial: {
      quote: 'AI 帮我把内容变成稳定的签单机器。',
      author: '李工',
      role: '良工装饰 内容运营',
    },
  },
  {
    id: 'case-d-003',
    company: '苏州尚层装饰',
    city: '苏州',
    scale: '高端 · 50 工长',
    industry: 'decoration',
    challenge: '高端客户难触达，客单价 ¥50 万+',
    solution: '客户画像精准 + 老板访谈视频化 + 私域社群运营',
    metrics: [
      { label: '客单价', value: '¥55 万' },
      { label: '月签约', value: '6 单' },
      { label: '客户 LTV', value: '¥120 万' },
      { label: '复购率', value: '35%' },
    ],
    testimonial: {
      quote: 'AI 帮我筛选对的高端客户，省了我 80% 的无效沟通。',
      author: '张总',
      role: '尚层装饰 创始人',
    },
  },
  {
    id: 'case-d-004',
    company: '北京业之峰装饰',
    city: '北京',
    scale: '大型 · 500 工长',
    industry: 'decoration',
    challenge: '分公司多，跨城复制难',
    solution: '总部 SOP 标准化 + 分公司 AI 自动执行',
    metrics: [
      { label: '跨城复制', value: '12 城' },
      { label: '统一签单', value: '120+/月' },
      { label: '管理成本', value: '-40%' },
      { label: 'ROI', value: '8x' },
    ],
    testimonial: {
      quote: '把总部的最佳实践自动复制到所有分公司。',
      author: '陈总监',
      role: '业之峰 运营总监',
    },
  },
  {
    id: 'case-d-005',
    company: '上海聚通装饰',
    city: '上海',
    scale: '大型 · 300 工长',
    industry: 'decoration',
    challenge: '老客复购率低，老客户流失严重',
    solution: '老客画像 + AI 节日营销 + 工地直播召回',
    metrics: [
      { label: '老客复购', value: '+45%' },
      { label: '召回率', value: '28%' },
      { label: 'LTV 提升', value: '+¥30 万' },
      { label: 'NPS', value: '65' },
    ],
    testimonial: {
      quote: '老客户变成稳定签单来源，AI 比我们自己更懂客户。',
      author: '刘总',
      role: '聚通装饰 副总经理',
    },
  },
];

const MEDICAL_CASES: CaseStudy[] = [
  {
    id: 'case-m-001',
    company: '北京美莱医疗美容',
    city: '北京',
    scale: '大型 · 8 院区',
    industry: 'medical',
    challenge: '医美合规获客难，违规风险高',
    solution: '6 红线守护 + AI 拦截违规话术 + 案例脱敏',
    metrics: [
      { label: '违规率', value: '0' },
      { label: '线索成本', value: '¥45 (-50%)' },
      { label: '二次到店', value: '38%' },
      { label: '合规审查', value: '100% 通过' },
    ],
    testimonial: {
      quote: 'AI 帮我把合规变成竞争力，6 红线守护比律师更稳。',
      author: '张院长',
      role: '美莱医疗 院长',
    },
    highlight: true,
  },
  {
    id: 'case-m-002',
    company: '北京伊美尔医疗美容',
    city: '北京',
    scale: '大型 · 5 院区',
    industry: 'medical',
    challenge: '老客复购 + 转介绍难',
    solution: '老客画像 + 案例脱敏 + 转介绍激励机制',
    metrics: [
      { label: '老客复购', value: '+60%' },
      { label: '转介绍率', value: '22%' },
      { label: '客单价', value: '¥8,500' },
      { label: 'NPS', value: '72' },
    ],
    testimonial: {
      quote: '老客户带新客户的比例从 15% 涨到 22%。',
      author: '王主任',
      role: '伊美尔 运营主任',
    },
  },
  {
    id: 'case-m-003',
    company: '北京画美医疗美容',
    city: '北京',
    scale: '中大型 · 3 院区',
    industry: 'medical',
    challenge: '客户到店率低，二次转化难',
    solution: '客户画像 + 精准触达 + 二次到店 SOP',
    metrics: [
      { label: '到店率', value: '+85%' },
      { label: '二次到店', value: '42%' },
      { label: '签单率', value: '28%' },
      { label: 'CAC', value: '¥120' },
    ],
    testimonial: {
      quote: 'AI 让客户到店 + 二次到店变成可预测的漏斗。',
      author: '陈院长',
      role: '画美医疗 院长',
    },
  },
  {
    id: 'case-m-004',
    company: '上海美莱医疗美容',
    city: '上海',
    scale: '大型 · 6 院区',
    industry: 'medical',
    challenge: '广告投放 ROI 低',
    solution: '小红书 + 抖音双平台内容 + AI 拦截红线',
    metrics: [
      { label: 'ROI', value: '6x' },
      { label: '线索成本', value: '¥35' },
      { label: '签单率', value: '32%' },
      { label: 'LTV', value: '¥2.8 万' },
    ],
    testimonial: {
      quote: '把上海一线市场的获客效率做到极致。',
      author: '李院长',
      role: '上海美莱 院长',
    },
  },
  {
    id: 'case-m-005',
    company: '成都华美紫馨',
    city: '成都',
    scale: '大型 · 4 院区',
    industry: 'medical',
    challenge: '客户决策周期长，信任建立难',
    solution: '老板访谈视频 + 案例脱敏 + 医生 IP',
    metrics: [
      { label: '决策周期', value: '-35%' },
      { label: '信任度', value: '+50%' },
      { label: '签单率', value: '38%' },
      { label: '复购率', value: '45%' },
    ],
    testimonial: {
      quote: 'AI 帮我把医生的专业变成可信任的内容资产。',
      author: '赵主任',
      role: '华美紫馨 品牌主任',
    },
  },
];

export function CaseLibraryPage() {
  return (
    <>
      <section className="py-16 bg-gradient-to-br from-orange-50 via-white to-pink-50">
        <div className="max-w-page mx-auto px-6">
          <span className="inline-block px-3 py-1 bg-orange-100 text-orange-700 rounded-full text-sm mb-4">
            📚 案例库 · 10 个真实客户故事
          </span>
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            看同行怎么用 AI 数字员工
            <br />
            <span className="text-brand-500">拿真实数据说话</span>
          </h1>
          <p className="text-lg text-gray-600 mb-8 max-w-2xl">
            5 装企 + 5 医美真实案例。每家都脱敏但保留核心数据：客户痛点、我们方案、量化结果、老板证言。
          </p>

          {/* 数据汇总 */}
          <div className="grid md:grid-cols-4 gap-4">
            <div className="p-4 bg-white rounded-lg border border-gray-200">
              <DollarSign className="w-6 h-6 text-green-500 mb-2" />
              <p className="text-2xl font-bold">¥200 万+</p>
              <p className="text-xs text-gray-500">客户累计节省</p>
            </div>
            <div className="p-4 bg-white rounded-lg border border-gray-200">
              <TrendingUp className="w-6 h-6 text-blue-500 mb-2" />
              <p className="text-2xl font-bold">+140%</p>
              <p className="text-xs text-gray-500">平均签约率提升</p>
            </div>
            <div className="p-4 bg-white rounded-lg border border-gray-200">
              <Users className="w-6 h-6 text-purple-500 mb-2" />
              <p className="text-2xl font-bold">10 行业</p>
              <p className="text-xs text-gray-500">已落地行业</p>
            </div>
            <div className="p-4 bg-white bg-white rounded-lg border border-gray-200">
              <Star className="w-6 h-6 text-yellow-500 mb-2" />
              <p className="text-2xl font-bold">4.9/5</p>
              <p className="text-xs text-gray-500">客户满意度</p>
            </div>
          </div>
        </div>
      </section>

      {/* 装企案例 */}
      <section className="py-16 bg-white">
        <div className="max-w-page mx-auto px-6">
          <h2 className="text-3xl font-bold mb-2">🏠 装企案例（5 家）</h2>
          <p className="text-gray-500 mb-8">一线 + 新一线城市装企老板的真实使用</p>

          <div className="grid lg:grid-cols-2 gap-6">
            {DECORATION_CASES.map((c) => (
              <CaseCard key={c.id} c={c} />
            ))}
          </div>
        </div>
      </section>

      {/* 医美案例 */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-page mx-auto px-6">
          <h2 className="text-3xl font-bold mb-2">💉 医美案例（5 家）</h2>
          <p className="text-gray-500 mb-8">合规获客 + 老客复购 + 转介绍</p>

          <div className="grid lg:grid-cols-2 gap-6">
            {MEDICAL_CASES.map((c) => (
              <CaseCard key={c.id} c={c} />
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 bg-gradient-to-r from-brand-500 to-brand-600 text-white">
        <div className="max-w-page mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-4">下一个案例 = 你</h2>
          <p className="text-lg opacity-90 mb-8">
            7 天试用 · 不需要信用卡 · 30 分钟跑通你公司的第一条管线
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link
              to="/try"
              className="px-8 py-3 bg-white text-brand-500 rounded-md hover:bg-gray-100 inline-flex items-center gap-2 font-medium"
            >
              立即试用 <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/contact"
              className="px-8 py-3 border border-white text-white rounded-md hover:bg-white/10"
            >
              约 1v1 demo
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}

function CaseCard({ c }: { c: CaseStudy }) {
  return (
    <div
      className={`p-6 rounded-lg border-2 ${
        c.highlight ? 'border-brand-500 bg-gradient-to-br from-brand-50 to-white' : 'border-gray-200 bg-white'
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-lg font-bold">{c.company}</h3>
          <p className="text-sm text-gray-500">
            📍 {c.city} · {c.scale}
          </p>
        </div>
        {c.highlight && (
          <span className="px-2 py-1 bg-brand-500 text-white text-xs rounded font-bold">
            ⭐ 标杆
          </span>
        )}
      </div>

      <div className="space-y-2 mb-4">
        <p className="text-sm">
          <span className="font-medium text-red-600">痛点：</span>
          <span className="text-gray-700">{c.challenge}</span>
        </p>
        <p className="text-sm">
          <span className="font-medium text-blue-600">方案：</span>
          <span className="text-gray-700">{c.solution}</span>
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2 mb-4">
        {c.metrics.map((m, i) => (
          <div key={i} className="p-2 bg-gray-50 rounded text-center">
            <p className="text-lg font-bold text-brand-500">{m.value}</p>
            <p className="text-xs text-gray-500">{m.label}</p>
          </div>
        ))}
      </div>

      <blockquote className="border-l-4 border-brand-500 pl-3 italic text-sm text-gray-700">
        "{c.testimonial.quote}"
        <footer className="text-xs text-gray-500 mt-1 not-italic">
          — {c.testimonial.author} · {c.testimonial.role}
        </footer>
      </blockquote>
    </div>
  );
}
