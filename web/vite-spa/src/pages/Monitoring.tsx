// Phase 46 D61-68 — 监控 + 财务 + 客户漏斗仪表盘 SPA 页
import { Link } from 'react-router-dom';
import { Activity, ArrowRight, AlertCircle, DollarSign, Users, Database, Server } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface DashboardPanel {
  name: string;
  type: string;
  desc: string;
  refresh: string;
  panels: number;
}

const TECH_DASHBOARDS: DashboardPanel[] = [
  { name: 'API P95 延迟', type: 'timeseries', desc: '各路由 P95 响应时间·阈值 500ms', refresh: '30s', panels: 1 },
  { name: '错误率', type: 'timeseries', desc: '5xx 错误率·阈值 1%', refresh: '30s', panels: 1 },
  { name: '数据库慢查询', type: 'timeseries', desc: 'SQL P95·阈值 100ms', refresh: '30s', panels: 1 },
  { name: 'LLM API 成功率', type: 'stat', desc: 'AI 模型调用成功率·阈值 99%', refresh: '30s', panels: 1 },
  { name: '最近错误日志', type: 'logs', desc: 'Loki 错误日志流', refresh: '实时', panels: 1 },
];

const BUSINESS_DASHBOARDS: DashboardPanel[] = [
  { name: 'MRR (月度经常性收入)', type: 'stat', desc: '付费客户合计·目标 ¥21,865', refresh: '5m', panels: 1 },
  { name: '付费客户数', type: 'stat', desc: '非免费版客户总数·目标 25', refresh: '5m', panels: 1 },
  { name: '月流失率', type: 'stat', desc: '30 天流失比例·阈值 5%', refresh: '5m', panels: 1 },
  { name: 'NRR (净收入留存)', type: 'stat', desc: '净收入留存率·目标 110%', refresh: '5m', panels: 1 },
  { name: 'MRR 趋势 (30 天)', type: 'timeseries', desc: '日 MRR 折线图', refresh: '5m', panels: 1 },
  { name: '80 家触达漏斗', type: 'barchart', desc: '5 状态机分布', refresh: '5m', panels: 1 },
  { name: '5 行业复盘概览', type: 'table', desc: 'Phase 45 D4-7 行业决策', refresh: '5m', panels: 1 },
];

const ALERT_LEVELS = [
  { level: 'P0', label: '紧急 (5 分钟内响应)', count: 5, color: 'bg-red-100 text-red-700 border-red-300' },
  { level: 'P1', label: '重要 (1 小时内响应)', count: 3, color: 'bg-orange-100 text-orange-700 border-orange-300' },
  { level: 'P2', label: '警告 (4 小时内响应)', count: 3, color: 'bg-yellow-100 text-yellow-700 border-yellow-300' },
  { level: 'P3', label: '提醒 (24 小时内响应)', count: 2, color: 'bg-blue-100 text-blue-700 border-blue-300' },
];

const SAAS_STACK = [
  { category: '财务', name: '金蝶云会计', cost: '¥800/月', rationale: '金税对接最稳 + 中小 SaaS 首选' },
  { category: 'HR', name: '飞书人事', cost: '¥2,400/月 (8 人)', rationale: '与已有飞书生态无缝集成' },
  { category: '监控', name: 'Grafana Cloud', cost: '¥500/月起', rationale: '免费起步 + SaaS 化运维' },
  { category: '短信', name: '阿里云通信', cost: '¥0.045/条', rationale: '金融级稳定性 + 国内为主' },
  { category: 'ICP 备案', name: 'e窗通 + 阿里云代理', cost: '¥0', rationale: '自办 + 阿里云免费代理' },
];

const FUNNEL_STAGES = [
  { key: 'pending', label: '待触达', count: 80, color: 'bg-gray-100 text-gray-700' },
  { key: 'contacted', label: '已联系', count: 24, color: 'bg-blue-100 text-blue-700' },
  { key: 'demo_scheduled', label: '已约演示', count: 10, color: 'bg-purple-100 text-purple-700' },
  { key: 'trial', label: '试用中', count: 4, color: 'bg-orange-100 text-orange-700' },
  { key: 'signed', label: '已签约', count: 2, color: 'bg-green-100 text-green-700' },
];

