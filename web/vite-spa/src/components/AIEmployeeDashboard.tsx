// 5 AI 角色 · 今日实时 feed
import { Link } from 'react-router-dom';
import { Activity, Brain, Database, Code, Megaphone } from 'lucide-react';

interface AIEmployeeActivity {
  employee: 'hermes' | 'lyra' | 'athena' | 'apollo' | 'artemis';
  task: string;
  result: string;
  time: string;
  status: 'success' | 'running' | 'pending';
}

const EMPLOYEES = {
  hermes: { name: 'Hermes', role: '治理', icon: Activity, color: 'text-purple-600 bg-purple-100' },
  lyra: { name: 'Lyra', role: '内容', icon: Brain, color: 'text-pink-600 bg-pink-100' },
  athena: { name: 'Athena', role: '架构', icon: Code, color: 'text-blue-600 bg-blue-100' },
  apollo: { name: 'Apollo', role: '数据', icon: Database, color: 'text-green-600 bg-green-100' },
  artemis: { name: 'Artemis', role: '运营', icon: Megaphone, color: 'text-orange-600 bg-orange-100' },
};

// 模拟今日活动（实际可接 backend API）
const TODAY_ACTIVITIES: AIEmployeeActivity[] = [
  { employee: 'lyra', task: '生成小红书爆款文案', result: '产出 3 篇 · 选最优派 1.0', time: '2 分钟前', status: 'success' },
  { employee: 'apollo', task: '更新 80 家客户漏斗数据', result: 'pending → contacted 6 家', time: '8 分钟前', status: 'success' },
  { employee: 'athena', task: '重构 Monitoring SPA 页', result: '4 大区导航 + Onboarding', time: '15 分钟前', status: 'success' },
  { employee: 'hermes', task: '守护 49 红线巡检', result: '0 违规 · 1 警告（已修）', time: '32 分钟前', status: 'success' },
  { employee: 'artemis', task: '起草 P0 客户 8 套话术', result: '北京 6 + 上海 2 · 100% 就绪', time: '1 小时前', status: 'success' },
  { employee: 'apollo', task: '同步 PostgreSQL → Grafana', result: '7 仪表盘就绪', time: '2 小时前', status: 'success' },
  { employee: 'lyra', task: '生成 Phase 46 内容报告', result: '1.0 3500 字 · 冲 95', time: '3 小时前', status: 'success' },
  { employee: 'hermes', task: 'Cron 守护 D1-D8 心跳检查', result: '8/8 健康', time: '4 小时前', status: 'success' },
];

const STATUS_BADGE = {
  success: 'bg-green-100 text-green-700',
  running: 'bg-yellow-100 text-yellow-700 animate-pulse',
  pending: 'bg-gray-100 text-gray-700',
};

const STATUS_LABEL = {
  success: '✓ 完成',
  running: '⟳ 进行中',
  pending: '◯ 待启动',
};

export function AIEmployeeDashboard() {
  return (
    <section className="py-12 bg-gray-50">
      <div className="max-w-page mx-auto px-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold">🤖 5 AI 数字员工 · 今日干了啥</h2>
            <p className="text-sm text-gray-500 mt-1">OPC 模式：实时看你的 5 个虚拟员工在跑什么</p>
          </div>
          <Link to="/employees" className="text-sm text-brand-500 hover:underline">
            查看完整工时表 →
          </Link>
        </div>

        {/* 5 员工状态卡 */}
        <div className="grid md:grid-cols-5 gap-3 mb-6">
          {Object.entries(EMPLOYEES).map(([key, e]) => {
            const Icon = e.icon;
            const tasks = TODAY_ACTIVITIES.filter((a) => a.employee === key);
            return (
              <div key={key} className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className={`w-8 h-8 rounded-md flex items-center justify-center ${e.color}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="font-bold text-sm">{e.name}</p>
                    <p className="text-xs text-gray-500">{e.role}</p>
                  </div>
                </div>
                <p className="text-2xl font-bold text-brand-500">{tasks.length}</p>
                <p className="text-xs text-gray-500">今日任务</p>
              </div>
            );
          })}
        </div>

        {/* 实时 feed */}
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
            <p className="text-sm font-medium">实时活动流</p>
            <span className="flex items-center gap-1 text-xs text-green-600">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span> 实时
            </span>
          </div>
          <div className="divide-y divide-gray-100">
            {TODAY_ACTIVITIES.map((a, i) => {
              const e = EMPLOYEES[a.employee];
              const Icon = e.icon;
              return (
                <div key={i} className="px-4 py-3 flex items-center gap-3 hover:bg-gray-50">
                  <div className={`w-8 h-8 rounded-md flex items-center justify-center ${e.color}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm">
                      <span className="font-medium">{e.name}</span>
                      <span className="text-gray-500"> · </span>
                      <span>{a.task}</span>
                    </p>
                    <p className="text-xs text-gray-500">{a.result}</p>
                  </div>
                  <span className={`px-2 py-0.5 text-xs rounded ${STATUS_BADGE[a.status]}`}>
                    {STATUS_LABEL[a.status]}
                  </span>
                  <span className="text-xs text-gray-400 w-20 text-right">{a.time}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
