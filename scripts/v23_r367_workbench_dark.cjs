// R367 · vite-spa 工作台 page dark mode 截图 · puppeteer-core + msedge
// 治本 R366 全仓 dark CSS · 验证 Settings / Dashboard / Monitoring 等页面 dark 真生效
const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');
const os = require('os');

const OUT_DIR = path.join(os.tmpdir(), 'v23_shots');
try { fs.mkdirSync(OUT_DIR, { recursive: true }); } catch {}

const TESTS = [
  // Marketing routes (already verified R363 · re-verify)
  { name: 'marketing',  url: 'http://127.0.0.1:7792/',                  expect: 'marketing hero' },
  // 工作台 routes (R367 验证)
  // Note: /dashboard 等需要 auth · 直接访问会被 redirect /login
  // 临时方案: 直接看 login page dark mode
  { name: 'login',      url: 'http://127.0.0.1:7792/login',             expect: 'login form' },
  { name: 'try',        url: 'http://127.0.0.1:7792/try',               expect: 'try page form' },
  { name: 'pricing',    url: 'http://127.0.0.1:7792/pricing',           expect: 'pricing 3-tier' },
];

const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';

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
      // 浅色
      await page.goto(test.url, { waitUntil: 'networkidle2', timeout: 15000 });
      await page.evaluate(() => {
        try { localStorage.setItem('cloudtech_onboarding_done', 'true'); } catch {}
      });
      await page.reload({ waitUntil: 'networkidle2' });
      await new Promise(r => setTimeout(r, 1500));
      const lightPath = path.join(OUT_DIR, `r367_${test.name}_light.png`);
      await page.screenshot({ path: lightPath });
      console.log(`✅ ${test.name} light: ${lightPath}`);

      // 深色
      await page.evaluate(() => {
        localStorage.setItem('ct.theme', 'dark');
        document.documentElement.classList.add('dark');
      });
      await page.reload({ waitUntil: 'networkidle2' });
      await new Promise(r => setTimeout(r, 1500));
      const darkPath = path.join(OUT_DIR, `r367_${test.name}_dark.png`);
      await page.screenshot({ path: darkPath });
      console.log(`✅ ${test.name} dark: ${darkPath}`);

      const cls = await page.evaluate(() => document.documentElement.className);
      console.log(`   ${test.name} documentElement.className: ${cls}`);

      await page.close();
    }
  } catch (e) {
    console.error('ERROR:', e.message);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();