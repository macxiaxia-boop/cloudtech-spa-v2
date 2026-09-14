// 博客列表页 · SEO 内容 · OPC 故事 + 行业洞察
import { Link } from 'react-router-dom';
import { Calendar, Clock, ArrowRight, BookOpen, Tag } from 'lucide-react';

interface BlogPost {
  id: string;
  title: string;
  excerpt: string;
  category: 'opc-story' | 'industry' | 'tech' | 'case';
  date: string;
  readTime: string;
  author: string;
  tags: string[];
  featured?: boolean;
}

const POSTS: BlogPost[] = [
  {
    id: 'opc-day-1',
    title: 'OPC Day 1：阿劲一个人 + 5 AI 数字员工，开了一家 SaaS 公司',
    excerpt:
      '我叫阿劲，灵策智算的创始人。今天是我一个人创办 SaaS 的第 1 天。团队 = 我 + 5 AI 员工（Hermes/Lyra/Athena/Apollo/Artemis）。我把今天干了啥写下来，给自己留个档。',
    category: 'opc-story',
    date: '2026-09-14',
    readTime: '8 分钟',
    author: '阿劲',
    tags: ['OPC', '创业日记', 'AI 数字员工'],
    featured: true,
  },
  {
    id: 'opc-day-30',
    title: 'OPC Day 30：30 天跑出 80 家客户清单 + 16 份公司文档',
    excerpt:
      '30 天，1 人 + 5 AI 员工。产出：80 家客户清单（P0/P1/P2/P3）+ 16 份公司文档（合同 / HR / 财务 / 营销 / 合规）+ 11 个 SPA 页面 + 208 测试 PASS。一场 OPC 实验的完整复盘。',
    category: 'opc-story',
    date: '2026-09-14',
    readTime: '12 分钟',
    author: '阿劲',
    tags: ['OPC', '复盘', 'SaaS'],
  },
  {
    id: 'phase-41-44-rules',
    title: 'Phase 41-44 内容生产：4 主题派最优规律（实战派深度型派 1.0）',
    excerpt:
      '灵策智算 4 个主题的内容生产实证：金句型 → 派 2.0（Phase 41）/ 实战派深度型教训向 → 派 1.0（Phase 42）/ 方法论向 → 派 1.0（Phase 43）/ 场景向 → 派 1.0（Phase 44）。规律：实战派深度型 = 派 1.0 实证稳定。',
    category: 'tech',
    date: '2026-09-13',
    readTime: '15 分钟',
    author: '阿劲 + Lyra AI',
    tags: ['内容生产', 'AI', '4 主题派最优'],
  },
  {
    id: 'red-line-22',
    title: '红 #22 Layer 15 治理边界：OPC 模式的 4 不可逆闸门',
    excerpt:
      'OPC 不是无边界。4 类必用户亲自触发：合同签字 / 钱进出 / 招聘 offer / 客户首单承诺。其余 AI 全程自治。49 条红线守护 = 内部 AI 就绪 + 外部必用户拍板。',
    category: 'tech',
    date: '2026-09-13',
    readTime: '10 分钟',
    author: '阿劲 + Hermes AI',
    tags: ['OPC', '红 #22', '治理边界'],
  },
  {
    id: 'case-decoration-huaning',
    title: '案例：成都华宁装饰 1 个月把签约率从 5% 干到 12%',
    excerpt:
      '成都华宁装饰老板王总的故事。单条线索 ¥80 → ¥28，签约 5% → 12%。怎么用 CloudTech 5 步法（客户画像 → 报价拆解 → 获客内容 → 工地直播 → AI 复盘）跑的。',
    category: 'case',
    date: '2026-09-12',
    readTime: '8 分钟',
    author: '阿劲',
    tags: ['装企案例', '成都', '获客'],
  },
  {
    id: 'case-medical-meilai',
    title: '案例：北京美莱医疗美容 6 红线守护 = 合规变成竞争力',
    excerpt:
      '医美行业最大痛点 = 合规。北京美莱张院长用 CloudTech 6 红线守护 + AI 拦截违规话术 + 案例脱敏。0 违规，二次到店率 38%。',
    category: 'case',
    date: '2026-09-12',
    readTime: '10 分钟',
    author: '阿劲',
    tags: ['医美案例', '北京', '合规'],
  },
  {
    id: 'industry-decoration-2026',
    title: '装企 2026 趋势：从抖音投流到工地直播',
    excerpt:
      '装企老板必看。抖音投流成本 ¥80+，签约率 5%。工地直播成本 ¥0，签约率 12%。5 步法落地 SOP。3 个标杆案例（成都 / 杭州 / 苏州）。',
    category: 'industry',
    date: '2026-09-10',
    readTime: '12 分钟',
    author: '阿劲 + Artemis AI',
    tags: ['装企', '2026 趋势', '工地直播'],
  },
  {
    id: 'industry-medical-compliance',
    title: '医美 6 红线 + 5 法规：老板必读合规手册',
    excerpt:
      '《医疗广告管理办法》+《医疗美容服务管理办法》+ 4 部医美法规解读。AI 拦截逻辑 + 6 红线实操 + 案例脱敏模板。老板 / 运营 / 内容三方都该看。',
    category: 'industry',
    date: '2026-09-08',
    readTime: '14 分钟',
    author: '阿劲 + Hermes AI',
    tags: ['医美', '合规', '6 红线'],
  },
  {
    id: 'red-line-25-constitution',
    title: '红 #25 自治系统宪法：8 daemon + 3 detector + 9 cron 的自我修复',
    excerpt:
      'CloudTech 内部的自我修复系统：8 daemon（D1-D8）+ 3 detector（drift/stall/loop）+ 9 cron 守护。8 分钟读懂这套 OPC 自治系统。',
    category: 'tech',
    date: '2026-09-05',
    readTime: '18 分钟',
    author: '阿劲 + Athena AI',
    tags: ['OPC', '红 #25', '自治系统'],
  },
];

