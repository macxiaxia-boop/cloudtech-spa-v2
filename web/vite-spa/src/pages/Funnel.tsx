// Phase 48.D84 · 漏斗数据可视化页（用 funnel.ts 数据）
// 5 状态机：待跟进 → 已联系 → 演示 → 试用 → 签约
import { Link } from 'react-router-dom';
import { TrendingDown, Lightbulb, AlertCircle, ArrowRight, Users, Phone, Film, FlaskConical, CheckCircle2 } from 'lucide-react';
import { FUNNEL_SNAPSHOT, FUNNEL_INSIGHTS, OVERALL_CONVERSION } from '../data/funnel';

const STAGE_ICONS: Record<string, any> = {
  lead: Users,
  contacted: Phone,
  demo: Film,
  trial: FlaskConical,
  signed: CheckCircle2,
};

export function FunnelPage() {
  const maxCount = Math.max(...FUNNEL_SNAPSHOT.stages.map(s => s.count));

  return (
    <>
      {/* HERO */}
      <section className="relative py-16 bg-gradient-to-br from-orange-50 via-white to-red-50 overflow-hidden">
        <div className="max-w-page mx-auto px-6 grid md:grid-cols-2 gap-10 items-center">
          <div>
            <span className="inline-flex items-center gap-2 px-3 py-1 bg-orange-100 text-orange-700 rounded-full text-sm mb-4">
              <TrendingDown className="w-3 h-3" /> Phase 48.D84 · 客户漏斗
            </span>
            <h1 className="text-4xl md:text-5xl font-bold mb-4 leading-[1.1]">
              80 → 1 的<br />
              <span className="text-orange-600">真实转化漏斗</span>
            </h1>
            <p className="text-lg text-gray-600 mb-6">
              5 状态机全透明 · 每一步转化率 + 流失原因可追溯
              <br />
              <span className="text-sm text-gray-500">{FUNNEL_SNAPSHOT.period}</span>
            </p>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-6 border-t border-gray-200">
              <div>
                <p className="text-2xl font-bold text-orange-600">{FUNNEL_SNAPSHOT.total_leads}</p>
                <p className="text-xs text-gray-500">待跟进</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-orange-600">5</p>
                <p className="text-xs text-gray-500">状态机</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-orange-600">{OVERALL_CONVERSION.toFixed(2)}%</p>
                <p className="text-xs text-gray-500">总转化率</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-orange-600">{FUNNEL_INSIGHTS.length}</p>
                <p className="text-xs text-gray-500">洞察</p>
              </div>
            </div>
          </div>
          <div>
            {/* 漏斗可视化 */}
            <div className="bg-white p-6 rounded-2xl shadow-2xl">
              <h3 className="font-bold text-lg mb-4 text-center">漏斗可视化</h3>
              <div className="space-y-3">
                {FUNNEL_SNAPSHOT.stages.map((stage, idx) => {
                  const Icon = STAGE_ICONS[stage.stage] || Users;
                  const width = (stage.count / maxCount) * 100;
                  const prevStage = idx > 0 ? FUNNEL_SNAPSHOT.stages[idx - 1] : null;
                  const conv = prevStage && prevStage.count > 0
                    ? ((stage.count / prevStage.count) * 100).toFixed(1)
                    : null;
                  return (
                    <div key={stage.stage}>
                      <div className="flex items-center justify-between mb-1 text-sm">
                        <span className={`font-medium ${stage.color}`}>
                          {stage.icon} {stage.label}
                        </span>
                        <span className="text-gray-700 font-bold">{stage.count}</span>
                      </div>
                      <div className="h-8 bg-gray-100 rounded-md overflow-hidden relative">
                        <div
                          className="h-full bg-gradient-to-r from-orange-400 to-red-500 flex items-center justify-end px-2 text-white text-xs font-bold"
                          style={{ width: `${width}%` }}
                        >
                          {width > 25 && `${width.toFixed(0)}%`}
                        </div>
                      </div>
                      {conv && (
                        <p className="text-xs text-gray-500 mt-1">
                          ↳ 上一阶段转化率 <span className="font-bold text-orange-600">{conv}%</span>
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 转化率明细 */}
      <section className="py-12 bg-white border-b border-gray-100">
        <div className="max-w-page mx-auto px-6">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
            <TrendingDown className="w-6 h-6 text-orange-500" />
            转化率明细（流失原因可追溯）
          </h2>
          <div className="grid md:grid-cols-2 gap-4">
            {FUNNEL_SNAPSHOT.conversions.map((c, i) => (
              <div key={i} className="p-5 bg-gradient-to-br from-orange-50 to-white border border-orange-200 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600">
                    {FUNNEL_SNAPSHOT.stages[i].label} → {FUNNEL_SNAPSHOT.stages[i + 1].label}
                  </span>
                  <span className="text-2xl font-bold text-orange-600">{c.rate.toFixed(1)}%</span>
                </div>
                <div className="flex items-start gap-2 text-xs text-gray-600">
                  <AlertCircle className="w-3 h-3 mt-0.5 flex-shrink-0 text-red-500" />
                  <span>主要流失：{c.drop_reason}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 4 大洞察 */}
      <section className="py-12 bg-gray-50">
        <div className="max-w-page mx-auto px-6">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
            <Lightbulb className="w-6 h-6 text-yellow-500" />
            4 大转化优化洞察
          </h2>
          <div className="grid md:grid-cols-2 gap-4">
            {FUNNEL_INSIGHTS.map((ins, i) => (
              <div key={i} className="p-5 bg-white rounded-lg border border-gray-200 hover:shadow-md transition">
                <div className="flex items-start gap-3 mb-3">
                  <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs rounded font-bold">
                    洞察 #{i + 1}
                  </span>
                  <h3 className="font-bold flex-1">{ins.insight}</h3>
                </div>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-gray-500">优化动作：</span>
                    <span className="text-gray-800">{ins.action}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-gray-500 pt-2 border-t border-gray-100">
                    <span>负责人：<span className="font-medium text-gray-700">{ins.owner}</span></span>
                    <span>截止：<span className="font-medium text-gray-700">{ins.deadline}</span></span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 bg-orange-600 text-white">
        <div className="max-w-page mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-4">想看自己的漏斗长啥样？</h2>
          <p className="text-lg opacity-90 mb-8">
            7 天试用 · 把您的客户跟进数据导入 Cloud · AI 自动跑漏斗分析
          </p>
          <div className="flex items-center justify-center gap-3">
            <Link
              to="/try"
              className="px-6 py-3 bg-white text-orange-600 rounded-md hover:bg-gray-100 font-medium inline-flex items-center gap-2"
            >
              7 天免费试用 <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/clients"
              className="px-6 py-3 border border-white/40 rounded-md hover:bg-white/10"
            >
              看 80 家清单
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
