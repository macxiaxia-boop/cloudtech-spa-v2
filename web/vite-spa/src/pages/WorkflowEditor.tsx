/**
 * CloudTech WorkflowEditor · V23 视觉重做 (2026-09-30)
 * 三栏布局：节点库 (200px) + Canvas (xyflow) + 节点配置面板 (320px) + shadcn Card
 */
import { useCallback, useState, useMemo } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  applyNodeChanges,
  type Node,
  type Edge,
  type NodeChange,
  type Connection,
  addEdge as rfAddEdge,
  Handle,
  Position,
  type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Save, Play, Settings, FileText, Bot, Database, GitBranch, Zap, ChevronRight, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useTranslation } from '@/i18n';

const nodeCategories = [
  {
    title: '触发', icon: Zap, color: 'text-success-600 bg-success-50',
    nodes: [{ id: 'start', label: '开始' }, { id: 'timer', label: '定时器' }, { id: 'webhook', label: 'Webhook' }],
  },
  {
    title: 'AI', icon: Bot, color: 'text-brand-600 bg-brand-50',
    nodes: [{ id: 'ai-chat', label: 'AI 对话' }, { id: 'ai-text', label: '文本生成' }, { id: 'ai-vision', label: '图像理解' }],
  },
  {
    title: '数据', icon: Database, color: 'text-accent-purple-600 bg-accent-purple-50',
    nodes: [{ id: 'http', label: 'HTTP 推流' }, { id: 'db', label: '数据库' }, { id: 'api', label: 'API 调用' }],
  },
  {
    title: '逻辑', icon: GitBranch, color: 'text-warning-600 bg-warning-50',
    nodes: [{ id: 'condition', label: '条件判断' }, { id: 'loop', label: '循环' }, { id: 'parallel', label: '并行' }],
  },
  {
    title: '操作', icon: Settings, color: 'text-muted-foreground bg-muted',
    nodes: [{ id: 'code', label: '代码执行' }, { id: 'file', label: '文件操作' }, { id: 'email', label: '邮件' }],
  },
];

const initialNodes: Node[] = [
  { id: '1', type: 'start', position: { x: 80, y: 200 }, data: { label: '开始' } },
  { id: '2', type: 'data', position: { x: 260, y: 200 }, data: { label: '数据处理', sub: 'Python 脚本' } },
  { id: '3', type: 'ai', position: { x: 460, y: 200 }, data: { label: 'AI 分析', sub: 'GPT-4o' } },
  { id: '4', type: 'output', position: { x: 660, y: 120 }, data: { label: '生成报告', sub: '文档输出' } },
  { id: '5', type: 'output', position: { x: 660, y: 280 }, data: { label: '发送通知', sub: '邮件+钉钉' } },
];

const initialEdges: Edge[] = [
  { id: 'e1-2', source: '1', target: '2' },
  { id: 'e2-3', source: '2', target: '3' },
  { id: 'e3-4', source: '3', target: '4' },
  { id: 'e3-5', source: '3', target: '5' },
];

function StartNode({ data }: NodeProps) {
  return (
    <div className="px-4 py-2 bg-success-500 text-white rounded-full shadow-md border-2 border-white flex items-center gap-2 min-w-[80px] justify-center">
      <div className="w-2 h-2 bg-white rounded-full" />
      <span className="text-sm font-medium">{(data as any).label}</span>
      <Handle type="source" position={Position.Right} className="!bg-success-600 !w-2 !h-2 !border-2 !border-white" />
    </div>
  );
}

