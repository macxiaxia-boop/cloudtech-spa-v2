/**
 * CloudTech Theme Settings
 * 来源：ant-design/ant-design-pro config/defaultSettings.ts 借鉴思想（不复制代码）
 * 用途：navTheme / layout / colorPrimary 等运行时主题设置（CloudTech 自实现）
 */

export type NavTheme = 'light' | 'dark';

export interface ThemeSettings {
  navTheme: NavTheme;
  colorPrimary: string;
  layout: 'mix' | 'side' | 'top';
  contentWidth: 'Fluid' | 'Fixed';
  fixedHeader: boolean;
  fixSiderbar: boolean;
  colorWeak: boolean;
  title: string;
}

const Settings: ThemeSettings = {
  navTheme: 'light',
  colorPrimary: '#2563EB',  // v2 视觉母版实测
  layout: 'mix',
  contentWidth: 'Fluid',
  fixedHeader: false,
  fixSiderbar: true,
  colorWeak: false,
  title: 'CloudTech · 企业级 AI 工作空间',
};

export default Settings;
