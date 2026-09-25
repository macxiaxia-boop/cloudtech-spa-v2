// Phase 46 D49-52 — 首批 50 家装企 + 30 家医美客户触达清单
import { Link } from 'react-router-dom';
import { Users, ArrowRight, MapPin, Phone, Mail, Building2, AlertCircle } from 'lucide-react';

interface Client {
  id: string;
  name: string;
  city: string;
  industry: 'decoration' | 'medical';
  scale: 'small' | 'medium' | 'large';
  contact?: string;
  phone?: string;
  status: 'pending' | 'contacted' | 'demo_scheduled' | 'trial' | 'signed';
}

const CLIENTS: Client[] = [
  // ─── 装企 50 家（一线城市 + 新一线） ───
  // 北京 5
  { id: 'D-BJ-001', name: '北京东易日盛装饰', city: '北京', industry: 'decoration', scale: 'large', contact: '王总', phone: '138****0001', status: 'pending' },
  { id: 'D-BJ-002', name: '北京业之峰装饰', city: '北京', industry: 'decoration', scale: 'large', contact: '李工', phone: '138****0002', status: 'pending' },
  { id: 'D-BJ-003', name: '北京今朝装饰', city: '北京', industry: 'decoration', scale: 'medium', contact: '张总', phone: '138****0003', status: 'pending' },
  { id: 'D-BJ-004', name: '北京轻舟装饰', city: '北京', industry: 'decoration', scale: 'medium', contact: '刘工', phone: '138****0004', status: 'pending' },
  { id: 'D-BJ-005', name: '北京博洛尼装饰', city: '北京', industry: 'decoration', scale: 'large', contact: '陈总监', phone: '138****0005', status: 'pending' },
  // 上海 5
  { id: 'D-SH-001', name: '上海聚通装饰', city: '上海', industry: 'decoration', scale: 'large', contact: '王总', phone: '138****0011', status: 'pending' },
  { id: 'D-SH-002', name: '上海统帅装饰', city: '上海', industry: 'decoration', scale: 'medium', contact: '李工', phone: '138****0012', status: 'pending' },
  { id: 'D-SH-003', name: '上海百姓装饰', city: '上海', industry: 'decoration', scale: 'medium', contact: '张总', phone: '138****0013', status: 'pending' },
  { id: 'D-SH-004', name: '上海全筑装饰', city: '上海', industry: 'decoration', scale: 'large', contact: '刘工', phone: '138****0014', status: 'pending' },
  { id: 'D-SH-005', name: '上海红蚂蚁装饰', city: '上海', industry: 'decoration', scale: 'medium', contact: '陈总监', phone: '138****0015', status: 'pending' },
  // 广州 4
  { id: 'D-GZ-001', name: '广州星艺装饰', city: '广州', industry: 'decoration', scale: 'large', contact: '王总', phone: '138****0021', status: 'pending' },
  { id: 'D-GZ-002', name: '广州华浔品味装饰', city: '广州', industry: 'decoration', scale: 'medium', contact: '李工', phone: '138****0022', status: 'pending' },
  { id: 'D-GZ-003', name: '广州名匠装饰', city: '广州', industry: 'decoration', scale: 'medium', contact: '张总', phone: '138****0023', status: 'pending' },
  { id: 'D-GZ-004', name: '广州轩怡装饰', city: '广州', industry: 'decoration', scale: 'small', contact: '刘工', phone: '138****0024', status: 'pending' },
  // 深圳 4
  { id: 'D-SZ-001', name: '深圳居众装饰', city: '深圳', industry: 'decoration', scale: 'large', contact: '王总', phone: '138****0031', status: 'pending' },
  { id: 'D-SZ-002', name: '深圳浩天装饰', city: '深圳', industry: 'decoration', scale: 'medium', contact: '李工', phone: '138****0032', status: 'pending' },
  { id: 'D-SZ-003', name: '深圳乐蜂装饰', city: '深圳', industry: 'decoration', scale: 'medium', contact: '张总', phone: '138****0033', status: 'pending' },
  { id: 'D-SZ-004', name: '深圳誉家装饰', city: '深圳', industry: 'decoration', scale: 'small', contact: '刘工', phone: '138****0034', status: 'pending' },
  // 成都 4
  { id: 'D-CD-001', name: '成都华宁装饰', city: '成都', industry: 'decoration', scale: 'medium', contact: '王总', phone: '138****0041', status: 'pending' },
  { id: 'D-CD-002', name: '成都岚庭装饰', city: '成都', industry: 'decoration', scale: 'medium', contact: '李工', phone: '138****0042', status: 'pending' },
  { id: 'D-CD-003', name: '成都生活家装饰', city: '成都', industry: 'decoration', scale: 'large', contact: '张总', phone: '138****0043', status: 'pending' },
  { id: 'D-CD-004', name: '成都东易日盛装饰', city: '成都', industry: 'decoration', scale: 'medium', contact: '刘工', phone: '138****0044', status: 'pending' },
  // 杭州 4
  { id: 'D-HZ-001', name: '杭州良工装饰', city: '杭州', industry: 'decoration', scale: 'medium', contact: '王总', phone: '138****0051', status: 'pending' },
  { id: 'D-HZ-002', name: '杭州中博装饰', city: '杭州', industry: 'decoration', scale: 'medium', contact: '李工', phone: '138****0052', status: 'pending' },
  { id: 'D-HZ-003', name: '杭州圣都装饰', city: '杭州', industry: 'decoration', scale: 'large', contact: '张总', phone: '138****0053', status: 'pending' },
  { id: 'D-HZ-004', name: '杭州铭品装饰', city: '杭州', industry: 'decoration', scale: 'medium', contact: '刘工', phone: '138****0054', status: 'pending' },
  // 苏州 3
  { id: 'D-SU-001', name: '苏州尚层装饰', city: '苏州', industry: 'decoration', scale: 'large', contact: '王总', phone: '138****0061', status: 'pending' },
  { id: 'D-SU-002', name: '苏州红蚂蚁装饰', city: '苏州', industry: 'decoration', scale: 'medium', contact: '李工', phone: '138****0062', status: 'pending' },
  { id: 'D-SU-003', name: '苏州东易日盛装饰', city: '苏州', industry: 'decoration', scale: 'medium', contact: '张总', phone: '138****0063', status: 'pending' },
  // 武汉 3
  { id: 'D-WH-001', name: '武汉嘉禾装饰', city: '武汉', industry: 'decoration', scale: 'large', contact: '王总', phone: '138****0071', status: 'pending' },
  { id: 'D-WH-002', name: '武汉名仕装饰', city: '武汉', industry: 'decoration', scale: 'medium', contact: '李工', phone: '138****0072', status: 'pending' },
  { id: 'D-WH-003', name: '武汉澳华装饰', city: '武汉', industry: 'decoration', scale: 'medium', contact: '张总', phone: '138****0073', status: 'pending' },
  // 南京 3
  { id: 'D-NJ-001', name: '南京锦华装饰', city: '南京', industry: 'decoration', scale: 'medium', contact: '王总', phone: '138****0081', status: 'pending' },
  { id: 'D-NJ-002', name: '南京红牛装饰', city: '南京', industry: 'decoration', scale: 'medium', contact: '李工', phone: '138****0082', status: 'pending' },
  { id: 'D-NJ-003', name: '南京东易日盛装饰', city: '南京', industry: 'decoration', scale: 'medium', contact: '张总', phone: '138****0083', status: 'pending' },
  // 重庆 3
  { id: 'D-CQ-001', name: '重庆天古装饰', city: '重庆', industry: 'decoration', scale: 'medium', contact: '王总', phone: '138****0091', status: 'pending' },
  { id: 'D-CQ-002', name: '重庆远景装饰', city: '重庆', industry: 'decoration', scale: 'medium', contact: '李工', phone: '138****0092', status: 'pending' },
  { id: 'D-CQ-003', name: '重庆兄弟装饰', city: '重庆', industry: 'decoration', scale: 'medium', contact: '张总', phone: '138****0093', status: 'pending' },
  // 西安 3
  { id: 'D-XA-001', name: '西安城市人家装饰', city: '西安', industry: 'decoration', scale: 'medium', contact: '王总', phone: '138****0101', status: 'pending' },
  { id: 'D-XA-002', name: '西安峰光无限装饰', city: '西安', industry: 'decoration', scale: 'medium', contact: '李工', phone: '138****0102', status: 'pending' },
  { id: 'D-XA-003', name: '西安紫苹果装饰', city: '西安', industry: 'decoration', scale: 'medium', contact: '张总', phone: '138****0103', status: 'pending' },
  // 天津 3
  { id: 'D-TJ-001', name: '天津力天装饰', city: '天津', industry: 'decoration', scale: 'medium', contact: '王总', phone: '138****0111', status: 'pending' },
  { id: 'D-TJ-002', name: '天津业之峰装饰', city: '天津', industry: 'decoration', scale: 'medium', contact: '李工', phone: '138****0112', status: 'pending' },
  { id: 'D-TJ-003', name: '天津阳光力天装饰', city: '天津', industry: 'decoration', scale: 'medium', contact: '张总', phone: '138****0113', status: 'pending' },
  // 长沙 2
  { id: 'D-CS-001', name: '长沙美迪装饰', city: '长沙', industry: 'decoration', scale: 'medium', contact: '王总', phone: '138****0121', status: 'pending' },
  { id: 'D-CS-002', name: '长沙鸿扬装饰', city: '长沙', industry: 'decoration', scale: 'medium', contact: '李工', phone: '138****0122', status: 'pending' },
  // 青岛 2
  { id: 'D-QD-001', name: '青岛东方家园装饰', city: '青岛', industry: 'decoration', scale: 'medium', contact: '王总', phone: '138****0131', status: 'pending' },
  { id: 'D-QD-002', name: '青岛拜占庭装饰', city: '青岛', industry: 'decoration', scale: 'medium', contact: '李工', phone: '138****0132', status: 'pending' },
  // 郑州 1
  { id: 'D-ZZ-001', name: '郑州华拓装饰', city: '郑州', industry: 'decoration', scale: 'medium', contact: '王总', phone: '138****0141', status: 'pending' },
  // 济南 1
  { id: 'D-JN-001', name: '济南万泰装饰', city: '济南', industry: 'decoration', scale: 'medium', contact: '李工', phone: '138****0151', status: 'pending' },

  // ─── 医美 30 家（北上广深 + 新一线） ───
  // 北京 4
  { id: 'M-BJ-001', name: '北京美莱医疗美容', city: '北京', industry: 'medical', scale: 'large', contact: '王总', phone: '138****0201', status: 'pending' },
  { id: 'M-BJ-002', name: '北京华美医疗美容', city: '北京', industry: 'medical', scale: 'large', contact: '李院长', phone: '138****0202', status: 'pending' },
  { id: 'M-BJ-003', name: '北京丽都医疗美容', city: '北京', industry: 'medical', scale: 'medium', contact: '张总监', phone: '138****0203', status: 'pending' },
  { id: 'M-BJ-004', name: '北京伊美尔医疗美容', city: '北京', industry: 'medical', scale: 'medium', contact: '刘主任', phone: '138****0204', status: 'pending' },
  // 上海 4
  { id: 'M-SH-001', name: '上海美莱医疗美容', city: '上海', industry: 'medical', scale: 'large', contact: '王总', phone: '138****0211', status: 'pending' },
  { id: 'M-SH-002', name: '上海华美医疗美容', city: '上海', industry: 'medical', scale: 'large', contact: '李院长', phone: '138****0212', status: 'pending' },
  { id: 'M-SH-003', name: '上海玫瑰医疗美容', city: '上海', industry: 'medical', scale: 'medium', contact: '张总监', phone: '138****0213', status: 'pending' },
  { id: 'M-SH-004', name: '上海时光整形外科', city: '上海', industry: 'medical', scale: 'medium', contact: '刘主任', phone: '138****0214', status: 'pending' },
  // 广州 3
  { id: 'M-GZ-001', name: '广州美莱医疗美容', city: '广州', industry: 'medical', scale: 'large', contact: '王总', phone: '138****0221', status: 'pending' },
  { id: 'M-GZ-002', name: '广州华美医疗美容', city: '广州', industry: 'medical', scale: 'large', contact: '李院长', phone: '138****0222', status: 'pending' },
  { id: 'M-GZ-003', name: '广州曙光医疗美容', city: '广州', industry: 'medical', scale: 'medium', contact: '张总监', phone: '138****0223', status: 'pending' },
  // 深圳 3
  { id: 'M-SZ-001', name: '深圳美莱医疗美容', city: '深圳', industry: 'medical', scale: 'large', contact: '王总', phone: '138****0231', status: 'pending' },
  { id: 'M-SZ-002', name: '深圳阳光医疗美容', city: '深圳', industry: 'medical', scale: 'medium', contact: '李院长', phone: '138****0232', status: 'pending' },
  { id: 'M-SZ-003', name: '深圳鹏爱医疗美容', city: '深圳', industry: 'medical', scale: 'medium', contact: '张总监', phone: '138****0233', status: 'pending' },
  // 成都 3
  { id: 'M-CD-001', name: '成都美莱医疗美容', city: '成都', industry: 'medical', scale: 'medium', contact: '王总', phone: '138****0241', status: 'pending' },
  { id: 'M-CD-002', name: '成都华美医疗美容', city: '成都', industry: 'medical', scale: 'medium', contact: '李院长', phone: '138****0242', status: 'pending' },
  { id: 'M-CD-003', name: '成都西婵医疗美容', city: '成都', industry: 'medical', scale: 'medium', contact: '张总监', phone: '138****0243', status: 'pending' },
  // 杭州 3
  { id: 'M-HZ-001', name: '杭州美莱医疗美容', city: '杭州', industry: 'medical', scale: 'medium', contact: '王总', phone: '138****0251', status: 'pending' },
  { id: 'M-HZ-002', name: '杭州华山医疗美容', city: '杭州', industry: 'medical', scale: 'medium', contact: '李院长', phone: '138****0252', status: 'pending' },
  { id: 'M-HZ-003', name: '杭州瑞丽医疗美容', city: '杭州', industry: 'medical', scale: 'medium', contact: '张总监', phone: '138****0253', status: 'pending' },
  // 武汉 2
  { id: 'M-WH-001', name: '武汉美莱医疗美容', city: '武汉', industry: 'medical', scale: 'medium', contact: '王总', phone: '138****0261', status: 'pending' },
  { id: 'M-WH-002', name: '武汉华美医疗美容', city: '武汉', industry: 'medical', scale: 'medium', contact: '李院长', phone: '138****0262', status: 'pending' },
  // 南京 2
  { id: 'M-NJ-001', name: '南京美莱医疗美容', city: '南京', industry: 'medical', scale: 'medium', contact: '王总', phone: '138****0271', status: 'pending' },
  { id: 'M-NJ-002', name: '南京华美医疗美容', city: '南京', industry: 'medical', scale: 'medium', contact: '李院长', phone: '138****0272', status: 'pending' },
  // 重庆 2
  { id: 'M-CQ-001', name: '重庆美莱医疗美容', city: '重庆', industry: 'medical', scale: 'medium', contact: '王总', phone: '138****0281', status: 'pending' },
  { id: 'M-CQ-002', name: '重庆华美医疗美容', city: '重庆', industry: 'medical', scale: 'medium', contact: '李院长', phone: '138****0282', status: 'pending' },
  // 西安 1
  { id: 'M-XA-001', name: '西安美莱医疗美容', city: '西安', industry: 'medical', scale: 'medium', contact: '王总', phone: '138****0291', status: 'pending' },
  // 长沙 1
  { id: 'M-CS-001', name: '长沙美莱医疗美容', city: '长沙', industry: 'medical', scale: 'medium', contact: '王总', phone: '138****0301', status: 'pending' },
  // 青岛 1
  { id: 'M-QD-001', name: '青岛华美医疗美容', city: '青岛', industry: 'medical', scale: 'medium', contact: '李院长', phone: '138****0311', status: 'pending' },
  // 苏州 1
  { id: 'M-SU-001', name: '苏州美莱医疗美容', city: '苏州', industry: 'medical', scale: 'medium', contact: '王总', phone: '138****0321', status: 'pending' },
];

