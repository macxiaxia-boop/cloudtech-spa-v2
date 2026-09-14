// 5 AI 数字员工 · 完整工时表 + 任务分配
import { Link } from 'react-router-dom';
import { Activity, Brain, Code, Database, Megaphone, Sparkles, ArrowRight, CheckCircle2 } from 'lucide-react';

interface Employee {
  id: string;
  name: string;
  role: string;
  motto: string;
  icon: any;
  color: string;
  bg: string;
  responsibilities: string[];
  skills: string[];
  todayHours: number;
  weekHours: number;
  tasksCompleted: number;
  successRate: number;
}

const EMPLOYEES: Employee[] = [
  {
    id: 'hermes',
    name: 'Hermes',
    role: '治理',
    motto: '守门人 · 红线守护 · 用户拍板',
    icon: Activity,
    color: 'text-purple-600',
    bg: 'bg-purple-100',
    responsibilities: [
      '49 红线守护（医疗/合规/隐私/财务/招聘）',
      '4 不可逆闸门（合同/钱/offer/首单）',
      'AI 行为审计 + 异常告警',
      'Phase 25 V9.0 OPC 治理边界守护',
      '红 #22 / 红 #23 / 红 #25 实时校验',
    ],
    skills: ['红线守护', '决策审计', '合规审查', '异常检测', '用户授权'],
    todayHours: 6.5,
    weekHours: 42,
    tasksCompleted: 218,
    successRate: 99.5,
  },
  {
    id: 'lyra',
    name: 'Lyra',
    role: '内容',
    motto: '小红书爆款 + 抖音脚本 + 公众号深度文',
    icon: Brain,
    color: 'text-pink-600',
    bg: 'bg-pink-100',
    responsibilities: [
      '小红书爆款文案（金句型派 2.0）',
      '实战派深度型内容（教训/方法论/场景向派 1.0）',
      '抖音短视频脚本 + 拍摄角度建议',
      '公众号深度长文（4500+ 字）',
      '内容工厂：日产 8 篇 + 选最优派 1.0',
    ],
    skills: ['金句型 2.0', '实战派深度 1.0', '短视频脚本', '内容工厂', '风格库'],
    todayHours: 5.8,
    weekHours: 38,
    tasksCompleted: 156,
    successRate: 97.4,
  },
  {
    id: 'athena',
    name: 'Athena',
    role: '架构',
    motto: 'SPA + FastAPI + PostgreSQL + 监控',
    icon: Code,
    color: 'text-blue-600',
    bg: 'bg-blue-100',
    responsibilities: [
      'Vite + React + TypeScript + Tailwind SPA',
      'FastAPI gateway_v22.py（1487 路由）',
      'PostgreSQL 数据库 schema + 迁移',
      'Grafana 仪表盘 + Prometheus 告警',
      '9,816 Python 文件架构守护',
    ],
    skills: ['React', 'FastAPI', 'PostgreSQL', 'Grafana', '监控告警'],
    todayHours: 7.2,
    weekHours: 48,
    tasksCompleted: 87,
    successRate: 98.8,
  },
  {
    id: 'apollo',
    name: 'Apollo',
    role: '数据',
    motto: '客户漏斗 + 财务核算 + 业务指标',
    icon: Database,
    color: 'text-green-600',
    bg: 'bg-green-100',
    responsibilities: [
      '80 家客户漏斗（P0/P1/P2/P3 状态机）',
      '财务核算（科目表 + 凭证 + 月度报表）',
      '业务指标 MRR/ARR/CAC/LTV',
      'A/B 实验 + 数据归因',
      '208 测试 PASS 数据守护',
    ],
    skills: ['数据建模', 'SQL', '归因分析', '财务核算', '漏斗'],
    todayHours: 5.4,
    weekHours: 35,
    tasksCompleted: 134,
    successRate: 99.1,
  },
  {
    id: 'artemis',
    name: 'Artemis',
    role: '运营',
    motto: '客户外呼 + 内容分发 + 社群激活',
    icon: Megaphone,
    color: 'text-orange-600',
    bg: 'bg-orange-100',
    responsibilities: [
      'P0 8 客户外呼（北京 6 + 上海 2）',
      '小红书/抖音/公众号多平台分发',
      '微信群激活 + 1v1 私信',
      '行业展会 + 客户活动',
      'CRM 跟进 + 转化漏斗',
    ],
    skills: ['客户外呼', '多平台分发', '社群运营', 'CRM', '转化漏斗'],
    todayHours: 4.9,
    weekHours: 32,
    tasksCompleted: 178,
    successRate: 96.2,
  },
];

