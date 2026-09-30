/**
 * CloudTech ErrorBoundary · 全局错误捕获
 *
 * 防止单个组件抛错导致整个应用崩溃
 * 提供友好的"出错了"页面 + 重试按钮
 */
import { Component, type ReactNode, type ErrorInfo } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
  fallbackMessage?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // P1+ 接入 Sentry / LogRocket
    if (import.meta.env.DEV) {
      console.error('[ErrorBoundary]', error, info);
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  handleHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center p-6 bg-muted">
          <div className="max-w-md text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-destructive-bg flex items-center justify-center">
              <AlertTriangle className="w-8 h-8 text-destructive-600" />
            </div>
            <h1 className="text-2xl font-bold mb-2">{this.props.fallbackTitle || '出错了'}</h1>
            <p className="text-sm text-muted-foreground mb-6">
              {this.props.fallbackMessage || '页面遇到了一个意外错误。请重试或返回首页。'}
            </p>
            {import.meta.env.DEV && this.state.error && (
              <pre className="text-left text-xs bg-destructive-bg/30 border border-destructive-200 rounded p-3 mb-4 overflow-auto max-h-40 font-mono">
                {this.state.error.message}
              </pre>
            )}
            <div className="flex items-center justify-center gap-3">
              <Button variant="outline" onClick={this.handleReset}>
                <RefreshCw className="w-4 h-4" />
                重试
              </Button>
              <Button onClick={this.handleHome}>
                <Home className="w-4 h-4" />
                返回首页
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
