/**
 * CloudTech Chat · v3 视觉母版 05 模块
 * 三栏布局：会话列表（240px）+ 消息流（flex-1）+ 模型选择（320px 折叠面板）
 */
import { useState } from 'react';
import { Plus, Send, Paperclip, Settings2, BarChart3, Bot, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

interface Session {
  id: string;
  title: string;
  model: string;
  updatedAt: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  chart?: { type: 'line'; label: string; value: string; change: string };
  time: string;
}

const sessions: Session[] = [
  { id: 's1', title: '产品价值分析', model: 'GPT-4o', updatedAt: '昨天 9:42' },
  { id: 's2', title: '客户访谈视频转表格', model: 'GPT-4o', updatedAt: '昨天 10:31' },
  { id: 's3', title: '需求文档撰写', model: 'Claude 3.5', updatedAt: '3月10日' },
  { id: 's4', title: '数据探索分析', model: 'GPT-4o', updatedAt: '3月10日' },
  { id: 's5', title: '合同摘要提取', model: 'Claude 3.5', updatedAt: '3月9日' },
];

const initialMessages: Message[] = [
  { id: 'm1', role: 'assistant', content: '你好！我是 Cloud 的 AI 助手。今天有什么可以帮你？', time: '10:31' },
  {
    id: 'm2', role: 'user',
    content: '分析最近 3 个月的用户增长情况，并生成图表。',
    time: '10:32',
  },
  {
    id: 'm3', role: 'assistant',
    content: '基于最近 3 个月的用户增长数据，主要变化如下：\n\n1. 产品功能优化\n2. 市场推广活动\n3. 用户口碑传播',
    chart: { type: 'line', label: '用户增长分析', value: '32,480', change: '+32%' },
    time: '10:33',
  },
];

export function ChatPage() {
  const [model, setModel] = useState('GPT-4o');
  const [input, setInput] = useState('');
  const [messages] = useState<Message[]>(initialMessages);

  function handleSend() {
    if (!input.trim()) return;
    setInput('');
    // P1+ 阶段接入真实流式响应（SSE/WebSocket）
  }

  return (
    <div className="flex h-[calc(100vh-56px)] -m-4">
      {/* 左侧：会话列表 */}
      <aside className="w-60 border-r border-border bg-card flex flex-col">
        <div className="p-3 border-b border-border">
          <Button className="w-full" size="sm">
            <Plus className="w-4 h-4" />
            新建对话
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {sessions.map((s) => (
            <button
              key={s.id}
              className="w-full text-left px-3 py-2 rounded-md text-sm hover:bg-muted transition-colors"
            >
              <div className="font-medium truncate text-foreground">{s.title}</div>
              <div className="text-xs text-muted-foreground mt-0.5">{s.updatedAt}</div>
            </button>
          ))}
        </div>
      </aside>

      {/* 中间：消息流 */}
      <div className="flex-1 flex flex-col bg-card min-w-0">
        {/* 顶栏：模型选择 */}
        <div className="h-12 border-b border-border flex items-center justify-between px-4">
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="text-sm font-medium bg-transparent border-0 focus:outline-none cursor-pointer"
          >
            <option>GPT-4o</option>
            <option>Claude 3.5</option>
            <option>Gemini 1.5</option>
            <option>DeepSeek</option>
            <option>智谱 GLM-4</option>
          </select>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>会话时间线</span>
            <button className="p-1 hover:bg-muted rounded"><Settings2 className="w-4 h-4" /></button>
          </div>
        </div>

        {/* 消息流 */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-brand-100 flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4 text-brand-600" />
                </div>
              )}
              <div className={`max-w-2xl ${msg.role === 'user' ? 'order-1' : ''}`}>
                <div
                  className={`rounded-xl px-4 py-3 text-sm ${
                    msg.role === 'user'
                      ? 'bg-brand-600 text-white'
                      : 'bg-muted text-foreground'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  {msg.chart && (
                    <div className="mt-3 p-3 bg-card rounded-lg border border-border">
                      <div className="flex items-center gap-2 mb-2">
                        <BarChart3 className="w-4 h-4 text-brand-600" />
                        <span className="font-medium text-sm">{msg.chart.label}</span>
                      </div>
                      <div className="flex items-end justify-between">
                        <div>
                          <div className="text-2xl font-bold text-foreground">{msg.chart.value}</div>
                          <div className="text-xs text-muted-foreground">活跃用户</div>
                        </div>
                        <div className="text-success-600 text-sm font-medium">{msg.chart.change}</div>
                      </div>
                    </div>
                  )}
                </div>
                <div className="text-xs text-muted-foreground mt-1 px-1">{msg.time}</div>
              </div>
              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-[var(--neutral-200)] flex items-center justify-center shrink-0">
                  <User className="w-4 h-4 text-muted-foreground" />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* 输入区 */}
        <div className="border-t border-border p-4">
          <div className="flex items-end gap-2 max-w-4xl mx-auto">
            <Button variant="ghost" size="icon" className="shrink-0">
              <Paperclip className="w-4 h-4" />
            </Button>
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="发送消息，输入 / 使用工具…"
              className="min-h-[44px] max-h-32 resize-none"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
            />
            <Button size="icon" onClick={handleSend} disabled={!input.trim()} className="shrink-0">
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* 右侧：模型/工具面板（折叠态） */}
      <aside className="hidden xl:flex w-80 border-l border-border bg-card flex-col">
        <div className="p-4 border-b border-border">
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <Settings2 className="w-4 h-4" />
            模型配置
          </h3>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4 text-sm">
          <div>
            <div className="text-xs text-muted-foreground mb-1.5">当前模型</div>
            <select className="w-full h-9 rounded-md border border-border bg-card px-3 text-sm focus:outline-none focus:border-brand-600">
              <option>{model}</option>
              <option>Claude 3.5</option>
              <option>GPT-4o</option>
            </select>
          </div>
          <div>
            <div className="text-xs text-muted-foreground mb-1.5">温度</div>
            <input type="range" min="0" max="2" step="0.1" defaultValue="0.7" className="w-full" />
            <div className="flex justify-between text-xs text-muted-foreground mt-1">
              <span>精确</span>
              <span>0.7</span>
              <span>创造</span>
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground mb-1.5">系统提示</div>
            <Textarea placeholder="你是一个专业的 AI 助手…" className="min-h-[100px] text-sm" />
          </div>
          <div>
            <div className="text-xs text-muted-foreground mb-1.5">可用工具</div>
            <div className="flex flex-wrap gap-1.5">
              {['联网搜索', '数据分析', '文档检索', '代码执行', '图像理解'].map((t) => (
                <span key={t} className="text-xs px-2 py-1 rounded-full bg-muted text-muted-foreground">{t}</span>
              ))}
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}