function DataNode({ data, selected }: NodeProps) {
  return (
    <div className={`px-4 py-2 bg-card rounded-lg shadow-md border-2 ${selected ? 'border-accent-purple-500' : 'border-border'} min-w-[140px]`}>
      <Handle type="target" position={Position.Left} className="!bg-[var(--border-default)] !w-2 !h-2 !border-2 !border-white" />
      <div className="flex items-center gap-2">
        <div className="w-6 h-6 rounded bg-accent-purple-50 flex items-center justify-center">
          <Database className="w-3 h-3 text-accent-purple-600" />
        </div>
        <div>
          <div className="text-xs font-semibold text-foreground">{(data as any).label}</div>
          {(data as any).sub && <div className="text-[10px] text-muted-foreground">{(data as any).sub}</div>}
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="!bg-[var(--border-default)] !w-2 !h-2 !border-2 !border-white" />
    </div>
  );
}

function AINode({ data, selected }: NodeProps) {
  return (
    <div className={`px-4 py-2 bg-card rounded-lg shadow-md border-2 ${selected ? 'border-brand-500' : 'border-border'} min-w-[140px]`}>
      <Handle type="target" position={Position.Left} className="!bg-[var(--border-default)] !w-2 !h-2 !border-2 !border-white" />
      <div className="flex items-center gap-2">
        <div className="w-6 h-6 rounded bg-brand-50 flex items-center justify-center">
          <Bot className="w-3 h-3 text-brand-600" />
        </div>
        <div>
          <div className="text-xs font-semibold text-foreground">{(data as any).label}</div>
          {(data as any).sub && <div className="text-[10px] text-muted-foreground">{(data as any).sub}</div>}
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="!bg-[var(--border-default)] !w-2 !h-2 !border-2 !border-white" />
    </div>
  );
}

function OutputNode({ data, selected }: NodeProps) {
  return (
    <div className={`px-4 py-2 bg-card rounded-lg shadow-md border-2 ${selected ? 'border-warning-500' : 'border-border'} min-w-[140px]`}>
      <Handle type="target" position={Position.Left} className="!bg-[var(--border-default)] !w-2 !h-2 !border-2 !border-white" />
      <div className="flex items-center gap-2">
        <div className="w-6 h-6 rounded bg-warning-50 flex items-center justify-center">
          <FileText className="w-3 h-3 text-warning-600" />
        </div>
        <div>
          <div className="text-xs font-semibold text-foreground">{(data as any).label}</div>
          {(data as any).sub && <div className="text-[10px] text-muted-foreground">{(data as any).sub}</div>}
        </div>
      </div>
    </div>
  );
}

const nodeTypes = { start: StartNode, data: DataNode, ai: AINode, output: OutputNode };

