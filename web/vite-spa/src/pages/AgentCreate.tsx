/**
 * CloudTech AgentCreate · v3 视觉母版 07 模块
 * 5 步向导：基础信息 → 技能配置 → 知识库 → 测试对话 → 发布使用
 * v3 supersede v2 的 6 步（合并"角色+技能"为"技能配置"，新增"测试对话"）
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Check, Sparkles, FileText, MessageSquare, Rocket, Settings2, BookOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useTranslation } from '@/i18n';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

const steps = [
  { num: 1, label: '基础信息', icon: FileText },
  { num: 2, label: '技能配置', icon: Settings2 },
  { num: 3, label: '知识库',   icon: BookOpen },
  { num: 4, label: '测试对话', icon: MessageSquare },
  { num: 5, label: '发布使用', icon: Rocket },
] as const;

const skillOptions = [
  '市场分析', '竞品分析', '用户增长', '行业洞察',
  '内容创作', '客户报告', '文档处理', '数据分析',
];

export function AgentCreatePage() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [step, setStep] = useState(1);
  const [skills, setSkills] = useState<string[]>([]);
  const [dataSource, setDataSource] = useState({ mongodb: false, postgresql: false, python: false });
  const [visible, setVisible] = useState('team');

  function toggleSkill(s: string) {
    setSkills((prev) => prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]);
  }

  function next() {
    if (step < 5) setStep(step + 1);
    else navigate('/employees');
  }
  function prev() { if (step > 1) setStep(step - 1); }

  return (
    <div className="max-w-[var(--agent-wizard-max-w)] mx-auto">
      {/* 进度条 */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          {steps.map((s) => {
            const Icon = s.icon;
            const isActive = s.num === step;
            const isDone = s.num < step;
            return (
              <div key={s.num} className="flex items-center gap-2 flex-1">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium shrink-0 transition-colors ${
                  isActive ? 'bg-brand-600 text-white'
                  : isDone ? 'bg-success-500 text-white'
                  : 'bg-muted text-muted-foreground'
                }`}>
                  {isDone ? <Check className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                </div>
                <div className={`text-sm ${isActive ? 'font-medium text-foreground' : 'text-muted-foreground'}`}>{s.label}</div>
                {s.num < 5 && <div className={`flex-1 h-0.5 mx-2 ${isDone ? 'bg-success-500' : 'bg-[var(--neutral-200)]'}`} />}
              </div>
            );
          })}
        </div>
      </div>

      {/* 步骤内容 */}
      <div className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
        <div className="grid grid-cols-[1fr_400px]">
          {/* 左：表单 */}
          <div className="p-8 border-r border-border">
            {step === 1 && (
              <div className="space-y-5">
                <h2 className="text-lg font-semibold">基础信息</h2>
                <div className="space-y-1.5">
                  <Label htmlFor="name">名称</Label>
                  <Input id="name" placeholder="市场分析师" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="intro">简介</Label>
                  <Input id="intro" placeholder="一句话描述它的核心能力" />
                </div>
                <div className="space-y-1.5">
                  <Label>头像</Label>
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-brand-500 to-accent-purple-500 flex items-center justify-center">
                      <Sparkles className="w-6 h-6 text-white" />
                    </div>
                    <Button variant="outline" size="sm">更换头像</Button>
                  </div>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-5">
                <h2 className="text-lg font-semibold">技能配置</h2>
                <p className="text-sm text-muted-foreground">选择该智能体擅长的技能领域，可多选</p>
                <div className="grid grid-cols-2 gap-2">
                  {skillOptions.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => toggleSkill(s)}
                      className={`flex items-center justify-between px-3 py-2.5 rounded-md border text-sm transition-colors ${
                        skills.includes(s)
                          ? 'border-brand-500 bg-brand-50 text-brand-700'
                          : 'border-border hover:bg-muted'
                      }`}
                    >
                      <span>{s}</span>
                      {skills.includes(s) && <Check className="w-4 h-4" />}
                    </button>
                  ))}
                </div>
                <div className="pt-3 border-t border-border space-y-3">
                  <Label>数据源</Label>
                  {[
                    { key: 'mongodb' as const, label: 'MongoDB' },
                    { key: 'postgresql' as const, label: 'PostgreSQL' },
                    { key: 'python' as const, label: 'Python 脚本' },
                  ].map((ds) => (
                    <label key={ds.key} className="flex items-center justify-between p-2 rounded-md hover:bg-muted cursor-pointer">
                      <span className="text-sm">{ds.label}</span>
                      <button
                        type="button"
                        onClick={() => setDataSource({ ...dataSource, [ds.key]: !dataSource[ds.key] })}
                        className={`relative w-9 h-5 rounded-full transition-colors ${dataSource[ds.key] ? 'bg-brand-600' : 'bg-[var(--neutral-300)]'}`}
                      >
                        <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-card transition-transform ${dataSource[ds.key] ? 'translate-x-4' : ''}`} />
                      </button>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-5">
                <h2 className="text-lg font-semibold">知识库</h2>
                <p className="text-sm text-muted-foreground">选择该智能体可以访问的知识库</p>
                <div className="space-y-2">
                  {['市场分析报告集', '产品需求文档库', '用户调研数据', '行业洞察报告'].map((kb) => (
                    <label key={kb} className="flex items-center gap-3 p-3 rounded-md border border-border hover:bg-muted cursor-pointer">
                      <input type="checkbox" className="rounded text-brand-600" />
                      <BookOpen className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm flex-1">{kb}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {step === 4 && (
              <div className="space-y-5">
                <h2 className="text-lg font-semibold">测试对话</h2>
                <p className="text-sm text-muted-foreground">用一段测试对话验证智能体表现</p>
                <div className="border border-border rounded-lg p-4 min-h-[200px] bg-muted">
                  <div className="flex gap-2 mb-3">
                    <div className="w-7 h-7 rounded-full bg-[var(--neutral-200)] flex items-center justify-center text-xs">U</div>
                    <div className="bg-card rounded-lg px-3 py-2 text-sm border border-border">分析最近 3 个月的市场趋势</div>
                  </div>
                  <div className="flex gap-2">
                    <div className="w-7 h-7 rounded-full bg-brand-100 flex items-center justify-center text-xs text-brand-600">AI</div>
                    <div className="bg-brand-50 rounded-lg px-3 py-2 text-sm max-w-md">
                      根据市场分析报告集，最近 3 个月的主要趋势包括：1. AI 产品渗透加速；2. 用户付费意愿提升；3. 竞争格局重塑。
                    </div>
                  </div>
                </div>
                <Textarea placeholder="发送测试消息…" className="min-h-[80px]" />
              </div>
            )}

            {step === 5 && (
              <div className="space-y-5">
                <h2 className="text-lg font-semibold">发布使用</h2>
                <div className="space-y-1.5">
                  <Label>可见范围</Label>
                  <div className="flex gap-2">
                    {[
                      { key: 'private', label: '仅我' },
                      { key: 'team', label: '团队' },
                      { key: 'public', label: '公开' },
                    ].map((v) => (
                      <button
                        key={v.key}
                        type="button"
                        onClick={() => setVisible(v.key)}
                        className={`flex-1 px-3 py-2 rounded-md border text-sm transition-colors ${
                          visible === v.key
                            ? 'border-brand-500 bg-brand-50 text-brand-700'
                            : 'border-border hover:bg-muted'
                        }`}
                      >{v.label}</button>
                    ))}
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="instruction">使用说明</Label>
                  <Textarea id="instruction" placeholder="告诉用户这个智能体能帮他们做什么…" className="min-h-[100px]" />
                </div>
                <div className="p-4 bg-success-bg rounded-lg border border-success-100 flex items-start gap-3">
                  <Check className="w-5 h-5 text-success-600 shrink-0 mt-0.5" />
                  <div className="text-sm">
                    <div className="font-medium text-success-700">已就绪 · 可发布</div>
                    <div className="text-success-700 mt-1">配置全部完成，点击"发布"后智能体将立即可用。</div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* 右：实时预览 */}
          <div className="p-6 bg-muted">
            <div className="text-xs text-muted-foreground mb-3 font-medium">实时预览</div>
            <div className="bg-card rounded-lg border border-border p-5">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-brand-500 to-accent-purple-500 flex items-center justify-center shrink-0">
                  <Sparkles className="w-6 h-6 text-white" />
                </div>
                <div>
                  <div className="font-semibold">市场分析师</div>
                  <div className="text-xs text-muted-foreground">一句话描述它的核心能力</div>
                </div>
              </div>
              {skills.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {skills.map((s) => (
                    <span key={s} className="text-xs px-2 py-0.5 rounded-full bg-brand-50 text-brand-700">{s}</span>
                  ))}
                </div>
              )}
              <div className="text-xs text-muted-foreground">已使用 0 次</div>
            </div>
          </div>
        </div>

        {/* 底部按钮 */}
        <div className="border-t border-border px-8 py-4 flex items-center justify-between bg-muted">
          <Button variant="ghost" onClick={prev} disabled={step === 1}>
            <ArrowLeft className="w-4 h-4" />上一步
          </Button>
          <div className="text-xs text-muted-foreground">第 {step} / 5 步</div>
          <Button onClick={next}>
            {step === 5 ? '发布' : '下一步'}<ArrowRight className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
