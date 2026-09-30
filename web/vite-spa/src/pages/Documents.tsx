// Phase 46 D53-60 — OPC 公司文档中心（合同/HR/财务/营业执照）
import { Link } from 'react-router-dom';
import { FileText, ArrowRight, AlertCircle, Shield, Users, DollarSign, Building2, Phone } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface Document {
  id: string;
  category: 'legal' | 'hr' | 'finance' | 'marketing';
  title: string;
  desc: string;
  path: string;
  redlines: string[];
  requires_user_approval: string[];
}

const DOCUMENTS: Document[] = [
  // Legal
  {
    id: 'doc-customer-service',
    category: 'legal',
    title: '客户主服务协议',
    desc: 'Cloud与客户的标准 SaaS 服务协议，含 SLA/数据归属/退费',
    path: 'legal/contracts/customer_service_agreement.md',
    redlines: ['#22 合同签字'],
    requires_user_approval: ['真实工商主体', '套餐定价', 'SLA 指标', '法务终审', '实际签字'],
  },
  {
    id: 'doc-nda',
    category: 'legal',
    title: '保密协议（NDA）',
    desc: '与客户/合作方的双向保密协议，3 年期 + ¥50 万违约金',
    path: 'legal/contracts/nda.md',
    redlines: ['#22 合同签字'],
    requires_user_approval: ['真实工商主体', '违约金金额', '保密期限'],
  },
  {
    id: 'doc-dpa',
    category: 'legal',
    title: '数据处理协议（DPA）',
    desc: '依据《个人信息保护法》《数据安全法》《网络安全法》',
    path: 'legal/contracts/data_processing_agreement.md',
    redlines: ['#22 合同签字'],
    requires_user_approval: ['跨境传输', '数据安全事件通知时限'],
  },
  {
    id: 'doc-medical-redlines',
    category: 'legal',
    title: '医美 6 条合规红线',
    desc: 'AI 自动拦截清单 + 装入 SaaS 平台的实施 SOP',
    path: 'legal/medical_compliance_redlines.md',
    redlines: ['#22 医美行业合规'],
    requires_user_approval: ['拦截阈值', 'OpenCV 自动打码', '法规更新触发机制'],
  },
  {
    id: 'doc-legal-checklist',
    category: 'legal',
    title: '法务审查清单',
    desc: '5 类合同 × 35 项必审 + AI 自动审 + 外聘律师审 4 步 SOP',
    path: 'legal/contracts/legal_review_checklist.md',
    redlines: ['#22 外聘律所'],
    requires_user_approval: ['律所选择', '外审频率'],
  },
  {
    id: 'doc-business-license',
    category: 'legal',
    title: '营业执照申请材料清单',
    desc: '公司名称/注册资本/经营范围/法人股东/注册地址 5 类必填',
    path: 'legal/license/business_license_checklist.md',
    redlines: ['#22 公司注册'],
    requires_user_approval: ['公司名称', '注册资本', '经营范围', '法人/股东', '注册地址'],
  },
  {
    id: 'doc-registration-flow',
    category: 'legal',
    title: '公司注册流程图',
    desc: 'M0 准备 → M1 注册 → M2 资质 5 周全流程 + 失败预案',
    path: 'legal/license/registration_flow.md',
    redlines: ['#22 实际注册'],
    requires_user_approval: ['所有 M0 决策项', 'M1 提交动作', 'M2 资质办理', '银行账户'],
  },
  // HR
  {
    id: 'doc-jd-fe',
    category: 'hr',
    title: 'JD · FE 工程师',
    desc: 'AI 数字员工 · 前端 · P5/P6/P7 三档 + 5 轮面试',
    path: 'hr/jd_fe_engineer.md',
    redlines: ['#22 招聘 offer'],
    requires_user_approval: ['实际发 offer', '试用期长度', '股权比例'],
  },
  {
    id: 'doc-jd-be',
    category: 'hr',
    title: 'JD · BE 工程师',
    desc: 'AI 数字员工 · 后端 · FastAPI/PostgreSQL 栈',
    path: 'hr/jd_be_engineer.md',
    redlines: ['#22 招聘 offer'],
    requires_user_approval: ['实际发 offer', '试用期长度', '股权比例', '远程边界'],
  },
  {
    id: 'doc-jd-content',
    category: 'hr',
    title: 'JD · 内容运营',
    desc: 'Phase 41-44 内容 SOP 执行 · 7 步对比派最优 + 双轨卡',
    path: 'hr/jd_content_marketing.md',
    redlines: ['#22 招聘 offer'],
    requires_user_approval: ['实际发 offer', '试用期长度', 'KPI', '作品集选题'],
  },
  {
    id: 'doc-offer-template',
    category: 'hr',
    title: 'Offer 模板',
    desc: '4 件套附件 · 7 大风险点 + 法务审查',
    path: 'hr/offer_template.md',
    redlines: ['#22 招聘 offer'],
    requires_user_approval: ['候选人', '月薪金额', '期权', '实际签字'],
  },
  {
    id: 'doc-hiring-sop',
    category: 'hr',
    title: '招聘 SOP',
    desc: '5 阶段 12 步骤 · AI 可主动干 vs 红 #22 必拍板边界',
    path: 'hr/hiring_sop.md',
    redlines: ['#22 招聘'],
    requires_user_approval: ['实际发 offer', '月薪/期权', '录用决定', '转正', '辞退', '招聘付费'],
  },
  // Finance
  {
    id: 'doc-financial-model',
    category: 'finance',
    title: '财务模型',
    desc: '3 档套餐 · M1/M3/M6/M12 收入预测 · 5 类 SaaS 选型',
    path: 'finance/financial_model.md',
    redlines: ['#22 财务 SaaS'],
    requires_user_approval: ['选型 SaaS', '付费', '薪资发放', '发票开具', '融资签约', '税务'],
  },
  {
    id: 'doc-monitoring',
    category: 'finance',
    title: '监控仪表盘配置',
    desc: '4 Dashboard · P0/P1/P2/P3 告警分级',
    path: 'finance/monitoring_dashboard.md',
    redlines: ['#22 监控 SaaS'],
    requires_user_approval: ['监控 SaaS 选型', '告警接收人', '告警通道开通', '数据保留期'],
  },
  // Marketing
  {
    id: 'doc-outreach-deco',
    category: 'marketing',
    title: '装企外呼脚本（80 家）',
    desc: 'P0/P1/P2/P3 分级 · 5 状态机 · 触达节奏 + 数据回流',
    path: 'marketing/scripts/outreach_decoration.md',
    redlines: ['#22 客户触达'],
    requires_user_approval: ['实际拨打电话', '加微信', '发短信', '发邮件', '试用账号开通'],
  },
  {
    id: 'doc-outreach-medical',
    category: 'marketing',
    title: '医美外呼脚本（30 家）',
    desc: '医美合规话术 · 6 红线严格遵守',
    path: 'marketing/scripts/outreach_medical.md',
    redlines: ['#22 客户触达 + #22 医美合规'],
    requires_user_approval: ['实际拨打电话', '加微信', '发短信/邮件', '案例脱敏示例', '试用账号'],
  },
];

