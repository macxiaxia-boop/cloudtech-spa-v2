// R368 · vite-spa 工作台 page dark mode 截图 · 绕过 RequireAuth · puppeteer-core + msedge
// 治本 R367 全局 ThemeInitializer · 验证 7 工作台 page dark 真生效
const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');
const os = require('os');

const OUT_DIR = path.join(os.tmpdir(), 'v23_shots');
try { fs.mkdirSync(OUT_DIR, { recursive: true }); } catch {}

const TESTS = [
  // 工作台 routes (R368 验证 · 绕过 RequireAuth 用 localStorage fake token)
  { name: 'dashboard',   url: 'http://127.0.0.1:7792/dashboard' },
  { name: 'tasks',       url: 'http://127.0.0.1:7792/tasks' },
  { name: 'monitoring',  url: 'http://127.0.0.1:7792/monitoring' },
  { name: 'analytics',   url: 'http://127.0.0.1:7792/analytics' },
  { name: 'ai-employees',url: 'http://127.0.0.1:7792/employees' },
  { name: 'settings',    url: 'http://127.0.0.1:7792/settings' },
  { name: 'profile',     url: 'http://127.0.0.1:7792/profile' },
];

const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';

// Auth bypass: 模拟登录态 (AuthContext 读 ct.auth.user JSON · R368 治本)
const AUTH_FAKE = {
  'ct.auth.user': JSON.stringify({
    id: 'u_mock001',
    email: 'r368@cloudtech.com',
    name: 'R368 测试',
    role: 'owner',
    tenant_id: 't_mock001',
    tenant_name: 'R368 测试',
  }),
  'ct.auth.workspace': JSON.stringify({
    id: 't_mock001',
    name: 'R368 测试',
    role: 'owner',
  }),
  ct_token:        'fake_token_r368_bypass',
  ct_user_id:      'u_mock001',
  ct_tenant_id:    't_mock001',
  ct_tenant_name:  'R368 测试',
  ct_industry:     'decoration',
  ct_sku_id:       'dec_pro',
  ct_trial:        'true',
  cloudtech_onboarding_done: 'true',
};

(async () => {
  const browser = await puppeteer.launch({
    executablePath: EDGE,
    headless: 'new',
    args: ['--no-sandbox', '--disable-gpu', '--hide-scrollbars'],
    defaultViewport: { width: 1440, height: 900 },
  });

  try {
    for (const test of TESTS) {
      const page = await browser.newPage();

      // 先访问一次设 auth localStorage (避免 RequireAuth redirect 到 /login)
      await page.goto('http://127.0.0.1:7792/', { waitUntil: 'networkidle2', timeout: 15000 });
      await page.evaluate((auth) => {
        for (const [k, v] of Object.entries(auth)) {
          localStorage.setItem(k, v);
        }
      }, AUTH_FAKE);

      // 浅色截图
      await page.evaluate(() => localStorage.setItem('ct.theme', 'light'));
      await page.evaluate(() => document.documentElement.classList.remove('dark'));
      await page.goto(test.url, { waitUntil: 'networkidle2', timeout: 15000 });
      await new Promise(r => setTimeout(r, 1500));
      const lightPath = path.join(OUT_DIR, `r368_${test.name}_light.png`);
      await page.screenshot({ path: lightPath });
      console.log(`✅ ${test.name} light: ${lightPath}`);

      // 深色截图
      await page.evaluate(() => localStorage.setItem('ct.theme', 'dark'));
      await page.evaluate(() => document.documentElement.classList.add('dark'));
      await page.reload({ waitUntil: 'networkidle2' });
      await new Promise(r => setTimeout(r, 1500));
      const darkPath = path.join(OUT_DIR, `r368_${test.name}_dark.png`);
      await page.screenshot({ path: darkPath });
      const cls = await page.evaluate(() => document.documentElement.className);
      console.log(`✅ ${test.name} dark: ${darkPath} · className=${cls}`);

      await page.close();
    }
  } catch (e) {
    console.error('ERROR:', e.message);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();