const CATEGORY_LABELS = {
  'opc-story': { label: 'OPC 故事', color: 'bg-purple-100 text-purple-700' },
  industry: { label: '行业洞察', color: 'bg-blue-100 text-blue-700' },
  tech: { label: '技术', color: 'bg-green-100 text-green-700' },
  case: { label: '客户案例', color: 'bg-orange-100 text-orange-700' },
};

export function BlogPage() {
  const featured = POSTS.find((p) => p.featured);
  const others = POSTS.filter((p) => !p.featured);

  return (
    <>
      <section className="py-16 bg-gradient-to-br from-green-50 via-white to-blue-50">
        <div className="max-w-page mx-auto px-6 text-center">
          <span className="inline-block px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm mb-4">
            📝 博客 · OPC 故事 + 行业洞察
          </span>
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            1 人 + AI 的 <span className="text-brand-500">实战手记</span>
          </h1>
          <p className="text-lg text-gray-600">
            阿劲 + 5 AI 员工的真实运营记录 · 行业案例 · 技术内幕
          </p>
        </div>
      </section>

      {/* 头条 */}
      {featured && (
        <section className="py-12 bg-white">
          <div className="max-w-page mx-auto px-6">
            <Link
              to={`/blog/${featured.id}`}
              className="block p-8 bg-gradient-to-br from-purple-50 to-white border-2 border-purple-200 rounded-2xl hover:shadow-lg transition"
            >
              <div className="flex items-center gap-2 mb-3">
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${CATEGORY_LABELS[featured.category].color}`}>
                  ⭐ {CATEGORY_LABELS[featured.category].label}
                </span>
                <span className="text-xs text-gray-500">{featured.date} · {featured.readTime}</span>
              </div>
              <h2 className="text-3xl font-bold mb-3">{featured.title}</h2>
              <p className="text-gray-600 mb-4">{featured.excerpt}</p>
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-500">作者：{featured.author}</p>
                <span className="text-brand-500 font-medium flex items-center gap-1">
                  阅读全文 <ArrowRight className="w-4 h-4" />
                </span>
              </div>
            </Link>
          </div>
        </section>
      )}

      {/* 列表 */}
      <section className="py-12 bg-gray-50">
        <div className="max-w-page mx-auto px-6">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
            <BookOpen className="w-6 h-6" /> 最新文章
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            {others.map((p) => (
              <Link
                key={p.id}
                to={`/blog/${p.id}`}
                className="block p-6 bg-white rounded-lg border border-gray-200 hover:border-brand-500 hover:shadow transition"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${CATEGORY_LABELS[p.category].color}`}>
                    {CATEGORY_LABELS[p.category].label}
                  </span>
                  <span className="text-xs text-gray-500 flex items-center gap-1">
                    <Calendar className="w-3 h-3" /> {p.date}
                  </span>
                  <span className="text-xs text-gray-500 flex items-center gap-1">
                    <Clock className="w-3 h-3" /> {p.readTime}
                  </span>
                </div>
                <h3 className="text-xl font-bold mb-2 hover:text-brand-500">{p.title}</h3>
                <p className="text-sm text-gray-600 mb-3 line-clamp-2">{p.excerpt}</p>
                <div className="flex items-center justify-between">
                  <div className="flex flex-wrap gap-1">
                    {p.tags.map((t) => (
                      <span key={t} className="inline-flex items-center gap-0.5 text-xs text-gray-500">
                        <Tag className="w-3 h-3" /> {t}
                      </span>
                    ))}
                  </div>
                  <span className="text-sm text-brand-500">阅读 →</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* 跨页面引导 */}
      <section className="py-12 bg-white">
        <div className="max-w-page mx-auto px-6 text-center">
          <h3 className="text-xl font-bold mb-4">看完了？动手试一下</h3>
          <p className="text-sm text-gray-500 mb-6">看 5 AI 员工实时在干啥 / 进你的客户后台</p>
          <div className="flex items-center justify-center gap-3">
            <Link
              to="/employees"
              className="px-5 py-2 bg-brand-500 text-white rounded-md hover:bg-brand-600 inline-flex items-center gap-1"
            >
              看 5 AI 员工 <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/dashboard"
              className="px-5 py-2 border border-gray-300 rounded-md hover:border-brand-500 inline-flex items-center gap-1"
            >
              进客户后台 <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
