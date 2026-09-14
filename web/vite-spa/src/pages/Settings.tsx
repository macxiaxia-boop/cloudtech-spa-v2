// Phase 46 D38-40 — 客户设置页
import { useEffect, useState } from 'react';
import { Settings as SettingsIcon, Building2, Phone, Mail, Check } from 'lucide-react';

interface TenantInfo {
  tenant_id: string;
  plan: string;
  contact_name: string;
  contact_email: string;
  company: string;
}

export function SettingsPage() {
  const [tenant, setTenant] = useState<TenantInfo | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch('/api/v2/billing/tenants')
      .then(r => r.json())
      .then(d => {
        const t = d.tenants?.find((x: TenantInfo) => x.tenant_id === 'default');
        if (t) setTenant(t);
      });
  }, []);

  if (!tenant) {
    return <div className="max-w-page mx-auto px-6 py-20 text-center">加载中…</div>;
  }

  return (
    <div className="py-12 bg-gray-50 min-h-screen">
      <div className="max-w-3xl mx-auto px-6">
        <div className="flex items-center gap-3 mb-8">
          <SettingsIcon className="w-7 h-7 text-brand-500" />
          <h1 className="text-3xl font-bold">账号设置</h1>
        </div>

        {/* 公司信息 */}
        <section className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Building2 className="w-5 h-5" /> 公司信息
          </h2>
          <Field label="租户 ID" value={tenant.tenant_id} readOnly />
          <Field label="公司名称" value={tenant.company} />
          <Field label="套餐" value={tenant.plan} readOnly />
        </section>

        {/* 联系信息 */}
        <section className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Phone className="w-5 h-5" /> 联系人
          </h2>
          <Field label="联系人姓名" value={tenant.contact_name} />
          <Field label="邮箱" value={tenant.contact_email} icon={<Mail className="w-4 h-4" />} />
        </section>

        <button
          onClick={() => {
            // 红 #22 守门：实际改资料需用户拍板（生产应接 PUT /api/v2/billing/tenants/{tid}）
            setSaved(true);
            setTimeout(() => setSaved(false), 2000);
          }}
          className="w-full px-6 py-3 bg-brand-500 text-white rounded-md hover:bg-brand-600 inline-flex items-center justify-center gap-2"
        >
          {saved ? <><Check className="w-4 h-4" /> 已保存（Demo）</> : '保存修改'}
        </button>

        <p className="text-xs text-gray-400 mt-4 text-center">
          注：实际修改接口待用户拍板后接入（红 #22）
        </p>
      </div>
    </div>
  );
}

function Field({ label, value, icon, readOnly = false }: { label: string; value: string; icon?: React.ReactNode; readOnly?: boolean }) {
  return (
    <div className="mb-3">
      <label className="block text-xs text-gray-500 mb-1">{label}</label>
      <div className="flex items-center gap-2">
        {icon}
        <input
          type="text"
          defaultValue={value}
          readOnly={readOnly}
          className={`flex-1 px-3 py-2 border rounded-md text-sm ${readOnly ? 'bg-gray-50 text-gray-500' : 'bg-white border-gray-300'}`}
        />
      </div>
    </div>
  );
}