const CATEGORY_META: Record<Document['category'], { label: string; icon: any; color: string; bg: string }> = {
  legal: { label: '法务 / 营业执照', icon: Shield, color: 'text-red-600', bg: 'bg-red-50 border-red-200' },
  hr: { label: '团队 / 招聘', icon: Users, color: 'text-blue-600', bg: 'bg-blue-50 border-blue-200' },
  finance: { label: '财务 / 监控', icon: DollarSign, color: 'text-green-600', bg: 'bg-green-50 border-green-200' },
  marketing: { label: '营销 / 触达', icon: Phone, color: 'text-yellow-600', bg: 'bg-yellow-50 border-yellow-200' },
};

export function DocumentsPage() {
  // 按类别分组
  const grouped = DOCUMENTS.reduce((acc, doc) => {
    if (!acc[doc.category]) acc[doc.category] = [];
    acc[doc.category].push(doc);
    return acc;
  }, {} as Record<string, Document[]>);

  const totalDocs = DOCUMENTS.length;
  const totalApprovals = DOCUMENTS.reduce((sum, d) => sum + d.requires_user_approval.length, 0);

  return (
    <>
      {/* HERO */}
      <section className="relative py-16 bg-gradient-to-br from-slate-50 via-white to-gray-50 overflow-hidden">
        <div className="max-w-page mx-auto px-6 grid md:grid-cols-2 gap-10 items-center">
          <div>
            <span className="inline-flex items-center gap-2 px-3 py-1 bg-slate-100 text-slate-700 rounded-full text-sm mb-4">
              <FileText className="w-3 h-3" /> Phase 46 D53-60 · OPC 公司文档中心
            </span>
            <h1 className="text-4xl md:text-5xl font-bold mb-4 leading-[1.1]">
              公司文档中心
              <br />
              <span className="text-slate-600">合同 + HR + 财务 + 营业执照</span>
            </h1>
            <p className="text-lg text-gray-600 mb-6">
              Phase 46 段 3 (D53-60) 收官 — 所有内部文档就绪。
              红 #22 边界：内部文档 AI 可主动干，外部签字 / 钱 / 触达必用户拍板。
            </p>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-6 border-t border-gray-200">
              <div>
                <p className="text-2xl font-bold text-slate-700">{totalDocs}</p>
                <p className="text-xs text-gray-500">文档总数</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-red-600">{totalApprovals}</p>
                <p className="text-xs text-gray-500">红 #22 项</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-red-600">{grouped.legal?.length || 0}</p>
                <p className="text-xs text-gray-500">法务</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-blue-600">{grouped.hr?.length || 0}</p>
                <p className="text-xs text-gray-500">HR</p>
              </div>
            </div>
          </div>
          <div>
            <img
              src="/images/documents-hero.jpeg"
              alt="公司文档中心"
              className="rounded-2xl shadow-2xl w-full"
            />
          </div>
        </div>
      </section>

      {/* 红 #22 守门 */}
      <section className="py-6 bg-red-50 border-y border-red-200">
        <div className="max-w-page mx-auto px-6">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm">
              <p className="font-medium text-red-800">红线 #22 总览</p>
              <p className="text-red-700 mt-1">
                内部文档（模板/JD/财务模型/流程图）= AI 已主动干，<strong>{totalDocs}</strong> 份就绪。
                外部动作（签字/打款/招聘 offer/客户触达/实际注册）= 必用户拍板，共 <strong>{totalApprovals}</strong> 项待办。
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 4 类别文档 */}
      {Object.entries(grouped).map(([cat, docs]) => {
        const meta = CATEGORY_META[cat as Document['category']];
        const Icon = meta.icon;
        return (
          <section key={cat} className="py-12 bg-white border-b border-gray-100">
            <div className="max-w-page mx-auto px-6">
              <div className="flex items-center gap-3 mb-6">
                <Icon className={`w-6 h-6 ${meta.color}`} />
                <h2 className="text-2xl font-bold">{meta.label}</h2>
                <span className="text-sm text-gray-500">({docs.length} 文档)</span>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                {docs.map((doc) => (
                  <div key={doc.id} className={`p-5 rounded-lg border ${meta.bg}`}>
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="text-base font-bold flex-1">{doc.title}</h3>
                      <span className="text-xs px-2 py-0.5 bg-white rounded text-gray-500 font-mono">
                        {doc.path.split('/').pop()}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 mb-3">{doc.desc}</p>

                    <div className="text-xs text-gray-600 mb-2">
                      <span className="font-medium">路径: </span>
                      <code className="px-1 py-0.5 bg-white rounded font-mono text-xs">{doc.path}</code>
                    </div>

                    {doc.redlines.length > 0 && (
                      <div className="flex flex-wrap gap-1 mb-2">
                        {doc.redlines.map((r) => (
                          <span key={r} className="text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded">
                            {r}
                          </span>
                        ))}
                      </div>
                    )}

                    <details className="text-xs">
                      <summary className="cursor-pointer text-gray-600 hover:text-gray-900">
                        红 #22 必拍板项 ({doc.requires_user_approval.length})
                      </summary>
                      <ul className="mt-2 space-y-1 pl-4 list-disc text-gray-700">
                        {doc.requires_user_approval.map((a, i) => (
                          <li key={i}>{a}</li>
                        ))}
                      </ul>
                    </details>
                  </div>
                ))}
              </div>
            </div>
          </section>
        );
      })}

      {/* CTA */}
      <section className="py-16 bg-slate-700 text-white">
        <div className="max-w-page mx-auto px-6 text-center">
          <Building2 className="w-12 h-12 mx-auto mb-4" />
          <h2 className="text-3xl font-bold mb-4">{totalDocs} 份内部文档就绪 · 待你逐项拍板</h2>
          <p className="text-lg opacity-90 mb-8">
            Phase 46 段 3 收官 · AI 已完成所有内部资源 · 外部动作 = 必用户拍板
          </p>
          <Link
            to="/clients"
            className="px-8 py-3 bg-white text-slate-700 rounded-md hover:bg-gray-100 inline-flex items-center gap-2 font-medium"
          >
            查看客户清单 <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </>
  );
}
