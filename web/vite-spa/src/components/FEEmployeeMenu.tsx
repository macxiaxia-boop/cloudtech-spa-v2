// Phase 45 D4-7 + D17-23: 前台 3 员工菜单收敛组件
// 数据源：v3_3_employees_routes.FRONTEND_EMPLOYEES
//   - content_writer
//   - customer_service
//   - market_researcher
import { Link } from 'react-router-dom';
import { useState } from 'react';
import { ChevronDown, Bot } from 'lucide-react';

const FE_EMPLOYEES = [
  { id: 'content_writer', name: '内容创作', desc: 'AI 写公众号 / 小红书 / 抖音脚本' },
  { id: 'customer_service', name: '智能客服', desc: '7×24 自动应答 + 工单分流' },
  { id: 'market_researcher', name: '市场调研', desc: '竞品监控 + 行业趋势报告' },
];

export function FEEmployeeMenu() {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative" onMouseLeave={() => setOpen(false)}>
      <button
        onMouseEnter={() => setOpen(true)}
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 hover:text-brand-500"
      >
        <Bot className="w-4 h-4" />
        数字员工 <ChevronDown className="w-3 h-3" />
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-2 w-72 bg-card border border-gray-200 rounded-lg shadow-lg z-10">
          <div className="p-3 border-b border-gray-100">
            <p className="text-xs text-gray-500">前台员工 · Phase 45 D4-7 收敛</p>
            <p className="text-xs text-gray-400 mt-1">后端 5 员工（short_video_script / data_analyst / seo_specialist / social_media_manager / growth_hacker）暂不在前台菜单</p>
          </div>
          {FE_EMPLOYEES.map((emp) => (
            <Link
              key={emp.id}
              to={`/employees/${emp.id}`}
              className="block p-3 hover:bg-gray-50 border-b border-gray-50 last:border-0"
              onClick={() => setOpen(false)}
            >
              <p className="text-sm font-medium">{emp.name}</p>
              <p className="text-xs text-gray-500">{emp.desc}</p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
