/**
 * CloudTech Knowledge · V23 视觉重做 (2026-09-30)
 * 文档检索 · 向量检索 · 多模态解析 · 权限控制 + shadcn Card + Table + i18n
 *
 * V23: bg-[var(--xxx)] 硬编码 → 标准 token · table → shadcn Table
 */
import { useState } from 'react';
import { Search, Plus, FileText, MoreHorizontal, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardAction } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { useTranslation } from '@/i18n';

type Tab = 'all' | 'docs' | 'db' | 'web' | 'team';

interface KnowledgeFile {
  id: string;
  name: string;
  type: string;
  typeColor: string;
  size: string;
  modifiedAt: string;
  owner: string;
}

const files: KnowledgeFile[] = [
  { id: 'f1', name: '产品需求文档 v2.0', type: 'PDF', typeColor: 'bg-destructive-50 text-destructive-700', size: '4.2 MB', modifiedAt: '3月5日', owner: '张三' },
  { id: 'f2', name: '市场研究报告', type: 'PPTX', typeColor: 'bg-warning-50 text-warning-700', size: '12.8 MB', modifiedAt: '3月6日', owner: '李四' },
  { id: 'f3', name: '用户调研报告', type: 'XLSX', typeColor: 'bg-success-50 text-success-700', size: '2.1 MB', modifiedAt: '3月4日', owner: '李四' },
  { id: 'f4', name: '竞品分析.xlsx', type: 'XLSX', typeColor: 'bg-success-50 text-success-700', size: '869 KB', modifiedAt: '3月8日', owner: '王五' },
  { id: 'f5', name: '产品架构文档', type: 'MD', typeColor: 'bg-brand-50 text-brand-700', size: '256 KB', modifiedAt: '3月9日', owner: '张三' },
  { id: 'f6', name: 'API 接口文档', type: 'PDF', typeColor: 'bg-destructive-50 text-destructive-700', size: '4.11 MB', modifiedAt: '3月10日', owner: '张三' },
  { id: 'f7', name: '项目会议记录', type: 'DOCX', typeColor: 'bg-accent-purple-50 text-accent-purple-700', size: '0.8 MB', modifiedAt: '3月9日', owner: '赵六' },
];

const tabs: { key: Tab; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'docs', label: '文档' },
  { key: 'db', label: '数据库' },
  { key: 'web', label: '网页链接' },
  { key: 'team', label: '团队知识库' },
];

export function KnowledgePage() {
  const [tab, setTab] = useState<Tab>('all');
  const [query, setQuery] = useState('');
  const { t } = useTranslation();

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">{t('nav.knowledge')}</h1>
        <p className="text-sm text-muted-foreground mt-1">文档检索 · 向量检索 · 多模态解析 · 权限控制</p>
      </div>

      <Card className="p-0">
        <div className="p-4 border-b border-border flex items-center gap-3 flex-wrap">
          <nav className="flex gap-1 mr-auto">
            {tabs.map((t) => (
              <button key={t.key} onClick={() => setTab(t.key)}
                className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
                  tab === t.key ? 'bg-brand-50 text-brand-700 font-medium' : 'text-muted-foreground hover:bg-muted'
                }`}>{t.label}</button>
            ))}
          </nav>
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索文件…" className="pl-10 h-9" />
          </div>
          <Button size="sm"><Plus className="w-4 h-4" />{t('app.upload_doc')}</Button>
        </div>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10"><input type="checkbox" className="rounded" /></TableHead>
              <TableHead>名称</TableHead>
              <TableHead className="w-24">类型</TableHead>
              <TableHead className="w-24">大小</TableHead>
              <TableHead className="w-24">修改时间</TableHead>
              <TableHead className="w-24">创建人</TableHead>
              <TableHead className="w-12 text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {files.map((f) => (
              <TableRow key={f.id}>
                <TableCell><input type="checkbox" className="rounded" /></TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Badge className={`w-12 justify-center ${f.typeColor}`}>{f.type}</Badge>
                    <span className="text-sm font-medium text-foreground">{f.name}</span>
                  </div>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">{f.type}</TableCell>
                <TableCell className="text-xs text-muted-foreground">{f.size}</TableCell>
                <TableCell className="text-xs text-muted-foreground">{f.modifiedAt}</TableCell>
                <TableCell className="text-xs text-muted-foreground">{f.owner}</TableCell>
                <TableCell className="text-right">
                  <button className="p-1 hover:bg-muted rounded"><MoreHorizontal className="w-4 h-4 text-muted-foreground" /></button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      <Card className="bg-brand-50 border-brand-200 p-0">
        <CardContent className="p-4 flex items-start gap-3">
          <Upload className="w-5 h-5 text-brand-600 shrink-0 mt-0.5" />
          <div className="text-sm">
            <div className="font-medium text-brand-700">支持多模态解析</div>
            <div className="text-brand-700 mt-1">上传 PDF/Word/PPT/Excel/Markdown 后，自动解析文本 + 图片 OCR + 表格结构，构建向量索引供智能体检索。</div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
