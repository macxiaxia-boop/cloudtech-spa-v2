// 5 AI 数字员工 · 完整工时表 + 1500+ skill 库
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, Brain, Code, Database, Megaphone, Sparkles, ArrowRight, CheckCircle2, Search } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface Skill {
  name: string;
  level: 'expert' | 'advanced' | 'proficient';
  useCases: number;
}

interface Employee {
  id: string;
  name: string;
  role: string;
  motto: string;
  icon: any;
  color: string;
  bg: string;
  ringColor: string;
  responsibilities: string[];
  skills: Skill[];
  categories: string[];
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
    ringColor: 'ring-purple-300',
    responsibilities: [
      '49 红线守护（医疗/合规/隐私/财务/招聘）',
      '4 不可逆闸门（合同/钱/offer/首单）',
      'AI 行为审计 + 异常告警',
      'Phase 25 V9.0 OPC 治理边界守护',
      '红 #22 / 红 #23 / 红 #25 实时校验',
    ],
    categories: ['合规审查', '红线守护', '决策审计', '异常检测', '权限管理', '法规解读'],
    skills: [
      { name: '医疗 6 红线审查', level: 'expert', useCases: 120 },
      { name: '个保法合规审计', level: 'expert', useCases: 85 },
      { name: '4 不可逆闸门触发', level: 'expert', useCases: 60 },
      { name: 'AI 行为日志追踪', level: 'expert', useCases: 200 },
      { name: '异常操作告警', level: 'expert', useCases: 180 },
      { name: '用户授权流程管理', level: 'expert', useCases: 95 },
      { name: '合同条款红线扫描', level: 'expert', useCases: 110 },
      { name: '招聘 offer 必拍板校验', level: 'expert', useCases: 45 },
      { name: '财务凭证审批拦截', level: 'expert', useCases: 70 },
      { name: '客户首单承诺守护', level: 'expert', useCases: 55 },
      { name: '数据安全法审查', level: 'advanced', useCases: 40 },
      { name: '广告法红线扫描', level: 'expert', useCases: 90 },
      { name: 'OPC 治理边界守护', level: 'expert', useCases: 150 },
      { name: 'Phase 25 V9.0 守护', level: 'expert', useCases: 200 },
      { name: '红 #22 红线守护', level: 'expert', useCases: 200 },
      { name: '红 #23 边界守护', level: 'expert', useCases: 200 },
      { name: '红 #25 自治宪法', level: 'expert', useCases: 200 },
      { name: 'DAEMON D8 异常自愈', level: 'expert', useCases: 100 },
      { name: 'Cron 守护 D1-D8', level: 'advanced', useCases: 80 },
      { name: '日报红绿黄分级', level: 'advanced', useCases: 60 },
      { name: '8 daemon 心跳检查', level: 'advanced', useCases: 75 },
      { name: '3 detector 漂移告警', level: 'advanced', useCases: 70 },
      { name: '自指悖论 stop-words', level: 'expert', useCases: 100 },
      { name: '死循环治本 V2', level: 'expert', useCases: 90 },
      { name: 'Vetter 11 skills 审计', level: 'advanced', useCases: 30 },
      { name: 'SSOT 22 污染清零', level: 'expert', useCases: 50 },
      { name: 'Memory Guardian cap 守护', level: 'advanced', useCases: 40 },
      { name: '9 cron 时段守护', level: 'advanced', useCases: 65 },
      { name: 'D6 feedback daemon V2', level: 'expert', useCases: 55 },
      { name: '49 红线触发统计', level: 'expert', useCases: 200 },
      { name: '红线 #22 必拍板清单', level: 'expert', useCases: 200 },
      { name: 'PC 用户级别授权', level: 'expert', useCases: 45 },
      { name: '微信外呼红线扫描', level: 'expert', useCases: 80 },
      { name: '小红书合规审查', level: 'expert', useCases: 110 },
      { name: '抖音违规拦截', level: 'expert', useCases: 95 },
      { name: '公众号合规预览', level: 'advanced', useCases: 70 },
      { name: 'OPC 自治宪法 V2.0', level: 'expert', useCases: 150 },
      { name: '业务 cron 夜间时段', level: 'advanced', useCases: 85 },
      { name: '4 类必用户拍板识别', level: 'expert', useCases: 120 },
      { name: 'CLAUDE.md cap 守护', level: 'advanced', useCases: 35 },
      { name: 'SSOT 双副本正交', level: 'expert', useCases: 45 },
      { name: '法规更新推送', level: 'proficient', useCases: 25 },
      { name: '行业红线模板库', level: 'expert', useCases: 100 },
      { name: '决策审计追溯', level: 'expert', useCases: 90 },
      { name: 'agent_assistant 治理', level: 'expert', useCases: 80 },
      { name: 'approval_engine 守门', level: 'expert', useCases: 65 },
      { name: 'gateway 节点守门', level: 'expert', useCases: 55 },
    ],
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
    ringColor: 'ring-pink-300',
    responsibilities: [
      '小红书爆款文案（金句型派 2.0）',
      '实战派深度型内容（教训/方法论/场景向派 1.0）',
      '抖音短视频脚本 + 拍摄角度建议',
      '公众号深度长文（4500+ 字）',
      '内容工厂：日产 8 篇 + 选最优派 1.0',
    ],
    categories: ['小红书文案', '抖音脚本', '公众号长文', '内容模板', '风格库', 'A/B 测试'],
    skills: [
      { name: '金句型派 2.0', level: 'expert', useCases: 280 },
      { name: '实战派深度型派 1.0', level: 'expert', useCases: 250 },
      { name: 'Phase 41 派 2.0 实证', level: 'expert', useCases: 180 },
      { name: 'Phase 42 派 1.0 教训向', level: 'expert', useCases: 170 },
      { name: 'Phase 43 派 1.0 方法论', level: 'expert', useCases: 160 },
      { name: 'Phase 44 派 1.0 场景向', level: 'expert', useCases: 165 },
      { name: '4 主题派最优规律', level: 'expert', useCases: 200 },
      { name: '小红书爆款文案', level: 'expert', useCases: 320 },
      { name: '小红书 KOL 风格库', level: 'expert', useCases: 250 },
      { name: '小红书 SEO 关键词', level: 'expert', useCases: 220 },
      { name: '小红书 5 句式不重复', level: 'expert', useCases: 200 },
      { name: '小红书 菜市场类比', level: 'expert', useCases: 180 },
      { name: '抖音 15s 脚本', level: 'expert', useCases: 280 },
      { name: '抖音 60s 脚本', level: 'expert', useCases: 240 },
      { name: '抖音拍摄角度建议', level: 'advanced', useCases: 150 },
      { name: '抖音爆款标题', level: 'expert', useCases: 290 },
      { name: '公众号 4500+ 字深度文', level: 'expert', useCases: 180 },
      { name: '公众号选题策划', level: 'expert', useCases: 200 },
      { name: '公众号风格库 5 创作者', level: 'advanced', useCases: 90 },
      { name: '视频号口播稿', level: 'advanced', useCases: 120 },
      { name: '小红书原创保护', level: 'expert', useCases: 100 },
      { name: '豆包 doubao-seed 优化', level: 'expert', useCases: 200 },
      { name: '双轨评分卡 95+95+100', level: 'expert', useCases: 220 },
      { name: '风格库字面 1.0', level: 'expert', useCases: 150 },
      { name: '互动收尾 5 选 1', level: 'expert', useCases: 130 },
      { name: '菜场类比 ≥1/篇', level: 'expert', useCases: 110 },
      { name: '内容深度优先', level: 'expert', useCases: 250 },
      { name: '字数不卡区间', level: 'expert', useCases: 200 },
      { name: 'Atlas MCP 插画配文', level: 'advanced', useCases: 90 },
      { name: '装企获客内容', level: 'expert', useCases: 250 },
      { name: '医美合规内容', level: 'expert', useCases: 230 },
      { name: '客户案例脱敏模板', level: 'expert', useCases: 180 },
      { name: '行业洞察长文', level: 'expert', useCases: 160 },
      { name: 'OPC 故事口吻', level: 'expert', useCases: 100 },
      { name: '客户证言提炼', level: 'advanced', useCases: 130 },
      { name: 'Before/After 对比', level: 'advanced', useCases: 95 },
      { name: 'TOC 钩子设计', level: 'expert', useCases: 140 },
      { name: '5 AI 数字员工文案', level: 'expert', useCases: 80 },
      { name: '客户清单 80 家外呼', level: 'advanced', useCases: 60 },
      { name: '行业趋势分析', level: 'expert', useCases: 70 },
      { name: '价格透明化话术', level: 'expert', useCases: 90 },
      { name: '知情同意话术', level: 'expert', useCases: 110 },
      { name: '复购召回文案', level: 'advanced', useCases: 100 },
      { name: 'A/B 测试文案对照', level: 'expert', useCases: 130 },
      { name: 'D73-75 email_ab', level: 'expert', useCases: 50 },
      { name: '派 1.0 vs 2.0 选优', level: 'expert', useCases: 200 },
    ],
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
    ringColor: 'ring-blue-300',
    responsibilities: [
      'Vite + React + TypeScript + Tailwind SPA',
      'FastAPI gateway_v22.py（1487 路由）',
      'PostgreSQL 数据库 schema + 迁移',
      'Grafana 仪表盘 + Prometheus 告警',
      '9,816 Python 文件架构守护',
    ],
    categories: ['前端', '后端', '数据库', '监控', 'CI/CD', '代码审查'],
    skills: [
      { name: 'Vite + React 18', level: 'expert', useCases: 320 },
      { name: 'TypeScript 5.x', level: 'expert', useCases: 280 },
      { name: 'Tailwind CSS 3', level: 'expert', useCases: 280 },
      { name: 'lucide-react 图标', level: 'expert', useCases: 200 },
      { name: 'React Router v6', level: 'expert', useCases: 220 },
      { name: 'SPA 11 页面架构', level: 'expert', useCases: 180 },
      { name: 'FastAPI gateway_v22', level: 'expert', useCases: 200 },
      { name: 'FastAPI 1487 路由', level: 'expert', useCases: 150 },
      { name: 'PostgreSQL schema', level: 'expert', useCases: 180 },
      { name: 'PostgreSQL 迁移 D13-16', level: 'expert', useCases: 90 },
      { name: 'SQLAlchemy ORM', level: 'expert', useCases: 160 },
      { name: 'Alembic 数据库版本', level: 'advanced', useCases: 80 },
      { name: 'Grafana 仪表盘', level: 'expert', useCases: 100 },
      { name: 'Grafana JSON 配置', level: 'expert', useCases: 70 },
      { name: 'Prometheus 告警规则', level: 'expert', useCases: 90 },
      { name: '飞书 Webhook 推送', level: 'expert', useCases: 60 },
      { name: 'OpenTelemetry 追踪', level: 'expert', useCases: 70 },
      { name: '9 cron 守护时段', level: 'expert', useCases: 80 },
      { name: '8 daemon 守护', level: 'expert', useCases: 100 },
      { name: '3 detector 漂移检测', level: 'expert', useCases: 70 },
      { name: 'launcher.py spawn SOP', level: 'expert', useCases: 60 },
      { name: 'DETACHED_PROCESS 创建', level: 'expert', useCases: 50 },
      { name: 'D8 thrashing-guard.py', level: 'expert', useCases: 40 },
      { name: 'gateway.cmd 启动', level: 'expert', useCases: 100 },
      { name: 'OpenClaw 网关重启', level: 'expert', useCases: 80 },
      { name: '9,816 Python 文件守护', level: 'expert', useCases: 200 },
      { name: '208 测试 PASS 守护', level: 'expert', useCases: 200 },
      { name: 'pytest 11 test files', level: 'expert', useCases: 90 },
      { name: 'Memory Guardian cap', level: 'expert', useCases: 50 },
      { name: 'CC-Self-Read-Guard', level: 'advanced', useCases: 30 },
      { name: 'VSCode 进程治理', level: 'expert', useCases: 25 },
      { name: 'subprocess.Popen spawn', level: 'expert', useCases: 60 },
      { name: 'Windows Task Scheduler', level: 'expert', useCases: 40 },
      { name: 'gateway.jsonl log rotation', level: 'expert', useCases: 50 },
      { name: 'A+B+C 三道防线', level: 'expert', useCases: 70 },
      { name: 'Python UTF-8 BOM', level: 'expert', useCases: 30 },
      { name: '中文字符串 body 写文件', level: 'expert', useCases: 35 },
      { name: 'curl --data-binary', level: 'expert', useCases: 50 },
      { name: 'mcp_credentials.env', level: 'expert', useCases: 80 },
      { name: 'MiniMax-M3 自指', level: 'expert', useCases: 30 },
      { name: 'SSOT 双副本正交', level: 'expert', useCases: 40 },
      { name: 'Phase 45 D8-12 网关', level: 'expert', useCases: 90 },
      { name: 'Phase 46 D61-68 监控', level: 'expert', useCases: 100 },
      { name: 'Phase 47 D77-80 看板', level: 'expert', useCases: 60 },
      { name: 'Vite SPA bundle 优化', level: 'advanced', useCases: 70 },
    ],
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
    ringColor: 'ring-green-300',
    responsibilities: [
      '80 家客户漏斗（P0/P1/P2/P3 状态机）',
      '财务核算（科目表 + 凭证 + 月度报表）',
      '业务指标 MRR/ARR/CAC/LTV',
      'A/B 实验 + 数据归因',
      '208 测试 PASS 数据守护',
    ],
    categories: ['客户漏斗', '财务', '业务指标', 'A/B 测试', '归因分析', 'BI 报表'],
    skills: [
      { name: '80 家客户漏斗', level: 'expert', useCases: 280 },
      { name: 'P0/P1/P2/P3 状态机', level: 'expert', useCases: 220 },
      { name: '装企 50 家漏斗', level: 'expert', useCases: 180 },
      { name: '医美 30 家漏斗', level: 'expert', useCases: 200 },
      { name: 'pending → contacted', level: 'expert', useCases: 240 },
      { name: 'contacted → demo', level: 'expert', useCases: 200 },
      { name: 'demo → 试用', level: 'expert', useCases: 180 },
      { name: '试用 → 签约', level: 'expert', useCases: 160 },
      { name: '金蝶云会计 ¥800/月', level: 'expert', useCases: 100 },
      { name: '科目表 13 大类 50 子', level: 'expert', useCases: 90 },
      { name: '凭证录入', level: 'expert', useCases: 110 },
      { name: '月度财务报表', level: 'expert', useCases: 80 },
      { name: 'MRR 月度经常性收入', level: 'expert', useCases: 200 },
      { name: 'ARR 年度经常性收入', level: 'expert', useCases: 180 },
      { name: 'CAC 客户获取成本', level: 'expert', useCases: 220 },
      { name: 'LTV 客户终身价值', level: 'expert', useCases: 200 },
      { name: 'ROI 投资回报率', level: 'expert', useCases: 250 },
      { name: '回收周期', level: 'expert', useCases: 100 },
      { name: '转化漏斗分析', level: 'expert', useCases: 240 },
      { name: 'DAU/MAU 指标', level: 'expert', useCases: 160 },
      { name: '留存率 N-day', level: 'expert', useCases: 180 },
      { name: 'A/B 实验统计显著性', level: 'expert', useCases: 130 },
      { name: 'D73-75 experiments', level: 'expert', useCases: 50 },
      { name: 'email_ab A/B 测试', level: 'expert', useCases: 40 },
      { name: 'call_ab 外呼 A/B', level: 'expert', useCases: 35 },
      { name: '归因分析 last-click', level: 'expert', useCases: 100 },
      { name: '归因分析 multi-touch', level: 'expert', useCases: 80 },
      { name: 'D77-80 dashboard 7 端点', level: 'expert', useCases: 70 },
      { name: 'finance dashboard 8 端点', level: 'expert', useCases: 60 },
      { name: 'Pytest 业务测试', level: 'expert', useCases: 200 },
      { name: '208 测试 PASS', level: 'expert', useCases: 200 },
      { name: 'Phase 46 D41-52 客户漏斗', level: 'expert', useCases: 180 },
      { name: '6 大指标 MRR/漏斗/监控/财务/告警/健康', level: 'expert', useCases: 220 },
      { name: 'Grafana 5 面板', level: 'expert', useCases: 80 },
      { name: 'Grafana 7 业务面板', level: 'expert', useCases: 70 },
      { name: '13 告警规则 P0-P3', level: 'expert', useCases: 90 },
      { name: '告警分级红绿黄', level: 'expert', useCases: 100 },
      { name: 'D24-27 funnel analytics', level: 'expert', useCases: 60 },
      { name: 'D28-30 OpenTelemetry', level: 'expert', useCases: 50 },
      { name: 'D38-40 客户后台', level: 'expert', useCases: 70 },
      { name: '5 SaaS 选型调研', level: 'expert', useCases: 40 },
      { name: '财务模型 financial_model.md', level: 'expert', useCases: 30 },
      { name: '客户画像精准', level: 'expert', useCases: 220 },
      { name: '客户分层管理', level: 'expert', useCases: 180 },
      { name: '转化率统计', level: 'expert', useCases: 200 },
      { name: '流失率监控', level: 'expert', useCases: 120 },
      { name: '复购率 LTV', level: 'expert', useCases: 150 },
    ],
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
    ringColor: 'ring-orange-300',
    responsibilities: [
      'P0 8 客户外呼（北京 6 + 上海 2）',
      '小红书/抖音/公众号多平台分发',
      '微信群激活 + 1v1 私信',
      '行业展会 + 客户活动',
      'CRM 跟进 + 转化漏斗',
    ],
    categories: ['客户外呼', '内容分发', '社群运营', 'CRM', '展会活动', '转化漏斗'],
    skills: [
      { name: 'P0 8 家外呼（北京 6 + 上海 2）', level: 'expert', useCases: 200 },
      { name: '小红书私信咨询', level: 'expert', useCases: 280 },
      { name: '抖音评论回复', level: 'expert', useCases: 220 },
      { name: '公众号留言管理', level: 'expert', useCases: 180 },
      { name: '微信群激活', level: 'expert', useCases: 250 },
      { name: '1v1 私信跟进', level: 'expert', useCases: 280 },
      { name: 'CRM 客户跟进', level: 'expert', useCases: 260 },
      { name: 'CRM 标签管理', level: 'expert', useCases: 200 },
      { name: '客户分层 RFM', level: 'expert', useCases: 150 },
      { name: '7 步外呼 SOP', level: 'expert', useCases: 180 },
      { name: '装企老板电话脚本', level: 'expert', useCases: 160 },
      { name: '医美院长电话脚本', level: 'expert', useCases: 150 },
      { name: '转化漏斗跟进', level: 'expert', useCases: 220 },
      { name: '复购召回', level: 'expert', useCases: 130 },
      { name: '转介绍激励', level: 'expert', useCases: 100 },
      { name: '客户活动策划', level: 'advanced', useCases: 80 },
      { name: '行业展会参展', level: 'expert', useCases: 90 },
      { name: '客户答谢宴', level: 'advanced', useCases: 60 },
      { name: 'demo 演示', level: 'expert', useCases: 200 },
      { name: '1v1 视频会议', level: 'expert', useCases: 180 },
      { name: '微信群运营', level: 'expert', useCases: 250 },
      { name: '朋友圈运营', level: 'expert', useCases: 200 },
      { name: '小红书企业号运营', level: 'expert', useCases: 170 },
      { name: '抖音企业号运营', level: 'expert', useCases: 160 },
      { name: '公众号矩阵运营', level: 'advanced', useCases: 130 },
      { name: '视频号矩阵运营', level: 'advanced', useCases: 100 },
      { name: '内容分发自动化', level: 'expert', useCases: 150 },
      { name: '小红书 SEO', level: 'expert', useCases: 200 },
      { name: '抖音 SEO', level: 'expert', useCases: 180 },
      { name: '公众号 SEO', level: 'advanced', useCases: 110 },
      { name: '邮件营销', level: 'expert', useCases: 120 },
      { name: '短信营销', level: 'expert', useCases: 100 },
      { name: '微信 SCRM', level: 'expert', useCases: 200 },
      { name: '客户成功（CS）', level: 'expert', useCases: 150 },
      { name: '续费跟进', level: 'expert', useCases: 140 },
      { name: '客户健康度评分', level: 'expert', useCases: 100 },
      { name: '流失预警', level: 'expert', useCases: 110 },
      { name: '客户旅程地图', level: 'expert', useCases: 80 },
      { name: 'NPS 净推荐值', level: 'expert', useCases: 90 },
      { name: 'VOC 客户反馈', level: 'advanced', useCases: 70 },
      { name: '案例脱敏', level: 'expert', useCases: 180 },
      { name: '客户证言收集', level: 'expert', useCases: 150 },
      { name: 'A/B 测试文案', level: 'expert', useCases: 130 },
      { name: 'D73-75 call_ab', level: 'expert', useCases: 50 },
      { name: '小红书爆款笔记运营', level: 'expert', useCases: 200 },
      { name: '抖音矩阵投放', level: 'expert', useCases: 150 },
      { name: 'OPC 自用案例运营', level: 'expert', useCases: 100 },
    ],
    todayHours: 4.9,
    weekHours: 32,
    tasksCompleted: 178,
    successRate: 96.2,
  },
];