export function AIEmployeesPage() {
  const totalTasks = EMPLOYEES.reduce((sum, e) => sum + e.tasksCompleted, 0);
  const totalTodayHours = EMPLOYEES.reduce((sum, e) => sum + e.todayHours, 0);
  const avgSuccessRate = EMPLOYEES.reduce((sum, e) => sum + e.successRate, 0) / EMPLOYEES.length;

  return (
    <>
      <section className="py-16 bg-gradient-to-br from-purple-50 via-white to-pink-50">
        <div className="max-w-page mx-auto px-6">
          <span className="inline-block px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm mb-4">
            🤖 5 AI 数字员工 · 完整工时表
          </span>
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            1 人 + 5 AI 员工 = <span className="text-brand-500">1 整家公司</span>
          </h1>
          <p className="text-lg text-gray-600 mb-8 max-w-2xl">
            CloudTech 自己的 5 个 AI 员工是怎么分工的。每人 1 个核心职责 + 7×24 在线 + 0 工资成本。
          </p>

          {/* 总览指标 */}
          <div className="grid md:grid-cols-4 gap-4">
            <StatCard label="今日总工时" value={`${totalTodayHours.toFixed(1)} h`} />
            <StatCard label="本周总工时" value={`${EMPLOYEES.reduce((s, e) => s + e.weekHours, 0)} h`} />
            <StatCard label="累计完成任务" value={totalTasks} />
            <StatCard label="平均成功率" value={`${avgSuccessRate.toFixed(1)}%`} />
          </div>
        </div>
      </section>

      {/* 5 员工详情 */}
      <section className="py-12 bg-white">
        <div className="max-w-page mx-auto px-6 space-y-8">
          {EMPLOYEES.map((e) => (
            <EmployeeCard key={e.id} e={e} />
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 bg-gradient-to-r from-brand-500 to-brand-600 text-white">
        <div className="max-w-page mx-auto px-6 text-center">
          <Sparkles className="w-12 h-12 mx-auto mb-4" />
          <h2 className="text-3xl font-bold mb-4">想自己拥有这 5 个 AI 员工？</h2>
          <p className="text-lg opacity-90 mb-8">
            7 天免费试用 · 5 AI 员工全功能 · 不需要信用卡
          </p>
          <Link
            to="/try"
            className="px-8 py-3 bg-white text-brand-500 rounded-md hover:bg-gray-100 inline-flex items-center gap-2 font-medium"
          >
            立即试用 <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="p-5 bg-white rounded-lg border border-gray-200">
      <p className="text-3xl font-bold text-brand-500">{value}</p>
      <p className="text-sm text-gray-500 mt-1">{label}</p>
    </div>
  );
}

function EmployeeCard({ e }: { e: Employee }) {
  const Icon = e.icon;
  return (
    <div className="bg-white border-2 border-gray-200 rounded-xl overflow-hidden hover:border-brand-500 transition">
      <div className={`p-6 ${e.bg}`}>
        <div className="flex items-center gap-4">
          <div className={`w-16 h-16 rounded-xl bg-white flex items-center justify-center ${e.color}`}>
            <Icon className="w-8 h-8" />
          </div>
          <div>
            <h3 className="text-2xl font-bold">{e.name}</h3>
            <p className="text-sm text-gray-600 mb-1">{e.role}</p>
            <p className="text-sm italic text-gray-700">"{e.motto}"</p>
          </div>
        </div>
      </div>

      <div className="p-6 grid md:grid-cols-3 gap-6">
        {/* 工时统计 */}
        <div>
          <p className="text-xs uppercase font-bold text-gray-500 mb-3">📊 工时统计</p>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>今日</span>
              <span className="font-bold">{e.todayHours} h</span>
            </div>
            <div className="flex justify-between text-sm">
              <span>本周</span>
              <span className="font-bold">{e.weekHours} h</span>
            </div>
            <div className="flex justify-between text-sm">
              <span>累计任务</span>
              <span className="font-bold">{e.tasksCompleted}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span>成功率</span>
              <span className="font-bold text-green-600">{e.successRate}%</span>
            </div>
          </div>
        </div>

        {/* 核心职责 */}
        <div>
          <p className="text-xs uppercase font-bold text-gray-500 mb-3">📋 核心职责</p>
          <ul className="space-y-1.5">
            {e.responsibilities.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <CheckCircle2 className={`w-4 h-4 ${e.color} flex-shrink-0 mt-0.5`} />
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* 技能栈 */}
        <div>
          <p className="text-xs uppercase font-bold text-gray-500 mb-3">🛠️ 技能栈</p>
          <div className="flex flex-wrap gap-2">
            {e.skills.map((s) => (
              <span key={s} className={`px-3 py-1 ${e.bg} ${e.color} rounded-full text-xs font-medium`}>
                {s}
              </span>
            ))}
          </div>
          <Link
            to="/dashboard"
            className={`inline-flex items-center gap-1 mt-4 text-sm ${e.color} hover:underline`}
          >
            看 {e.name} 实时活动 →
          </Link>
        </div>
      </div>
    </div>
  );
}
