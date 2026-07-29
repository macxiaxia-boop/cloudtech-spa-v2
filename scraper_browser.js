/**
 * 社交媒体浏览器采集器 — Browser-based Social Scraper
 * =====================================================
 * Playwright 驱动，真实抓取小红书/抖音装修热门内容
 * 运行: node scraper_browser.js --platform xiaohongshu --keyword "装修前后对比"
 *       node scraper_browser.js --batch  # 批量采集
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, 'data', 'social_raw');
const SEARCH_KEYWORDS = {
  xiaohongshu: [
    '装修前后对比 改造 老房翻新',
    'room tour 装修 全屋设计',
    '装修预算 省钱攻略 费用明细',
    '装修避坑 经验分享 新手',
    '装修材料选购 怎么选 测评',
    '奶油风装修 现代简约 设计案例',
    '小户型装修 空间利用 收纳',
    '装修施工 水电改造 瓦工',
  ],
  douyin: [
    '装修全过程记录 vlog',
    '装修验收 避坑指南',
    '装修设计 效果图vs实景',
    '装修材料 到底怎么选',
    'room tour 新家 第一视角',
    '装修花费 多少钱 明细',
    '同城装修 案例实拍',
  ],
};

// ── Cookie 加载 ──
function loadCookies(platform) {
  const cookieFile = path.join(__dirname, `cookies_${platform}.json`);
  if (fs.existsSync(cookieFile)) {
    try {
      const cookies = JSON.parse(fs.readFileSync(cookieFile, 'utf-8'));
      console.log(`[Cookie] Loaded ${cookies.length} cookies for ${platform}`);
      return cookies;
    } catch (e) {
      console.log(`[Cookie] Failed to load ${cookieFile}: ${e.message}`);
    }
  }
  console.log(`[Cookie] No cookie file at ${cookieFile} — using anonymous mode`);
  return [];
}

// ── 小红书抓取 ──
async function scrapeXiaohongshu(keyword, maxResults = 5) {
  const notes = [];
  const browser = await chromium.launch({ headless: true });
  const cookies = loadCookies('xiaohongshu');
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 800 },
  });
  if (cookies.length > 0) {
    await context.addCookies(cookies);
  }
  const page = await context.newPage();

  try {
    const searchUrl = `https://www.xiaohongshu.com/search_result?keyword=${encodeURIComponent(keyword)}&sort=general`;
    console.log(`[XHS] Navigating: ${searchUrl}`);
    await page.goto(searchUrl, { timeout: 20000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    // Try multiple selectors for note cards
    const selectors = ['.note-item', '.search-result-item', 'section.note-item', '[data-testid="note-card"]'];
    let cards = [];
    for (const sel of selectors) {
      cards = await page.$$(sel);
      if (cards.length > 0) break;
    }

    console.log(`[XHS] Found ${cards.length} cards for "${keyword}"`);

    for (let i = 0; i < Math.min(cards.length, maxResults); i++) {
      try {
        const card = cards[i];
        const note = { platform: 'xiaohongshu', search_keyword: keyword, collected_at: new Date().toISOString() };

        // Title
        const titleEl = await card.$('.title, .note-title, [data-testid="title"]');
        note.title = titleEl ? (await titleEl.innerText()).trim() : '';

        // Content/Description
        const descEl = await card.$('.desc, .note-desc, .description');
        note.content = descEl ? (await descEl.innerText()).trim() : '';

        // Hashtags & topics
        const tagEls = await card.$$('.tag, .hashtag, .topic-tag, a[href*="tag"]');
        note.hashtags = [];
        for (const t of tagEls) {
          const text = (await t.innerText()).replace(/#/g, '').trim();
          if (text && text.length < 20) note.hashtags.push(text);
        }

        // Interaction counts
        const likeEl = await card.$('.like-count, .count, [class*="like"]');
        note.likes = likeEl ? parseCount(await likeEl.innerText()) : 0;

        // Cover image URL
        const imgEl = await card.$('img');
        note.cover_image = imgEl ? (await imgEl.getAttribute('src')) : '';

        // Link
        const linkEl = await card.$('a[href*="explore"]');
        note.url = linkEl ? 'https://www.xiaohongshu.com' + (await linkEl.getAttribute('href')) : '';

        // Infer layout type from content
        note.layout_type = inferLayout(note.title + note.content);

        notes.push(note);
        console.log(`  [XHS] ${note.title?.substring(0, 40)} | ${note.hashtags.length} tags | ${note.likes} likes`);
      } catch (e) {
        console.log(`  [XHS] Skip card ${i}: ${e.message}`);
      }
    }
  } catch (e) {
    console.error(`[XHS] Error: ${e.message}`);
  } finally {
    await browser.close();
  }

  return notes;
}

// ── 抖音抓取 ──
async function scrapeDouyin(keyword, maxResults = 5) {
  const videos = [];
  const browser = await chromium.launch({ headless: true });
  const cookies = loadCookies('douyin');
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 800 },
  });
  if (cookies.length > 0) {
    await context.addCookies(cookies);
  }
  const page = await context.newPage();

  try {
    const searchUrl = `https://www.douyin.com/search/${encodeURIComponent(keyword)}?type=general`;
    console.log(`[DY] Navigating: ${searchUrl}`);
    await page.goto(searchUrl, { timeout: 20000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    const selectors = ['.search-result-card', '.video-card', '[data-e2e="search-card"]'];
    let cards = [];
    for (const sel of selectors) {
      cards = await page.$$(sel);
      if (cards.length > 0) break;
    }

    console.log(`[DY] Found ${cards.length} cards for "${keyword}"`);

    for (let i = 0; i < Math.min(cards.length, maxResults); i++) {
      try {
        const card = cards[i];
        const video = { platform: 'douyin', search_keyword: keyword, collected_at: new Date().toISOString() };

        // Title
        const titleEl = await card.$('.title, .video-title, [data-e2e="title"]');
        video.title = titleEl ? (await titleEl.innerText()).trim() : '';

        // Duration
        const durEl = await card.$('.duration, [class*="duration"]');
        video.duration_sec = durEl ? parseDuration(await durEl.innerText()) : 0;

        // Likes
        const likeEl = await card.$('.like-count, [class*="like"]');
        video.likes = likeEl ? parseCount(await likeEl.innerText()) : 0;

        // Hashtags
        const tagEls = await card.$$('a[href*="tag"], .hashtag');
        video.hashtags = [];
        for (const t of tagEls) {
          const text = (await t.innerText()).replace(/#/g, '').trim();
          if (text && text.length < 20) video.hashtags.push(text);
        }

        // Cover image
        const imgEl = await card.$('img');
        video.cover_image = imgEl ? (await imgEl.getAttribute('src')) : '';

        // Author
        const authorEl = await card.$('.author, .nickname');
        video.author = authorEl ? (await authorEl.innerText()).trim() : '';

        video.url = page.url();

        videos.push(video);
        console.log(`  [DY] ${video.title?.substring(0, 40)} | ${video.duration_sec}s | ${video.likes} likes`);
      } catch (e) {
        console.log(`  [DY] Skip card ${i}: ${e.message}`);
      }
    }
  } catch (e) {
    console.error(`[DY] Error: ${e.message}`);
  } finally {
    await browser.close();
  }

  return videos;
}

// ── 批量采集 ──
async function batchScrape() {
  console.log('=== 社交媒体批量采集 ===');
  console.log(`时间: ${new Date().toISOString()}`);
  console.log(`小红书Query: ${SEARCH_KEYWORDS.xiaohongshu.length}  抖音Query: ${SEARCH_KEYWORDS.douyin.length}`);
  console.log('');

  const allResults = { xiaohongshu: [], douyin: [] };

  // Xiaohongshu
  for (const kw of SEARCH_KEYWORDS.xiaohongshu.slice(0, 3)) {
    console.log(`\n[XHS] "${kw}"`);
    const notes = await scrapeXiaohongshu(kw, 5);
    allResults.xiaohongshu.push(...notes);
    // Rate limiting
    await new Promise(r => setTimeout(r, 2000));
  }

  // Douyin
  for (const kw of SEARCH_KEYWORDS.douyin.slice(0, 3)) {
    console.log(`\n[DY] "${kw}"`);
    const videos = await scrapeDouyin(kw, 5);
    allResults.douyin.push(...videos);
    await new Promise(r => setTimeout(r, 2000));
  }

  // Save
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
  const outFile = path.join(DATA_DIR, `batch_${timestamp}.json`);
  fs.mkdirSync(DATA_DIR, { recursive: true });
  fs.writeFileSync(outFile, JSON.stringify(allResults, null, 2), 'utf-8');

  console.log(`\n=== 完成 ===`);
  console.log(`小红书: ${allResults.xiaohongshu.length} 条`);
  console.log(`抖音: ${allResults.douyin.length} 条`);
  console.log(`输出: ${outFile}`);

  return allResults;
}

// ── 工具函数 ──
function parseCount(text) {
  if (!text) return 0;
  text = text.trim().replace(/,/g, '');
  if (text.includes('万')) return Math.round(parseFloat(text.replace('万', '')) * 10000);
  if (text.includes('w')) return Math.round(parseFloat(text.replace('w', '')) * 10000);
  return parseInt(text) || 0;
}

function parseDuration(text) {
  if (!text) return 0;
  const parts = text.trim().split(':');
  if (parts.length === 2) return parseInt(parts[0]) * 60 + parseInt(parts[1]);
  if (parts.length === 3) return parseInt(parts[0]) * 3600 + parseInt(parts[1]) * 60 + parseInt(parts[2]);
  return parseInt(text) || 0;
}

function inferLayout(text) {
  if (/对比|before|after|改造前|改造后/.test(text)) return '对比图';
  if (/合集|推荐|TOP|盘点/.test(text)) return '拼图合集';
  if (/roomtour|漫游|全屋|一镜到底/.test(text)) return '长图/视频';
  if (/细节|材质|纹理|特写/.test(text)) return '细节特写';
  return '单图/实拍';
}

// ── CLI ──
const args = process.argv.slice(2);
const platformIdx = args.indexOf('--platform');
const keywordIdx = args.indexOf('--keyword');
const batchFlag = args.includes('--batch');

(async () => {
  if (batchFlag) {
    await batchScrape();
  } else if (platformIdx >= 0 && keywordIdx >= 0) {
    const platform = args[platformIdx + 1];
    const keyword = args[keywordIdx + 1];
    if (platform === 'xiaohongshu') {
      const notes = await scrapeXiaohongshu(keyword, 5);
      console.log(JSON.stringify(notes, null, 2));
    } else if (platform === 'douyin') {
      const videos = await scrapeDouyin(keyword, 5);
      console.log(JSON.stringify(videos, null, 2));
    }
  } else {
    console.log('Usage: node scraper_browser.js --batch');
    console.log('       node scraper_browser.js --platform xiaohongshu --keyword "装修"');
  }
})();
