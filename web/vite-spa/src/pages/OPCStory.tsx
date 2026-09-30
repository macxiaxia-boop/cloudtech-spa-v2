// OPC 故事页 · 心之所向便是光的今天 · 创始人后台
import { Link } from 'react-router-dom';
import { Calendar, Clock, TrendingUp, Users, DollarSign, Heart, Code, FileText, Target, Award, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

const TIMELINE = [
  { time: '08:30', task: '5 AI 员工晨会', detail: 'Hermes 报告：49 红线全绿 · 0 违规', icon: Heart, color: 'text-purple-600' },
  { time: '09:00', task: 'Apollo 跑 80 家客户漏斗', detail: 'pending 32 → contacted 6 → demo 4', icon: TrendingUp, color: 'text-green-600' },
  { time: '10:30', task: 'Lyra 出 Phase 47 内容报告', detail: '金句型 1 篇 + 实战派深度 2 篇', icon: FileText, color: 'text-pink-600' },
  { time: '12:00', task: '午饭 + 客户 1v1 demo 1 家', detail: '北京装企王总，30 分钟跑通试用', icon: Users, color: 'text-blue-600' },
  { time: '14:00', task: 'Artemis 外呼 P0 客户 8 家', detail: '接通 5 家 · 2 家约 demo · 1 家婉拒', icon: Target, color: 'text-orange-600' },
  { time: '15:30', task: 'Athena 重构 Monitoring SPA', detail: '+ 实时数据图表 + 告警面板', icon: Code, color: 'text-blue-600' },
  { time: '17:00', task: 'Hermes 守护 49 红线巡检', detail: 'P0 检查 12 项 · 100% 通过', icon: Award, color: 'text-purple-600' },
  { time: '18:30', task: '收工 · 5 AI 员工继续 7×24 跑', detail: '夜间 cron：备份 / 监控 / 复盘 / 学习', icon: Clock, color: 'text-gray-600' },
];

const TODAY_METRICS = [
  { label: '产出内容', value: '8 篇', sub: '+20% vs 上周' },
  { label: '外呼接通', value: '5/8', sub: '62.5% 接通率' },
  { label: '新增试用', value: '3 家', sub: '¥0 成本获取' },
  { label: 'M0 闸门', value: '0', sub: '用户拍板 0 次' },
];

const KEY_DECISIONS = [
  { date: '2026-09-14', title: '签了 5 份 SaaS 服务合同', type: '合同签字 · 必我拍板' },
  { date: '2026-09-12', title: '招聘 FE 工程师 P5 · 25-35K+期权', type: '招聘 offer · 必我拍板' },
  { date: '2026-09-10', title: 'P0 8 家客户外呼 · 北京 6 + 上海 2', type: '客户首单承诺 · 必我拍板' },
  { date: '2026-09-08', title: '金蝶云会计 ¥800/月 · 公司账套初始化', type: '钱进出 · 必我拍板' },
];

const PHILOSOPHY = [
  {
    icon: '🎯',
    title: 'OPC = 1 人 + AI = 整家公司',
    desc: '我是 CEO + 产品 + 销售 + 财务 + HR。AI 是我的 5 个 7×24 数字员工。我只做 4 类必拍板的决策，其余全授权 AI。',
  },
  {
    icon: '🛡️',
    title: '4 不可逆闸门守护',
    desc: '合同签字 / 钱进出 / 招聘 offer / 客户首单承诺 — 这 4 类动作必我亲自触发。AI 永远不替我做。其余 AI 全程自治。',
  },
  {
    icon: '⚙️',
    title: '8 daemon + 3 detector = 自我修复',
    desc: 'Cloud 内部有 8 个守护 daemon + 3 个探测器（drift/stall/loop）+ 9 个 cron。系统跑偏会自动修复或冻结，绝不失控。',
  },
  {
    icon: '📚',
    title: '先自用 · 再卖 · 案例化',
    desc: '我自己就是 Cloud 的第一个客户。我用 30 天跑出来的真实数据 = 你的案例。我经历的坑 = 你的避雷针。',
  },
];

export function OPCStoryPage() {
  return (
    <>
      <section className="py-16 bg-gradient-to-br from-indigo-50 via-white to-purple-50 overflow-hidden">
        <div className="max-w-page mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-10 items-center mb-10">
            <div>
              <span className="inline-block px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm mb-4">
                👤 心之所向便是光的今天 · 创始人后台
              </span>
              <div className="flex items-center gap-6 mb-6">
                <div className="w-24 h-24 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white flex items-center justify-center text-3xl font-bold">
                  心之所向便是光
                </div>
                <div>
                  <h1 className="text-4xl md:text-5xl font-bold mb-2 leading-[1.1]">
                    1 人 + 5 AI 员工
                    <br />
                    <span className="text-brand-500">的整家公司</span>
                  </h1>
                </div>
              </div>
              <p className="text-lg text-muted-foreground mb-4">
                Cloud创始人 · Cloud OPC 模式实证 · Day 30 · 208/208 测试 PASS
              </p>
              <div className="flex flex-wrap gap-3">
                <Link to="/try" className="px-5 py-2.5 bg-indigo-500 text-white rounded-md hover:bg-indigo-600 inline-flex items-center gap-2 font-medium text-sm">
                  7 天免费试用 <ArrowRight className="w-4 h-4" />
                </Link>
                <Link to="/employees" className="px-5 py-2.5 border border-gray-300 rounded-md hover:border-indigo-500 inline-flex items-center gap-2 text-sm">
                  看 5 AI 员工 →
                </Link>
              </div>
            </div>
            <div className="relative">
              <img
                src="/images/opc-hero.jpeg"
                alt="OPC 1 人 + AI 创业"
                className="rounded-2xl shadow-2xl w-full"
              />
              <div className="absolute -bottom-4 -right-4 bg-card p-3 rounded-lg shadow-lg border border-gray-200">
                <div className="text-xs">
                  <p className="font-bold text-indigo-600">Day 30</p>
                  <p className="text-gray-500">5 AI · 11 SPA · 80 客户</p>
                </div>
              </div>
            </div>
          </div>

          {/* 今日指标 */}
          <div className="grid md:grid-cols-4 gap-4">
            {TODAY_METRICS.map((m) => (
              <div key={m.label} className="p-5 bg-card rounded-lg border border-gray-200">
                <p className="text-3xl font-bold text-brand-500">{m.value}</p>
                <p className="text-sm text-foreground mt-1">{m.label}</p>
                <p className="text-xs text-gray-500 mt-1">{m.sub}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 今日时间线 */}
      <section className="py-12 bg-card">
        <div className="max-w-page mx-auto px-6">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
            <Calendar className="w-6 h-6" /> 心之所向便是光的今天 · 时间线
          </h2>
          <p className="text-gray-500 mb-8 text-sm">
            真实记录我每天 + 5 AI 员工在干啥。每条都附时间 + 任务 + 结果。8 节点 = 1 整天的 OPC 模式。
          </p>

          <div className="space-y-3">
            {TIMELINE.map((t, i) => {
              const Icon = t.icon;
              return (
                <div key={i} className="flex items-start gap-4 p-4 bg-muted rounded-lg border border-gray-200 hover:border-brand-500 transition">
                  <div className="text-center flex-shrink-0">
                    <div className={`w-10 h-10 rounded-full bg-card flex items-center justify-center ${t.color} mb-1`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <p className="text-xs text-gray-500 font-bold">{t.time}</p>
                  </div>
                  <div className="flex-1">
                    <p className="font-medium">{t.task}</p>
                    <p className="text-sm text-muted-foreground mt-1">{t.detail}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 关键决策 */}
      <section className="py-12 bg-muted">
        <div className="max-w-page mx-auto px-6">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
            <Award className="w-6 h-6 text-yellow-500" /> 红 #22 关键决策 · 必我拍板的 4 闸门
          </h2>
          <p className="text-gray-500 mb-8 text-sm">
            OPC 模式不 = AI 失控。这 4 类动作 AI 不替我做，必须我亲自触发。1 个月来拍了 4 次板。
          </p>

          <div className="grid md:grid-cols-2 gap-4">
            {KEY_DECISIONS.map((d) => (
              <div key={d.title} className="p-5 bg-card rounded-lg border border-gray-200">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm text-gray-500">{d.date}</p>
                  <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded font-medium">
                    {d.type}
                  </span>
                </div>
                <p className="font-medium">{d.title}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* OPC 哲学 */}
      <section className="py-12 bg-card">
        <div className="max-w-page mx-auto px-6">
          <h2 className="text-2xl font-bold mb-8 flex items-center gap-2">
            <Heart className="w-6 h-6 text-red-500" /> 我的 OPC 哲学
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            {PHILOSOPHY.map((p) => (
              <div key={p.title} className="p-6 bg-gradient-to-br from-gray-50 to-white rounded-lg border border-gray-200">
                <p className="text-4xl mb-3">{p.icon}</p>
                <h3 className="text-lg font-bold mb-2">{p.title}</h3>
                <p className="text-sm text-foreground">{p.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 30 天数据 */}
      <section className="py-12 bg-muted">
        <div className="max-w-page mx-auto px-6">
          <h2 className="text-2xl font-bold mb-6">📈 30 天 OPC 实证数据</h2>
          <div className="grid md:grid-cols-4 gap-4">
            <BigStat icon={Code} label="SPA 页面" value="11" sub="全可交互" color="text-blue-600" />
            <BigStat icon={FileText} label="公司文档" value="16" sub="合同/HR/财务/营销" color="text-green-600" />
            <BigStat icon={Users} label="客户清单" value="80" sub="P0/P1/P2/P3 漏斗" color="text-purple-600" />
            <BigStat icon={TrendingUp} label="测试 PASS" value="208/208" sub="100% 通过率" color="text-orange-600" />
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 bg-gradient-to-r from-indigo-500 to-purple-600 text-white">
        <div className="max-w-page mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-4">你也想跑 OPC 模式？</h2>
          <p className="text-lg opacity-90 mb-8">
            把心之所向便是光的 5 AI 员工 + 11 SPA + 80 客户清单 + 16 文档 · 全部复制给你
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link
              to="/try"
              className="px-8 py-3 bg-card text-indigo-600 rounded-md hover:bg-gray-100 inline-flex items-center gap-2 font-medium"
            >
              立即试用 <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/cases"
              className="px-8 py-3 border border-white text-white rounded-md hover:bg-white/10"
            >
              看客户案例
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}

function BigStat({ icon: Icon, label, value, sub, color }: any) {
  return (
    <div className="p-6 bg-card rounded-lg border border-gray-200 text-center">
      <Icon className={`w-8 h-8 ${color} mx-auto mb-2`} />
      <p className="text-3xl font-bold mb-1">{value}</p>
      <p className="text-sm text-foreground font-medium">{label}</p>
      <p className="text-xs text-gray-500 mt-1">{sub}</p>
    </div>
  );
}
