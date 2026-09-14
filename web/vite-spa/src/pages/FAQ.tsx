// FAQ 帮助中心页 · 折叠式 + 分类 + 搜索
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown, Search, MessageCircle } from 'lucide-react';
import { FilterBar } from '../components/FilterBar';
import { EmptyState } from '../components/EmptyState';

interface FAQ {
  q: string;
  a: string;
  category: 'getting-started' | 'pricing' | 'tech' | 'compliance' | 'team';
  helpful: number;
}

const FAQS: FAQ[] = [
  {
    q: 'CloudTech 适合什么规模的公司？',
    a: 'OPC 模式专为 1-10 人小公司设计。如果你有 1-2 名员工 + 想要 AI 帮跑业务，CloudTech 就是为你做的。超过 50 人团队建议考虑定制版。',
    category: 'getting-started',
    helpful: 128,
  },
  {
    q: '我完全不懂技术也能用吗？',
    a: '可以。CloudTech 是 SaaS，开箱即用。你只需要：① 注册账号 ② 选 5 AI 员工 ③ 告诉它们你想跑啥。技术细节（数据库/API/cron）全部由 AI 自己搞定。',
    category: 'getting-started',
    helpful: 256,
  },
  {
    q: '7 天试用是真的免费吗？',
    a: '真的。无需信用卡。7 天内你可以用全部功能（5 AI 员工 + 监控 + 财务 + 客户管理）。到期后自动转为免费版（功能受限）。',
    category: 'pricing',
    helpful: 198,
  },
  {
    q: '3 套餐价格分别是多少？',
    a: '轻装版 ¥299/月（适合 1-2 人小团队），标准版 ¥999/月（适合 5-10 人中型团队），旗舰版 ¥3,999/月（含定制 + 专属客服）。年付 8 折。',
    category: 'pricing',
    helpful: 156,
  },
  {
    q: '5 AI 数字员工具体做什么？',
    a: 'Hermes（治理）/ Lyra（内容）/ Athena（架构）/ Apollo（数据）/ Artemis（运营）。你可以给它们分配任务（写文案 / 拉客户 / 算财务 / 看监控），它们 7×24 跑。',
    category: 'getting-started',
    helpful: 89,
  },
  {
    q: '我的数据安全吗？',
    a: '数据存放在阿里云上海集群，符合《个人信息保护法》。传输加密 + 存储加密 + 备份 3 副本。你可随时导出 / 删除。详见《数据处理协议》（DPA）。',
    category: 'compliance',
    helpful: 234,
  },
  {
    q: '医美 / 装企有合规要求吗？',
    a: '有。医美 6 红线守护（《医疗广告管理办法》+《医疗美容服务管理办法》）。AI 自动拦截违规话术 + 案例脱敏 + 价格透明。装企无特殊合规要求。',
    category: 'compliance',
    helpful: 167,
  },
  {
    q: '能定制开发吗？',
    a: '可以。旗舰版包含 5 人天定制开发额度。超过部分按 ¥3,000/人天。也可以直接招我们的 FE 工程师（¥25-35K/月+期权）。',
    category: 'pricing',
    helpful: 78,
  },
  {
    q: '5 AI 员工是真人还是机器人？',
    a: '都是 AI 数字员工（基于多 LLM：Claude / GPT / Doubao 混合路由）。它们可以：① 7×24 跑不累 ② 0 工资成本 ③ 任务标准化 ④ 数据可追溯。但无法替代真人的「战略决策 + 客户关系」。',
    category: 'tech',
    helpful: 145,
  },
  {
    q: '如果 AI 跑了错的事怎么办？',
    a: '3 道保险：① 红线守护（49 条，AI 触红线自动停）② 重要动作必你拍板（发合同 / 付费 / 客户跟进 / 招聘 offer）③ 实时监控 + 告警。所有 AI 行为都有日志可追溯。',
    category: 'tech',
    helpful: 198,
  },
  {
    q: '可以换套餐吗？',
    a: '随时可以。升级立即生效，差价按天补。降档下个计费周期生效。数据完整保留。',
    category: 'pricing',
    helpful: 67,
  },
  {
    q: 'OPC 模式是什么？',
    a: 'OPC = One Person + Company = 1 人 + AI 的整家公司。CloudTech 自己是 OPC 模式跑出来的（创始人阿劲 1 人 + 5 AI 员工）。我们把同样的工具开放给你。',
    category: 'getting-started',
    helpful: 312,
  },
  {
    q: '能团队协作吗？',
    a: '可以。轻装版 1 人，标准版 5 人，旗舰版 20 人。团队成员有不同的角色权限（管理员 / 销售 / 运营 / 只读）。',
    category: 'team',
    helpful: 92,
  },
  {
    q: '支持哪些支付方式？',
    a: '微信支付、支付宝、企业网银（公对公转账）。年付可签合同 + 开增票。',
    category: 'pricing',
    helpful: 56,
  },
  {
    q: '有 API 吗？',
    a: '有。标准版起开放 RESTful API + Webhook。可对接你的内部 CRM / ERP / BI 系统。详见 /docs/api。',
    category: 'tech',
    helpful: 134,
  },
];

