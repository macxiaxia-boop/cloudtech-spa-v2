// R360 · V23 vite-spa Dark mode 截图 · puppeteer-core + msedge
// 治本 R359 受限 (OnboardingTrigger modal + SPA fallback class 覆盖)
const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');
const os = require('os');

// Windows: 用 os.tmpdir() 拿真 temp 目录
const OUT_DIR = path.join(os.tmpdir(), 'v23_shots');
try { fs.mkdirSync(OUT_DIR, { recursive: true }); } catch {}

(async () => {
  const URL = process.env.URL || 'http://127.0.0.1:7792/';
  const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';

  const browser = await puppeteer.launch({
    executablePath: EDGE,
    headless: 'new',
    args: ['--no-sandbox', '--disable-gpu', '--hide-scrollbars'],
    defaultViewport: { width: 1440, height: 900 },
  });

  try {
    const page = await browser.newPage();

    // 1) 浅色截图
    await page.goto(URL, { waitUntil: 'networkidle2', timeout: 15000 });
    await page.evaluate(() => {
      try { localStorage.setItem('cloudtech_onboarding_done', 'true'); } catch {}
    });
    await page.reload({ waitUntil: 'networkidle2' });
    await new Promise(r => setTimeout(r, 1500));
    const lightPath = path.join(OUT_DIR, 'r360_light.png');
    await page.screenshot({ path: lightPath });
    console.log('✅ Light:', lightPath);

    // 2) 深色 (用 ThemeToggle 按钮)
    const toggleBtn = await page.$('button[aria-label="切换深色模式"]');
    if (toggleBtn) {
      await toggleBtn.click();
      await new Promise(r => setTimeout(r, 800));
    } else {
      console.log('⚠️  Toggle button not found, using localStorage fallback');
      await page.evaluate(() => {
        localStorage.setItem('ct.theme', 'dark');
        document.documentElement.classList.add('dark');
      });
    }
    await page.reload({ waitUntil: 'networkidle2' });
    await new Promise(r => setTimeout(r, 1500));
    const darkPath = path.join(OUT_DIR, 'r360_dark.png');
    await page.screenshot({ path: darkPath });
    console.log('✅ Dark:', darkPath);

    const cls = await page.evaluate(() => document.documentElement.className);
    console.log('documentElement.className:', cls);
  } catch (e) {
    console.error('ERROR:', e.message);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();