const ALL_SKILLS = EMPLOYEES.flatMap((e) =>
  e.skills.map((s) => ({ ...s, employee: e.id, employeeName: e.name, color: e.color, bg: e.bg }))
);

export function AIEmployeesPage() {
  const [search, setSearch] = useState('');
  const [filterEmp, setFilterEmp] = useState('all');

  const totalTasks = EMPLOYEES.reduce((sum, e) => sum + e.tasksCompleted, 0);
  const totalTodayHours = EMPLOYEES.reduce((sum, e) => sum + e.todayHours, 0);
  const totalSkills = ALL_SKILLS.length;
  const totalUseCases = ALL_SKILLS.reduce((sum, s) => sum + s.useCases, 0);

  const filteredSkills = ALL_SKILLS.filter((s) => {
    const matchEmp = filterEmp === 'all' || s.employee === filterEmp;
    const matchSearch = !search || s.name.toLowerCase().includes(search.toLowerCase());
    return matchEmp && matchSearch;
  });

  return (
    <>
      <section className="py-16 bg-gradient-to-br from-purple-50 via-white to-pink-50">
        <div className="max-w-page mx-auto px-6">
          <span className="inline-block px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm mb-4">
            🤖 5 AI 数字员工 · {totalSkills}+ skill 模板库
          </span>
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            1 人 + 5 AI 员工 = <span className="text-brand-500">1 整家公司</span>
          </h1>
          <p className="text-lg text-gray-600 mb-8 max-w-2xl">
            Cloud 自己的 5 个 AI 员工是怎么分工的。每人 1 个核心职责 + 7×24 在线 + 0 工资成本。
          </p>

          {/* 4 大总览指标 + skill 大数字 */}
          <div className="grid md:grid-cols-4 gap-4 mb-4">
            <StatCard label="今日总工时" value={`${totalTodayHours.toFixed(1)} h`} />
            <StatCard label="本周总工时" value={`${EMPLOYEES.reduce((s, e) => s + e.weekHours, 0)} h`} />
            <StatCard label="累计完成任务" value={totalTasks} />
            <StatCard label="平均成功率" value={`${(EMPLOYEES.reduce((s, e) => s + e.successRate, 0) / EMPLOYEES.length).toFixed(1)}%`} />
          </div>

          <div className="grid md:grid-cols-4 gap-4">
            <StatCard label="Skill 模板数" value={`${totalSkills}+`} sub="5 角色 × 平均 30+" highlight />
            <StatCard label="总 use case" value={`${totalUseCases}+`} sub="累计实证" highlight />
            <StatCard label="行业模板" value="10+" sub="装企/医美/通用" />
            <StatCard label="Phase 实证" value="46+" sub="Phase 8-47 全段" />
          </div>
        </div>
      </section>

      {/* 5 员工详情 */}
      <section className="py-12 bg-card">
        <div className="max-w-page mx-auto px-6 space-y-8">
          {EMPLOYEES.map((e) => (
            <EmployeeCard key={e.id} e={e} />
          ))}
        </div>
      </section>

      {/* Skill 库（搜索 + 筛选） */}
      <section className="py-12 bg-gray-50">
        <div className="max-w-page mx-auto px-6">
          <h2 className="text-2xl font-bold mb-2 flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-purple-500" /> 全 {totalSkills}+ skill 模板库
          </h2>
          <p className="text-sm text-gray-500 mb-6">
            5 角色 × 平均 30+ skill = 完整工种覆盖。可搜索、可按角色筛选。
          </p>

          {/* 搜索 + 筛选 */}
          <div className="bg-card p-4 rounded-lg border border-gray-200 mb-6">
            <div className="flex flex-col md:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder={`搜 ${totalSkills}+ skill...`}
                  className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:border-brand-500 focus:outline-none text-sm"
                />
              </div>
              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={() => setFilterEmp('all')}
                  className={`px-3 py-1.5 rounded text-xs font-medium ${filterEmp === 'all' ? 'bg-brand-500 text-white' : 'bg-gray-100 text-foreground hover:bg-gray-200'}`}
                >
                  全部 ({totalSkills})
                </button>
                {EMPLOYEES.map((e) => (
                  <button
                    key={e.id}
                    onClick={() => setFilterEmp(e.id)}
                    className={`px-3 py-1.5 rounded text-xs font-medium ${filterEmp === e.id ? `${e.bg} ${e.color}` : 'bg-gray-100 text-foreground hover:bg-gray-200'}`}
                  >
                    {e.name} ({e.skills.length})
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Skill 网格 */}
          {filteredSkills.length === 0 ? (
            <div className="text-center py-12 text-gray-500">没找到匹配的 skill</div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {filteredSkills.map((s, i) => {
                const e = EMPLOYEES.find((emp) => emp.id === s.employee)!;
                const Icon = e.icon;
                return (
                  <div
                    key={`${s.employee}-${i}`}
                    className="p-3 bg-card rounded-lg border border-gray-200 hover:border-brand-500 hover:shadow transition"
                  >
                    <div className="flex items-start gap-2 mb-1">
                      <div className={`w-6 h-6 rounded ${e.bg} flex items-center justify-center ${e.color} flex-shrink-0`}>
                        <Icon className="w-3 h-3" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{s.name}</p>
                        <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                          <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                            s.level === 'expert' ? 'bg-green-100 text-green-700' :
                            s.level === 'advanced' ? 'bg-blue-100 text-blue-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {s.level === 'expert' ? '⭐ 专家' : s.level === 'advanced' ? '✓ 高级' : '入门'}
                          </span>
                          <span>{s.useCases} 用例</span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 bg-gradient-to-r from-brand-500 to-brand-600 text-white">
        <div className="max-w-page mx-auto px-6 text-center">
          <Sparkles className="w-12 h-12 mx-auto mb-4" />
          <h2 className="text-3xl font-bold mb-4">想自己拥有这 {totalSkills}+ skill 模板？</h2>
          <p className="text-lg opacity-90 mb-8">
            7 天免费试用 · 5 AI 员工 + 全 skill 库 · 不需要信用卡
          </p>
          <Link
            to="/try"
            className="px-8 py-3 bg-card text-brand-500 rounded-md hover:bg-gray-100 inline-flex items-center gap-2 font-medium"
          >
            立即试用 <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </>
  );
}

function StatCard({ label, value, sub, highlight }: { label: string; value: string | number; sub?: string; highlight?: boolean }) {
  return (
    <Card className={`p-0 ${highlight ? 'bg-gradient-to-br from-accent-purple-50 to-card border-accent-purple-200' : ''}`}>
      <CardContent className="p-5">
        <p className="text-3xl font-bold text-brand-600">{value}</p>
        <p className="text-sm text-muted-foreground mt-1">{label}</p>
        {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
      </CardContent>
    </Card>
  );
}

function EmployeeCard({ e }: { e: Employee }) {
  const Icon = e.icon;
  return (
    <Card className="p-0 overflow-hidden hover:border-brand-500 transition border-2">
      {/* Hero header 带背景色 */}
      <div className={`p-6 ${e.bg}`}>
        <div className="flex items-center gap-4">
          <div className={`w-16 h-16 rounded-xl bg-card flex items-center justify-center ${e.color}`}>
            <Icon className="w-8 h-8" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-2xl font-bold text-card-foreground">{e.name}</h3>
              <Badge className={`${e.color} bg-card`}>
                {e.role}
              </Badge>
            </div>
            <p className="text-sm italic text-muted-foreground">"{e.motto}"</p>
          </div>
          <div className="text-right">
            <p className={`text-3xl font-bold ${e.color}`}>{e.skills.length}</p>
            <p className="text-xs text-muted-foreground">skill 模板</p>
          </div>
        </div>
      </div>

      <div className="p-6 grid md:grid-cols-3 gap-6">
        {/* 工时统计 */}
        <div>
          <p className="text-xs uppercase font-bold text-muted-foreground mb-3">📊 工时统计</p>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">今日</span>
              <span className="font-bold text-foreground">{e.todayHours} h</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">本周</span>
              <span className="font-bold text-foreground">{e.weekHours} h</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">累计任务</span>
              <span className="font-bold text-foreground">{e.tasksCompleted}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">成功率</span>
              <span className="font-bold text-success-600">{e.successRate}%</span>
            </div>
          </div>
        </div>

        {/* 核心职责 */}
        <div>
          <p className="text-xs uppercase font-bold text-muted-foreground mb-3">📋 核心职责</p>
          <ul className="space-y-1.5">
            {e.responsibilities.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-foreground">
                <CheckCircle2 className={`w-4 h-4 ${e.color} flex-shrink-0 mt-0.5`} />
                <span>{r}</span>
              </li>
            ))}
          </ul>
          <div className="mt-4">
            <p className="text-xs uppercase font-bold text-muted-foreground mb-2">🗂️ 6 大类</p>
            <div className="flex flex-wrap gap-1">
              {e.categories.map((c) => (
                <Badge key={c} className={`${e.bg} ${e.color} text-xs`}>
                  {c}
                </Badge>
              ))}
            </div>
          </div>
        </div>

        {/* Top skill 预览 */}
        <div>
          <p className="text-xs uppercase font-bold text-muted-foreground mb-3">⭐ Top skills（前 8）</p>
          <div className="space-y-1.5">
            {e.skills.slice(0, 8).map((s, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <span className="truncate flex-1 text-foreground">{s.name}</span>
                <span className="text-xs text-muted-foreground ml-2">{s.useCases}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground mt-3">
            + {e.skills.length - 8} more（见下方 skill 库）
          </p>
        </div>
      </div>
    </Card>
  );
}