const CATEGORIES = [
  { label: '全部', value: 'all' },
  { label: '🚀 新手入门', value: 'getting-started' },
  { label: '💰 定价', value: 'pricing' },
  { label: '🔧 技术', value: 'tech' },
  { label: '🛡️ 合规', value: 'compliance' },
  { label: '👥 团队', value: 'team' },
];

export function FAQPage() {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('all');
  const [openId, setOpenId] = useState<number | null>(0);

  const filtered = FAQS.filter((f) => {
    const matchCat = category === 'all' || f.category === category;
    const matchSearch =
      !search ||
      f.q.toLowerCase().includes(search.toLowerCase()) ||
      f.a.toLowerCase().includes(search.toLowerCase());
    return matchCat && matchSearch;
  });

  return (
    <>
      <section className="py-16 bg-gradient-to-br from-blue-50 via-white to-purple-50 overflow-hidden">
        <div className="max-w-page mx-auto px-6 grid md:grid-cols-2 gap-10 items-center">
          <div className="text-center md:text-left">
            <span className="inline-block px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm mb-4">
              💬 帮助中心
            </span>
            <h1 className="text-4xl md:text-5xl font-bold mb-4">
              你想问的，<span className="text-brand-500">都在这</span>
            </h1>
            <p className="text-lg text-gray-600 mb-6">
              15 个最常见问题 · 按分类找 · 搜不到就联系我们
            </p>
            <div className="grid grid-cols-3 gap-3 mt-6 pt-6 border-t border-gray-200">
              <div>
                <p className="text-2xl font-bold text-brand-500">15</p>
                <p className="text-xs text-gray-500">常见问题</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-brand-500">5</p>
                <p className="text-xs text-gray-500">分类</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-brand-500">1280+</p>
                <p className="text-xs text-gray-500">helpful 数</p>
              </div>
            </div>
          </div>
          <div>
            <img
              src="/images/faq-hero.jpeg"
              alt="FAQ 帮助中心"
              className="rounded-2xl shadow-2xl w-full"
            />
          </div>
        </div>
      </section>

      <section className="py-8 bg-white border-b border-gray-200">
        <div className="max-w-page mx-auto px-6">
          <div className="max-w-2xl mx-auto relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="搜问题或关键词..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-12 pr-4 py-4 border-2 border-gray-200 rounded-lg focus:border-brand-500 focus:outline-none text-lg"
            />
          </div>
        </div>
      </section>

      {/* 分类 */}
      <section className="py-6 bg-white border-b border-gray-200 sticky top-16 z-30">
        <div className="max-w-page mx-auto px-6">
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map((c) => (
              <button
                key={c.value}
                onClick={() => setCategory(c.value)}
                className={`px-4 py-2 rounded-md text-sm transition ${
                  category === c.value
                    ? 'bg-brand-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ 列表 */}
      <section className="py-12 bg-gray-50">
        <div className="max-w-4xl mx-auto px-6">
          {filtered.length === 0 ? (
            <EmptyState
              illustration="chat"
              title="没找到答案？"
              desc="试其他关键词，或直接联系我们"
              cta={
                <Link to="/contact" className="px-6 py-2 bg-brand-500 text-white rounded-md">
                  联系客服
                </Link>
              }
            />
          ) : (
            <div className="space-y-3">
              {filtered.map((f, i) => (
                <FAQItem
                  key={i}
                  f={f}
                  open={openId === i}
                  onToggle={() => setOpenId(openId === i ? null : i)}
                />
              ))}
            </div>
          )}
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 bg-white">
        <div className="max-w-page mx-auto px-6 text-center">
          <MessageCircle className="w-12 h-12 text-brand-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold mb-4">还没找到答案？</h2>
          <p className="text-gray-600 mb-6">3 种方式联系我们：1v1 demo / 微信群 / 邮件</p>
          <div className="flex items-center justify-center gap-4">
            <Link to="/contact" className="px-6 py-3 bg-brand-500 text-white rounded-md hover:bg-brand-600">
              约 1v1 demo
            </Link>
            <a
              href="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
              className="px-6 py-3 border border-gray-300 rounded-md hover:border-brand-500"
            >
              加入微信群
            </a>
          </div>
        </div>
      </section>
    </>
  );
}

function FAQItem({ f, open, onToggle }: { f: FAQ; open: boolean; onToggle: () => void }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full px-6 py-4 text-left flex items-center justify-between gap-4 hover:bg-gray-50"
      >
        <span className="font-medium flex-1">{f.q}</span>
        <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="px-6 pb-4 text-gray-700 border-t border-gray-100 pt-3">
          <p className="mb-3">{f.a}</p>
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>👍 {f.helpful} 人觉得有帮助</span>
            <Link to="/contact" className="text-brand-500 hover:underline">
              没解决？联系我们
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
