/**
 * CloudTech Files · v3 视觉母版 11 模块
 * 网格视图 + 文件类型筛选 + 缩略图 + i18n
 */
import { useState } from 'react';
import { Plus, Search, Grid3x3, List, MoreHorizontal, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useTranslation } from '@/i18n';

type View = 'grid' | 'list';
type Tab = 'all' | 'image' | 'doc' | 'video' | 'other';

interface FileItem {
  id: string;
  name: string;
  type: string;
  typeLabel: string;
  bgColor: string;
  size: string;
  modifiedAt: string;
}

const items: FileItem[] = [
  { id: 'f1', name: '产品主视觉图.png', type: 'image', typeLabel: 'PNG', bgColor: 'bg-gradient-to-br from-blue-100 to-indigo-100', size: '2.4 MB', modifiedAt: '2天前' },
  { id: 'f2', name: '市场调研报告.pdf', type: 'doc', typeLabel: 'PDF', bgColor: 'bg-gradient-to-br from-red-100 to-orange-100', size: '5.1 MB', modifiedAt: '2天前' },
  { id: 'f3', name: '竞品资料', type: 'doc', typeLabel: 'ZIP', bgColor: 'bg-gradient-to-br from-gray-100 to-slate-200', size: '12.3 MB', modifiedAt: '5天前' },
  { id: 'f4', name: '产品介绍.pptx', type: 'doc', typeLabel: 'PPTX', bgColor: 'bg-gradient-to-br from-orange-100 to-amber-100', size: '8.4 MB', modifiedAt: '1周前' },
  { id: 'f5', name: '宣传片.mp4', type: 'video', typeLabel: 'MP4', bgColor: 'bg-gradient-to-br from-purple-100 to-pink-100', size: '142 MB', modifiedAt: '1周前' },
  { id: 'f6', name: 'logo.svg', type: 'image', typeLabel: 'SVG', bgColor: 'bg-gradient-to-br from-cyan-100 to-blue-100', size: '24 KB', modifiedAt: '2周前' },
  { id: 'f7', name: '用户访谈录音.mp3', type: 'other', typeLabel: 'MP3', bgColor: 'bg-gradient-to-br from-emerald-100 to-teal-100', size: '46 MB', modifiedAt: '2周前' },
  { id: 'f8', name: '运营数据.xlsx', type: 'doc', typeLabel: 'XLSX', bgColor: 'bg-gradient-to-br from-green-100 to-emerald-100', size: '1.2 MB', modifiedAt: '3周前' },
];

const tabs: { key: Tab; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'image', label: '图片' },
  { key: 'doc', label: '文档' },
  { key: 'video', label: '视频' },
  { key: 'other', label: '其他' },
];

export function FilesPage() {
  const [view, setView] = useState<View>('grid');
  const [tab, setTab] = useState<Tab>('all');
  const [query, setQuery] = useState('');
  const { t } = useTranslation();

  const filtered = tab === 'all' ? items : items.filter((i) => i.type === tab);

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">{t('nav.files')}</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">网格视图 · 类型筛选 · 多格式支持</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex border border-[var(--border-default)] rounded-md overflow-hidden">
            <button onClick={() => setView('grid')} className={`p-2 ${view === 'grid' ? 'bg-brand-50 text-brand-600' : 'text-[var(--text-secondary)] hover:bg-[var(--surface-muted)]'}`} aria-label="网格视图"><Grid3x3 className="w-4 h-4" /></button>
            <button onClick={() => setView('list')} className={`p-2 border-l border-[var(--border-default)] ${view === 'list' ? 'bg-brand-50 text-brand-600' : 'text-[var(--text-secondary)] hover:bg-[var(--surface-muted)]'}`} aria-label="列表视图"><List className="w-4 h-4" /></button>
          </div>
          <Button size="sm"><Plus className="w-4 h-4" />{t('app.upload_file')}</Button>
        </div>
      </div>

      <div className="bg-[var(--surface-base)] rounded-lg border border-[var(--border-default)]">
        <div className="p-4 border-b border-[var(--border-default)] flex items-center gap-3 flex-wrap">
          <nav className="flex gap-1 mr-auto">
            {tabs.map((t) => (
              <button key={t.key} onClick={() => setTab(t.key)}
                className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
                  tab === t.key ? 'bg-brand-50 text-brand-700 font-medium' : 'text-[var(--text-secondary)] hover:bg-[var(--surface-muted)]'
                }`}>{t.label}</button>
            ))}
          </nav>
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-tertiary)] pointer-events-none" />
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索文件…" className="pl-10 h-9" />
          </div>
        </div>

        {view === 'grid' ? (
          <div className="p-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {filtered.map((item) => (
              <div key={item.id} className="group relative bg-[var(--surface-base)] rounded-lg border border-[var(--border-default)] overflow-hidden hover:shadow-md hover:border-brand-300 transition-all cursor-pointer">
                <div className={`aspect-square ${item.bgColor} flex items-center justify-center`}>
                  <span className="text-2xl font-bold text-white/80 drop-shadow">{item.typeLabel}</span>
                </div>
                <div className="p-2.5">
                  <div className="text-sm font-medium truncate text-[var(--text-primary)]">{item.name}</div>
                  <div className="text-[11px] text-[var(--text-tertiary)] mt-0.5">{item.size} · {item.modifiedAt}</div>
                </div>
                <button className="absolute top-2 right-2 p-1 rounded bg-white/80 backdrop-blur opacity-0 group-hover:opacity-100 transition-opacity">
                  <MoreHorizontal className="w-4 h-4 text-[var(--text-secondary)]" />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="bg-[var(--surface-subtle)] border-b border-[var(--border-default)]">
                <th className="text-left text-xs font-medium text-[var(--text-secondary)] px-4 py-2.5">名称</th>
                <th className="text-left text-xs font-medium text-[var(--text-secondary)] px-4 py-2.5 w-24">大小</th>
                <th className="text-left text-xs font-medium text-[var(--text-secondary)] px-4 py-2.5 w-24">修改</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={item.id} className="border-b border-[var(--border-default)] hover:bg-[var(--surface-subtle)]">
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-[var(--text-tertiary)]" />
                      <span className="text-sm">{item.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-xs text-[var(--text-secondary)]">{item.size}</td>
                  <td className="px-4 py-2.5 text-xs text-[var(--text-tertiary)]">{item.modifiedAt}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