export function MonitoringPage() {
  const totalDashboards = TECH_DASHBOARDS.length + BUSINESS_DASHBOARDS.length;
  const totalAlerts = ALERT_LEVELS.reduce((s, a) => s + a.count, 0);
  const totalSaasCost = 800 + 2400 + 500;

  return (
    <>
      {/* HERO */}
      <section className="relative py-16 bg-gradient-to-br from-cyan-50 via-white to-blue-50">
        <div className="max-w-page mx-auto px-6">
          <div className="max-w-3xl">
            <span className="inline-flex items-center gap-2 px-3 py-1 bg-cyan-100 text-cyan-700 rounded-full text-sm mb-4">
              <Activity className="w-3 h-3" /> Phase 46 D61-68 · OPC 监控 + 财务 + 漏斗中心
            </span>
            <h1 className="text-4xl md:text-5xl font-bold mb-4 leading-[1.1]">
              监控与财务中心
              <br />
              <span className="text-cyan-500">实时可见 · 自动告警 · 红线守护</span>
            </h1>
            <p className="text-lg text-gray-600 mb-8">
              2 Grafana 仪表盘 + 13 监控告警规则 + 5 SaaS 选型 + 80 家漏斗追踪。
              红 #22 边界：内部监控 AI 已就绪，外部开通 + 付费必用户拍板。
            </p>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
              <Card className="p-0">
                <CardContent className="p-4">
                  <p className="text-xs text-muted-foreground">仪表盘</p>
                  <p className="text-3xl font-bold text-cyan-600">{totalDashboards}</p>
                  <p className="text-xs text-muted-foreground mt-1">Grafana</p>
                </CardContent>
              </Card>
              <Card className="p-0">
                <CardContent className="p-4">
                  <p className="text-xs text-muted-foreground">告警规则</p>
                  <p className="text-3xl font-bold text-red-600">{totalAlerts}</p>
                  <p className="text-xs text-muted-foreground mt-1">P0-P3 四级</p>
                </CardContent>
              </Card>
              <Card className="p-0">
                <CardContent className="p-4">
                  <p className="text-xs text-muted-foreground">SaaS 月成本</p>
                  <p className="text-3xl font-bold text-green-600">¥{totalSaasCost.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground mt-1">不含 ICP</p>
                </CardContent>
              </Card>
              <Card className="p-0">
                <CardContent className="p-4">
                  <p className="text-xs text-muted-foreground">客户漏斗</p>
                  <p className="text-3xl font-bold text-emerald-600">80</p>
                  <p className="text-xs text-muted-foreground mt-1">5 状态</p>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* 红 #22 守门 */}
      <section className="py-6 bg-red-50 border-y border-red-200">
        <div className="max-w-page mx-auto px-6">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm">
              <p className="font-medium text-red-800">红线 #22 监控边界</p>
              <p className="text-red-700 mt-1">
                内部监控配置（仪表盘 JSON / 告警规则 / SaaS 选型调研）= AI 已就绪。
                外部动作（开通账号 / 付费 / 接收群 / 阈值调优 / 客户跟进）= 必用户拍板。
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 仪表盘 */}
      <section className="py-12 bg-card border-b border-gray-100">
        <div className="max-w-page mx-auto px-6">
          <div className="flex items-center gap-3 mb-6">
            <Server className="w-6 h-6 text-cyan-600" />
            <h2 className="text-2xl font-bold">技术健康仪表盘</h2>
            <span className="text-sm text-gray-500">({TECH_DASHBOARDS.length} 面板)</span>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {TECH_DASHBOARDS.map((d) => (
              <div key={d.name} className="p-4 bg-cyan-50 rounded-lg border border-cyan-200">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-bold">{d.name}</h3>
                  <span className="text-xs px-2 py-0.5 bg-card text-cyan-700 rounded font-mono">
                    {d.type}
                  </span>
                </div>
                <p className="text-sm text-foreground">{d.desc}</p>
                <p className="text-xs text-gray-500 mt-2">刷新: {d.refresh}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-12 bg-gray-50 border-b border-gray-100">
        <div className="max-w-page mx-auto px-6">
          <div className="flex items-center gap-3 mb-6">
            <DollarSign className="w-6 h-6 text-green-600" />
            <h2 className="text-2xl font-bold">业务北极星仪表盘</h2>
            <span className="text-sm text-gray-500">({BUSINESS_DASHBOARDS.length} 面板)</span>
          </div>
          <div className="grid md:grid-cols-3 gap-4">
            {BUSINESS_DASHBOARDS.map((d) => (
              <div key={d.name} className="p-4 bg-green-50 rounded-lg border border-green-200">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-bold text-sm">{d.name}</h3>
                  <span className="text-xs px-2 py-0.5 bg-card text-green-700 rounded font-mono">
                    {d.type}
                  </span>
                </div>
                <p className="text-xs text-foreground">{d.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 告警分级 */}
      <section className="py-12 bg-card border-b border-gray-100">
        <div className="max-w-page mx-auto px-6">
          <h2 className="text-2xl font-bold mb-4">告警分级 (P0-P3)</h2>
          <p className="text-gray-600 mb-6">共 {totalAlerts} 条规则 + 4 飞书机器人通道</p>
          <div className="grid md:grid-cols-4 gap-4">
            {ALERT_LEVELS.map((a) => (
              <div key={a.level} className={`p-4 rounded-lg border-2 ${a.color}`}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-2xl font-bold">{a.level}</span>
                  <span className="text-3xl font-bold">{a.count}</span>
                </div>
                <p className="text-xs">{a.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SaaS 选型 */}
      <section className="py-12 bg-gray-50 border-b border-gray-100">
        <div className="max-w-page mx-auto px-6">
          <h2 className="text-2xl font-bold mb-4">5 SaaS 选型 (X01/F01)</h2>
          <p className="text-gray-600 mb-6">月成本 ¥{totalSaasCost.toLocaleString()} · 待用户拍板付费</p>
          <div className="overflow-x-auto bg-card rounded-lg border border-gray-200">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">类别</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">SaaS</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">成本</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">推荐理由</th>
                </tr>
              </thead>
              <tbody>
                {SAAS_STACK.map((s) => (
                  <tr key={s.category} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{s.category}</td>
                    <td className="px-4 py-3 font-medium">{s.name}</td>
                    <td className="px-4 py-3 text-gray-600">{s.cost}</td>
                    <td className="px-4 py-3 text-gray-600 text-xs">{s.rationale}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* 80 家漏斗 */}
      <section className="py-12 bg-card">
        <div className="max-w-page mx-auto px-6">
          <h2 className="text-2xl font-bold mb-4">80 家客户触达漏斗</h2>
          <p className="text-gray-600 mb-6">M1 预期分布：50% 待触达 / 30% 已联系 / 12% 演示 / 5% 试用 / 3% 签约</p>
          <div className="grid md:grid-cols-5 gap-4">
            {FUNNEL_STAGES.map((s) => (
              <div key={s.key} className={`p-4 rounded-lg border ${s.color}`}>
                <p className="text-xs mb-1">{s.label}</p>
                <p className="text-3xl font-bold">{s.count}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 bg-cyan-600 text-white">
        <div className="max-w-page mx-auto px-6 text-center">
          <Database className="w-12 h-12 mx-auto mb-4" />
          <h2 className="text-3xl font-bold mb-4">监控全套就绪 · 待你拍板付费开通</h2>
          <p className="text-lg opacity-90 mb-8">Phase 46 段 4 收官 · 内部配置 AI 全程自治</p>
          <Link
            to="/documents"
            className="px-8 py-3 bg-card text-cyan-600 rounded-md hover:bg-gray-100 inline-flex items-center gap-2 font-medium"
          >
            查看文档中心 <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </>
  );
}
