// Phase 46 D45-48 — 内容生产 SOP 工具页（Phase 41-44 4 主题派最优规律可视化）
import { Link } from 'react-router-dom';
import { BookOpen, ArrowRight, Sparkles, Trophy, GitBranch, Zap, CheckCircle2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface Template {
  phase: string;
  theme: string;
  type: '金句型' | '实战派深度型';
  subtype?: '教训向' | '方法论向' | '场景向';
  v1_words: number;
  v2_words: number;
  compression: string;
  score_v1: string;
  score_v2: string;
  winner: '1.0' | '2.0';
  rationale: string;
  redlines: string[];
  author_voice: string;
}

const TEMPLATES: Template[] = [
  {
    phase: 'Phase 41',
    theme: 'Cloud ToB SaaS',
    type: '金句型',
    v1_words: 4260,
    v2_words: 3500,
    compression: '-15%',
    score_v1: '95+95+100',
    score_v2: '95+95+100',
    winner: '2.0',
    rationale: '金句型主题 → 豆包压缩损失小（仅 -15%）→ 2.0 表达维度可冲 95 → 派 2.0 更精炼',
    redlines: ['#15.5 对比派最优', '#16 双轨评分卡', '#13 风格库字面'],
    author_voice: '半佛仙人风格 · 灵魂金句密度高',
  },
  {
    phase: 'Phase 42',
    theme: 'Cloud"5 个产品坑"',
    type: '实战派深度型',
    subtype: '教训向',
    v1_words: 3300,
    v2_words: 1500,
    compression: '-55%',
    score_v1: '95+95+100',
    score_v2: '95+90+100',
    winner: '1.0',
    rationale: '实战派深度型教训向 → 豆包压缩 -55% → 2.0 表达 90 未冲 95 → 派 1.0 保留场景细节',
    redlines: ['#15.5 对比派最优', '#16 双轨评分卡', '#14 内容深度优先'],
    author_voice: '小A学财经风格 · 复盘 5 个真实产品坑',
  },
  {
    phase: 'Phase 43',
    theme: 'Cloud"定价心法"',
    type: '实战派深度型',
    subtype: '方法论向',
    v1_words: 3500,
    v2_words: 1700,
    compression: '-51%',
    score_v1: '95+95+100',
    score_v2: '95+92+100',
    winner: '1.0',
    rationale: '实战派深度型方法论向 → 豆包压缩 -51% → 2.0 表达 92 接近但未冲 95 → 派 1.0 保留哲学深度',
    redlines: ['#15.5 对比派最优', '#16 双轨评分卡', '#14 内容深度优先'],
    author_voice: '小A学财经风格 · 3 段式定价方法论',
  },
  {
    phase: 'Phase 44',
    theme: 'Cloud"5 个客户问题"',
    type: '实战派深度型',
    subtype: '场景向',
    v1_words: 3500,
    v2_words: 1500,
    compression: '-57%',
    score_v1: '95+95+100',
    score_v2: '95+92+100',
    winner: '1.0',
    rationale: '实战派深度型场景向 → 豆包压缩 -57% → 2.0 表达 92 接近但未冲 95 → 派 1.0 保留客户场景',
    redlines: ['#15.5 对比派最优', '#16 双轨评分卡', '#14 内容深度优先'],
    author_voice: '小A学财经风格 · 5 个真实客户场景',
  },
];

const DECISION_TREE = [
  {
    question: '主题是什么类型？',
    options: [
      { type: '金句型', next: '金句密度高 / 表达犀利 / 短句为主', example: 'Phase 41 ToB SaaS' },
      { type: '实战派深度型', next: '场景细节 / 哲学深度 / 复盘 / 长段', example: 'Phase 42-44' },
    ],
  },
  {
    question: '豆包压缩比例？',
    options: [
      { type: '< 30%', next: '2.0 可冲 95 → 派 2.0（更精炼）', example: 'Phase 41 -15%' },
      { type: '> 50%', next: '2.0 难冲 95 → 派 1.0（灵魂版）', example: 'Phase 42-44 -51~-57%' },
    ],
  },
];

export function ContentSOPPage() {
  return (
    <>
      {/* HERO */}
      <section className="relative py-20 bg-gradient-to-br from-indigo-50 via-white to-purple-50">
        <div className="max-w-page mx-auto px-6">
          <div className="max-w-3xl">
            <span className="inline-flex items-center gap-2 px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm mb-4">
              <BookOpen className="w-3 h-3" /> 内容生产 SOP · Phase 41-44 四主题跑通
            </span>
            <h1 className="text-4xl md:text-5xl font-bold mb-4 leading-[1.1]">
              内容生产 SOP 工具
              <br />
              <span className="text-indigo-500">让 AI 替你跑"原版 + 优化版"双轨对比</span>
            </h1>
            <p className="text-lg text-gray-600 mb-8">
              基于Cloud Phase 41-44 四主题实战跑通，
              红线 #15.5 对比派最优 + 红线 #16 双轨评分卡，
              自动判主题类型 → 自动派最优版。
            </p>
            <div className="flex gap-4">
              <Link
                to="/login"
                className="px-6 py-3 bg-indigo-500 text-white rounded-md hover:bg-indigo-600 inline-flex items-center gap-2"
              >
                立即使用 <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/pricing"
                className="px-6 py-3 border border-gray-300 rounded-md hover:border-indigo-500"
              >
                查看定价
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* 4 主题模板库 */}
      <section className="py-20 bg-white">
        <div className="max-w-page mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-3">4 主题派最优规律（实证 4/4 稳定）</h2>
            <p className="text-gray-600">每条规律都经过 Phase 41-44 完整跑通验证</p>
          </div>
          <div className="space-y-6">
            {TEMPLATES.map((t) => (
              <div key={t.phase} className="p-6 bg-gray-50 rounded-lg border border-gray-200">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 text-xs rounded font-mono">
                        {t.phase}
                      </span>
                      <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">
                        {t.type}{t.subtype ? ` · ${t.subtype}` : ''}
                      </span>
                      <span className={`px-2 py-0.5 text-xs rounded font-medium ${
                        t.winner === '1.0'
                          ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-green-100 text-green-700'
                      }`}>
                        <Trophy className="w-3 h-3 inline mr-1" />
                        派 {t.winner}
                      </span>
                    </div>
                    <h3 className="text-xl font-bold mb-1">{t.theme}</h3>
                    <p className="text-sm text-gray-500">{t.author_voice}</p>
                  </div>
                </div>

                <div className="grid md:grid-cols-4 gap-4 mb-4">
                  <div className="p-3 bg-white rounded border border-gray-200">
                    <p className="text-xs text-gray-500">原版 1.0</p>
                    <p className="text-2xl font-bold">{t.v1_words.toLocaleString()} 字</p>
                    <p className="text-xs text-green-600 mt-1">{t.score_v1}</p>
                  </div>
                  <div className="p-3 bg-white rounded border border-gray-200">
                    <p className="text-xs text-gray-500">豆包优化 2.0</p>
                    <p className="text-2xl font-bold">{t.v2_words.toLocaleString()} 字</p>
                    <p className="text-xs text-green-600 mt-1">{t.score_v2}</p>
                  </div>
                  <div className="p-3 bg-white rounded border border-gray-200">
                    <p className="text-xs text-gray-500">压缩比例</p>
                    <p className="text-2xl font-bold text-orange-600">{t.compression}</p>
                    <p className="text-xs text-gray-400 mt-1">2.0 vs 1.0</p>
                  </div>
                  <div className="p-3 bg-white rounded border border-gray-200">
                    <p className="text-xs text-gray-500">派最优</p>
                    <p className={`text-2xl font-bold ${t.winner === '1.0' ? 'text-yellow-600' : 'text-green-600'}`}>
                      {t.winner}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">主题决定</p>
                  </div>
                </div>

                <div className="p-3 bg-white rounded border border-gray-200">
                  <p className="text-sm text-gray-700">
                    <span className="font-medium">理由: </span>{t.rationale}
                  </p>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {t.redlines.map((r) => (
                      <span key={r} className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
                        {r}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 决策树 */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-page mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-3">
              <GitBranch className="w-6 h-6 inline mr-2" />
              2 步决策树
            </h2>
            <p className="text-gray-600">按主题类型 + 压缩比例 → 自动派最优版</p>
          </div>
          <div className="max-w-3xl mx-auto space-y-6">
            {DECISION_TREE.map((step, i) => (
              <div key={i} className="p-6 bg-white rounded-lg border-2 border-indigo-200">
                <div className="flex items-center gap-3 mb-4">
                  <span className="flex items-center justify-center w-8 h-8 bg-indigo-500 text-white rounded-full font-bold">
                    {i + 1}
                  </span>
                  <h3 className="text-lg font-bold">{step.question}</h3>
                </div>
                <div className="grid md:grid-cols-2 gap-3">
                  {step.options.map((opt) => (
                    <div key={opt.type} className="p-3 bg-gray-50 rounded border border-gray-200">
                      <p className="text-sm font-bold text-indigo-700 mb-1">{opt.type}</p>
                      <p className="text-sm text-gray-600 mb-1">{opt.next}</p>
                      <p className="text-xs text-gray-400">实证: {opt.example}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 4 大特点 */}
      <section className="py-20 bg-white">
        <div className="max-w-page mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-3">为什么用对比派最优？</h2>
          </div>
          <div className="grid md:grid-cols-4 gap-6">
            {[
              { icon: Sparkles, title: '1.0 灵魂版', desc: '保留原汁原味风格 · 不被算法抹平' },
              { icon: Zap, title: '2.0 精炼版', desc: '豆包压缩后可读性更强' },
              { icon: CheckCircle2, title: '3 维评分', desc: '形式 + 表达 + 合规 · 总评 min' },
              { icon: Trophy, title: '主题决定', desc: '金句型→2.0 · 实战派→1.0' },
            ].map((f, i) => (
              <div key={i} className="text-center p-6 bg-gray-50 rounded-lg border border-gray-200">
                <f.icon className="w-10 h-10 mx-auto mb-3 text-indigo-500" />
                <h3 className="text-base font-bold mb-2">{f.title}</h3>
                <p className="text-sm text-gray-600">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-indigo-500 text-white">
        <div className="max-w-page mx-auto px-6 text-center">
          <Sparkles className="w-12 h-12 mx-auto mb-4" />
          <h2 className="text-3xl font-bold mb-4">Phase 41-44 四主题跑通，规律已稳定</h2>
          <p className="text-lg opacity-90 mb-8">7 天免费试用 · 双轨对比 · 自动派最优</p>
          <Link
            to="/login"
            className="px-8 py-3 bg-white text-indigo-500 rounded-md hover:bg-gray-100 inline-flex items-center gap-2 font-medium"
          >
            立即开始 <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </>
  );
}