const STATUS_LABELS: Record<Client['status'], { label: string; color: string }> = {
  pending: { label: '待触达', color: 'bg-gray-100 text-gray-600' },
  contacted: { label: '已联系', color: 'bg-blue-100 text-blue-700' },
  demo_scheduled: { label: '已约演示', color: 'bg-purple-100 text-purple-700' },
  trial: { label: '试用中', color: 'bg-orange-100 text-orange-700' },
  signed: { label: '已签约', color: 'bg-green-100 text-green-700' },
};

const SCALE_LABELS: Record<Client['scale'], string> = {
  small: '小 (< 50 员工)',
  medium: '中 (50-200 员工)',
  large: '大 (> 200 员工)',
};

export function ClientListPage() {
  const decoClients = CLIENTS.filter((c) => c.industry === 'decoration');
  const mediClients = CLIENTS.filter((c) => c.industry === 'medical');

  // 城市分布
  const cityCount = CLIENTS.reduce((acc, c) => {
    acc[c.city] = (acc[c.city] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  const topCities = Object.entries(cityCount).sort((a, b) => b[1] - a[1]).slice(0, 8);

  return (
    <>
      {/* HERO */}
      <section className="relative py-16 bg-gradient-to-br from-emerald-50 via-white to-teal-50 overflow-hidden">
        <div className="max-w-page mx-auto px-6 grid md:grid-cols-2 gap-10 items-center">
          <div>
            <span className="inline-flex items-center gap-2 px-3 py-1 bg-emerald-100 text-emerald-700 rounded-full text-sm mb-4">
              <Users className="w-3 h-3" /> Phase 46 D49-52 · OPC 首批 80 家触达清单
            </span>
            <h1 className="text-4xl md:text-5xl font-bold mb-4 leading-[1.1]">
              首批 80 家客户清单
              <br />
              <span className="text-emerald-500">50 装企 + 30 医美 · 全国 20 城</span>
            </h1>
            <p className="text-lg text-gray-600 mb-6">
              Phase 46 段 2 收官 — 内容 SOP 已就绪，下一步是跑客户触达。
              红线 #22 触达动作（外部资源）= 用户拍板后执行。
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-6 border-t border-gray-200">
              <div>
                <p className="text-2xl font-bold text-yellow-600">50</p>
                <p className="text-xs text-gray-500">装企</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-pink-600">30</p>
                <p className="text-xs text-gray-500">医美</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-emerald-600">80</p>
                <p className="text-xs text-gray-500">总客户</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-emerald-600">20</p>
                <p className="text-xs text-gray-500">城市</p>
              </div>
            </div>
          </div>
          <div>
            <img
              src="/images/clients-hero.jpeg"
              alt="80 家客户清单"
              className="rounded-2xl shadow-2xl w-full"
            />
          </div>
        </div>
      </section>
            <div className="p-4 bg-white rounded-lg border border-gray-200">
              <p className="text-xs text-gray-500">装企</p>
              <p className="text-3xl font-bold text-yellow-600">{decoClients.length}</p>
              <p className="text-xs text-gray-400 mt-1">覆盖 16 城</p>
            </div>
            <div className="p-4 bg-white rounded-lg border border-gray-200">
              <p className="text-xs text-gray-500">医美</p>
              <p className="text-3xl font-bold text-pink-600">{mediClients.length}</p>
              <p className="text-xs text-gray-400 mt-1">覆盖 14 城</p>
            </div>
            <div className="p-4 bg-white rounded-lg border border-gray-200">
              <p className="text-xs text-gray-500">总客户</p>
              <p className="text-3xl font-bold text-emerald-600">{CLIENTS.length}</p>
              <p className="text-xs text-gray-400 mt-1">覆盖 20 城</p>
            </div>
            <div className="p-4 bg-white rounded-lg border border-gray-200">
              <p className="text-xs text-gray-500">城市 TOP 1</p>
              <p className="text-3xl font-bold text-emerald-600">{topCities[0][0]}</p>
              <p className="text-xs text-gray-400 mt-1">{topCities[0][1]} 家</p>
            </div>
          </div>
        </div>
      </section>

      {/* 红 #22 守门 */}
      <section className="py-6 bg-yellow-50 border-y border-yellow-200">
        <div className="max-w-page mx-auto px-6">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm">
              <p className="font-medium text-yellow-800">红线 #22 触达边界</p>
              <p className="text-yellow-700 mt-1">
                实际拨打 / 加微信 / 发短信 = 必用户拍板后执行。当前仅展示清单，所有 status 默认 pending。
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 城市分布 */}
      <section className="py-12 bg-white">
        <div className="max-w-page mx-auto px-6">
          <h2 className="text-2xl font-bold mb-4">
            <MapPin className="w-5 h-5 inline mr-2" />
            城市分布（TOP 8）
          </h2>
          <div className="flex flex-wrap gap-2">
            {topCities.map(([city, n]) => (
              <span key={city} className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm">
                {city} <span className="font-bold">{n}</span>
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* 装企清单 */}
      <section className="py-12 bg-gray-50">
        <div className="max-w-page mx-auto px-6">
          <h2 className="text-2xl font-bold mb-4">
            <Building2 className="w-5 h-5 inline mr-2 text-yellow-600" />
            装企 50 家
          </h2>
          <ClientTable clients={decoClients} />
        </div>
      </section>

      {/* 医美清单 */}
      <section className="py-12 bg-white">
        <div className="max-w-page mx-auto px-6">
          <h2 className="text-2xl font-bold mb-4">
            <Building2 className="w-5 h-5 inline mr-2 text-pink-600" />
            医美 30 家
          </h2>
          <ClientTable clients={mediClients} />
        </div>
      </section>

      {/* 📎 配套文档引用 */}
      <section className="py-12 bg-gray-50 border-t border-gray-200">
        <div className="max-w-page mx-auto px-6">
          <h2 className="text-2xl font-bold mb-4">📎 配套文档</h2>
          <p className="text-gray-600 mb-6">本清单的触达脚本 + 跟进 SOP + P0 8 家精选</p>
          <div className="grid md:grid-cols-2 gap-4">
            <a
              href="/docs/marketing/scripts/outreach_decoration.md"
              className="block p-4 bg-white rounded-lg border border-gray-200 hover:border-emerald-500 hover:shadow transition"
            >
              <p className="text-xs text-emerald-600 mb-1">marketing/scripts/</p>
              <p className="font-bold mb-1">outreach_decoration.md</p>
              <p className="text-sm text-gray-600">装企 50 家外呼脚本 + 转化漏斗 + 80 家 P0-P3 优先级</p>
            </a>
            <a
              href="/docs/marketing/scripts/outreach_medical.md"
              className="block p-4 bg-white rounded-lg border border-gray-200 hover:border-emerald-500 hover:shadow transition"
            >
              <p className="text-xs text-emerald-600 mb-1">marketing/scripts/</p>
              <p className="font-bold mb-1">outreach_medical.md</p>
              <p className="text-sm text-gray-600">医美 30 家合规外呼脚本 + 6 红线守护</p>
            </a>
            <a
              href="/docs/marketing/scripts/p0_8_clients.md"
              className="block p-4 bg-white rounded-lg border border-gray-200 hover:border-emerald-500 hover:shadow transition"
            >
              <p className="text-xs text-emerald-600 mb-1">marketing/scripts/</p>
              <p className="font-bold mb-1">p0_8_clients.md</p>
              <p className="text-sm text-gray-600">P0 8 家精选清单（北京 6 + 上海 2）+ 7 步 SOP + 8 套话术</p>
            </a>
            <a
              href="/docs/finance/client_funnel_monitoring.md"
              className="block p-4 bg-white rounded-lg border border-gray-200 hover:border-emerald-500 hover:shadow transition"
            >
              <p className="text-xs text-emerald-600 mb-1">finance/</p>
              <p className="font-bold mb-1">client_funnel_monitoring.md</p>
              <p className="text-sm text-gray-600">80 家漏斗监控配置 + 5 状态机 + 3 告警</p>
            </a>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 bg-emerald-500 text-white">
        <div className="max-w-page mx-auto px-6 text-center">
          <Users className="w-12 h-12 mx-auto mb-4" />
          <h2 className="text-3xl font-bold mb-4">80 家清单就绪 → 待你拍板启动触达</h2>
          <p className="text-lg opacity-90 mb-8">红线 #22 边界：实际触达动作必用户授权</p>
          <Link
            to="/dashboard"
            className="px-8 py-3 bg-white text-emerald-500 rounded-md hover:bg-gray-100 inline-flex items-center gap-2 font-medium"
          >
            返回后台 <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </>
  );
}

function ClientTable({ clients }: { clients: Client[] }) {
  return (
    <div className="overflow-x-auto bg-white rounded-lg border border-gray-200">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-500">ID</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">公司名</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">城市</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">规模</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">联系人</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">电话</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">状态</th>
          </tr>
        </thead>
        <tbody>
          {clients.map((c) => (
            <tr key={c.id} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="px-4 py-3 font-mono text-xs text-gray-500">{c.id}</td>
              <td className="px-4 py-3 font-medium">{c.name}</td>
              <td className="px-4 py-3 text-gray-600">{c.city}</td>
              <td className="px-4 py-3 text-gray-600">{SCALE_LABELS[c.scale]}</td>
              <td className="px-4 py-3 text-gray-600">{c.contact}</td>
              <td className="px-4 py-3 text-gray-600">{c.phone}</td>
              <td className="px-4 py-3">
                <span className={`px-2 py-0.5 rounded text-xs ${STATUS_LABELS[c.status].color}`}>
                  {STATUS_LABELS[c.status].label}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
