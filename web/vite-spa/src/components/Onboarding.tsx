// 首次访问 onboarding wizard（5 步）
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { X, ChevronRight, ChevronLeft, Sparkles } from 'lucide-react';

interface OnboardingProps {
  onComplete: () => void;
}

const STEPS = [
  {
    icon: '👋',
    title: '欢迎来到 Cloud',
    desc: '1 人 + AI 的整家公司。我是心之所向便是光，Cloud的创始人 + 0 号用户。本产品我自己用、自己跑、自己讲案例。',
    cta: '下一步',
  },
  {
    icon: '🎯',
    title: '4 步搞定你公司',
    desc: '① 选 5 AI 数字员工 → ② 让它们跑你业务 → ③ 看真实数据 → ④ 讲你的 OPC 故事',
    cta: '继续',
  },
  {
    icon: '🤖',
    title: '5 个 AI 数字员工',
    desc: 'Hermes（治理）/ Lyra（内容）/ Athena（架构）/ Apollo（数据）/ Artemis（运营）。它们 7×24 帮你跑业务，你睡觉时也干活。',
    cta: '看看 5 员工',
    ctaLink: '/employees',
  },
  {
    icon: '📊',
    title: '看你的真实仪表盘',
    desc: 'MRR / 漏斗 / 监控 / 财务 / 监控告警 — 你的业务跑得怎样，一眼看完。',
    cta: '看监控',
    ctaLink: '/monitoring',
  },
  {
    icon: '🚀',
    title: '7 天免费试用',
    desc: '不用信用卡。30 分钟跑通你公司的第一条管线。',
    cta: '开始试用',
    ctaLink: '/try',
  },
];

export function Onboarding({ onComplete }: OnboardingProps) {
  const [step, setStep] = useState(0);
  const current = STEPS[step];

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full p-8 relative shadow-2xl">
        <button
          onClick={onComplete}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="text-center mb-6">
          <div className="text-7xl mb-4">{current.icon}</div>
          <h2 className="text-2xl font-bold mb-2">{current.title}</h2>
          <p className="text-gray-600">{current.desc}</p>
        </div>

        {/* 进度 */}
        <div className="flex justify-center gap-1 mb-6">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-1.5 w-8 rounded-full transition-colors ${
                i <= step ? 'bg-brand-500' : 'bg-gray-200'
              }`}
            />
          ))}
        </div>

        {/* CTA */}
        <div className="flex items-center justify-between gap-3">
          {step > 0 ? (
            <button
              onClick={() => setStep(step - 1)}
              className="px-4 py-2 text-gray-600 hover:text-gray-900 flex items-center gap-1"
            >
              <ChevronLeft className="w-4 h-4" /> 上一步
            </button>
          ) : (
            <button
              onClick={onComplete}
              className="px-4 py-2 text-gray-400 hover:text-gray-600 text-sm"
            >
              跳过引导
            </button>
          )}

          {step < STEPS.length - 1 ? (
            <button
              onClick={() => setStep(step + 1)}
              className="px-6 py-2 bg-brand-500 text-white rounded-md hover:bg-brand-600 flex items-center gap-1"
            >
              {current.cta} <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <Link
              to={current.ctaLink || '/dashboard'}
              onClick={onComplete}
              className="px-6 py-2 bg-brand-500 text-white rounded-md hover:bg-brand-600 flex items-center gap-1"
            >
              <Sparkles className="w-4 h-4" /> {current.cta}
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
