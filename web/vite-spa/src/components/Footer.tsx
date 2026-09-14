// 页脚 · 5 列 + Logo + 备案 + 版权
import { Link } from 'react-router-dom';
import { Sparkles } from 'lucide-react';

export function Footer() {
  return (
    <footer className="border-t border-gray-200 bg-gray-50 mt-20">
      <div className="max-w-page mx-auto px-6 py-12">
        <div className="grid md:grid-cols-5 gap-8">
          {/* Logo + 简介 */}
          <div className="md:col-span-2">
            <Link to="/" className="flex items-center gap-2 text-xl font-bold text-brand-500 mb-3">
              <Sparkles className="w-5 h-5" />
              CloudTech · AI 数字员工
            </Link>
            <p className="text-sm text-gray-600 mb-4">
              1 人 + AI 的整家公司 SaaS
              <br />
              OPC 模式开创者 · 灵策智算出品
            </p>
            <div className="flex gap-3 text-sm">
              <a href="#" className="text-gray-500 hover:text-brand-500">
                微信公众号
              </a>
              <span className="text-gray-300">·</span>
              <a href="#" className="text-gray-500 hover:text-brand-500">
                视频号
              </a>
              <span className="text-gray-300">·</span>
              <a href="#" className="text-gray-500 hover:text-brand-500">
                小红书
              </a>
              <span className="text-gray-300">·</span>
              <a href="#" className="text-gray-500 hover:text-brand-500">
                抖音
              </a>
            </div>
          </div>

          {/* 产品 */}
          <div>
            <h4 className="font-bold mb-3 text-sm">产品</h4>
            <ul className="space-y-2 text-sm text-gray-600">
              <li><Link to="/employees" className="hover:text-brand-500">5 AI 数字员工</Link></li>
              <li><Link to="/monitoring" className="hover:text-brand-500">监控中心</Link></li>
              <li><Link to="/clients" className="hover:text-brand-500">80 家客户清单</Link></li>
              <li><Link to="/documents" className="hover:text-brand-500">公司文档</Link></li>
              <li><Link to="/try" className="hover:text-brand-500">7 天免费试用</Link></li>
            </ul>
          </div>

          {/* 行业 */}
          <div>
            <h4 className="font-bold mb-3 text-sm">行业</h4>
            <ul className="space-y-2 text-sm text-gray-600">
              <li><Link to="/industries/decoration" className="hover:text-brand-500">装企获客</Link></li>
              <li><Link to="/industries/medical" className="hover:text-brand-500">医美合规</Link></li>
              <li><Link to="/content-sop" className="hover:text-brand-500">内容 SOP</Link></li>
            </ul>
          </div>

          {/* 资源 + 关于 */}
          <div>
            <h4 className="font-bold mb-3 text-sm">资源</h4>
            <ul className="space-y-2 text-sm text-gray-600 mb-4">
              <li><Link to="/cases" className="hover:text-brand-500">案例库</Link></li>
              <li><Link to="/blog" className="hover:text-brand-500">博客</Link></li>
              <li><Link to="/faq" className="hover:text-brand-500">FAQ</Link></li>
              <li><Link to="/opc-story" className="hover:text-brand-500">OPC 故事</Link></li>
            </ul>
            <h4 className="font-bold mb-3 text-sm">关于</h4>
            <ul className="space-y-2 text-sm text-gray-600">
              <li><Link to="/pricing" className="hover:text-brand-500">定价</Link></li>
              <li><Link to="/contact" className="hover:text-brand-500">联系</Link></li>
              <li><Link to="/terms" className="hover:text-brand-500">服务条款</Link></li>
              <li><Link to="/privacy" className="hover:text-brand-500">隐私政策</Link></li>
            </ul>
          </div>
        </div>

        {/* 版权 + 备案 */}
        <div className="border-t border-gray-200 mt-8 pt-6 flex flex-col md:flex-row items-center justify-between gap-3 text-xs text-gray-500">
          <p>© 2026 灵策智算 · CloudTech SaaS · 1 人 + AI 跑出 OPC 实证</p>
          <div className="flex gap-4">
            <span>京 ICP 备 XXXXXX 号</span>
            <span>京公网安备 XXXXXX 号</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