export function WorkflowEditorPage() {
  const { t } = useTranslation();
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);
  const [selectedNode, setSelectedNode] = useState<string | null>('3');

  const onNodesChange = useCallback((changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)), []);
  const onConnect = useCallback((conn: Connection) => setEdges((eds) => rfAddEdge({ ...conn, animated: true, style: { stroke: '#2563EB', strokeWidth: 2 } }, eds)), []);

  const onNodeClick = useCallback((_: any, node: Node) => setSelectedNode(node.id), []);
  const onPaneClick = useCallback(() => setSelectedNode(null), []);

  const selected = useMemo(() => nodes.find((n) => n.id === selectedNode), [nodes, selectedNode]);

  return (
    <div className="-m-4 h-[calc(100vh-56px)] flex flex-col">
      {/* Toolbar */}
      <div className="h-12 border-b border-border bg-card flex items-center px-4 gap-3">
        <Input defaultValue="市场分析工作流" className="w-64 h-8 text-sm" />
        <span className="text-xs text-muted-foreground">未保存</span>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="ghost" size="sm"><Play className="w-3.5 h-3.5" />{t('common.confirm')}</Button>
          <Button variant="outline" size="sm">调试</Button>
          <Button size="sm"><Save className="w-3.5 h-3.5" />{t('common.save')}</Button>
        </div>
      </div>

      <div className="flex-1 flex min-h-0">
        {/* 左侧节点库 */}
        <aside className="w-52 border-r border-border bg-card overflow-y-auto p-3 space-y-4">
          {nodeCategories.map((cat) => {
            const Icon = cat.icon;
            return (
              <div key={cat.title}>
                <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground mb-2">
                  <Icon className="w-3.5 h-3.5" />
                  {cat.title}
                </div>
                <div className="space-y-1">
                  {cat.nodes.map((n) => (
                    <button
                      key={n.id}
                      draggable
                      onDragStart={(e) => e.dataTransfer.setData('application/reactflow', n.id)}
                      className={`w-full flex items-center gap-2 px-2 py-1.5 rounded text-xs border ${cat.color} hover:opacity-80 cursor-grab`}
                    >
                      {n.label}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </aside>

        {/* 中间 Canvas */}
        <div className="flex-1 bg-[var(--neutral-50)]">
          <ReactFlowProvider>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onConnect={onConnect}
              onNodeClick={onNodeClick}
              onPaneClick={onPaneClick}
              nodeTypes={nodeTypes}
              fitView
              attributionPosition="bottom-left"
              defaultEdgeOptions={{ style: { stroke: '#94A3B8', strokeWidth: 2 } }}
            >
              <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#CBD5E1" />
              <Controls className="!shadow-md" />
              <MiniMap className="!shadow-md" maskColor="rgba(241,245,249,0.6)" pannable zoomable />
            </ReactFlow>
          </ReactFlowProvider>
        </div>

        {/* 右侧节点配置 */}
        <aside className="w-80 border-l border-border bg-card overflow-y-auto">
      <Card className="p-0">
          <CardContent className="p-0">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <Settings className="w-4 h-4" />
              节点配置
            </h3>
            {selectedNode && (
              <button onClick={() => setSelectedNode(null)} className="p-1 hover:bg-muted rounded">
                <X className="w-3.5 h-3.5 text-muted-foreground" />
              </button>
            )}
          </div>
          {!selected ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              <p>选中节点查看配置</p>
            </div>
          ) : (
            <div className="p-4 space-y-4">
              <div className="flex items-center gap-2 pb-3 border-b border-border">
                <span className="text-xs px-2 py-0.5 rounded-full bg-brand-50 text-brand-700 font-medium">
                  {(selected.data as any).label}
                </span>
                <span className="text-xs text-muted-foreground">节点 ID: {selected.id}</span>
              </div>
              <div className="space-y-1.5">
                <Label>节点名称</Label>
                <Input defaultValue={(selected.data as any).label} />
              </div>
              <div className="space-y-1.5">
                <Label>模型</Label>
                <select className="w-full h-9 rounded-md border border-border bg-card px-3 text-sm focus:outline-none focus:border-brand-600">
                  <option>GPT-4o</option>
                  <option>Claude 3.5</option>
                  <option>Gemini 1.5</option>
                  <option>DeepSeek</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <Label>预设备（系统提示）</Label>
                <textarea
                  defaultValue="你是一个专业的数据分析师，能够从数据中提取有价值的洞察，并生成清晰的报告。"
                  rows={4}
                  className="w-full rounded-md border border-border bg-card px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:border-brand-600 focus:ring-3 focus:ring-brand-500/20"
                />
              </div>
              <div className="space-y-1.5">
                <Label>输入变量</Label>
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-xs font-mono p-2 bg-muted rounded">
                    <ChevronRight className="w-3 h-3 text-muted-foreground" />
                    market_data
                  </div>
                  <div className="flex items-center gap-2 text-xs font-mono p-2 bg-muted rounded">
                    <ChevronRight className="w-3 h-3 text-muted-foreground" />
                    analysis_type
                  </div>
                </div>
              </div>
              <div className="space-y-1.5">
                <Label>输出变量</Label>
                <div className="flex items-center gap-2 text-xs font-mono p-2 bg-muted rounded">
                  <ChevronRight className="w-3 h-3 text-muted-foreground" />
                  analysis_result
                </div>
              </div>
              <Button className="w-full">保存节点配置</Button>
            </div>
          )}
          </CardContent>
        </Card>
        </aside>
      </div>
    </div>
  );
}
