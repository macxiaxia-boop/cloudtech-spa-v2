/**
 * CloudTech Frontend Validator v3 — 发布前质量闸门
 * 用法: node validate_frontend.js [--fix]
 * 
 * 检测规则:
 *   1. 重复关键字 (async async, function function 等)
 *   2. JS 语法错误 (通过 Node.js vm.Script 解析)
 * 
 * 退出码 0 = 通过, 1 = 阻塞发布
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const LANDING = path.join(__dirname, 'landing-page');
const HTML_FILES = fs.readdirSync(LANDING).filter(f => f.endsWith('.html'));

let totalErrors = 0;

// ── Extract <script> blocks, skipping non-JS types ──
function extractJSBlocks(html) {
  const blocks = [];
  const regex = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
  let match;
  while ((match = regex.exec(html)) !== null) {
    const attrs = match[1];
    const body = match[2];
    
    // Skip non-JS scripts (JSON-LD, templates, etc.)
    const typeMatch = attrs.match(/type\s*=\s*["']([^"']+)["']/i);
    if (typeMatch) {
      const type = typeMatch[1].toLowerCase();
      if (type !== 'text/javascript' && type !== 'module' && type !== 'application/javascript') {
        continue;
      }
    }
    
    const lineOffset = html.substring(0, match.index).split('\n').length - 1;
    blocks.push({ code: body, lineOffset, raw: match[0] });
  }
  return blocks;
}

// ── Check 1: Double keywords ──
function checkDoubleKeywords(code, filename, lineOffset) {
  const errors = [];
  const keywords = ['async', 'function', 'var', 'let', 'const', 'if', 'for', 'while'];

  for (const kw of keywords) {
    const regex = new RegExp(`\\b(${kw})\\s+(${kw})\\b`, 'g');
    let m;
    while ((m = regex.exec(code)) !== null) {
      const localLine = code.substring(0, m.index).split('\n').length;
      errors.push({
        file: filename, line: localLine + lineOffset,
        type: 'DOUBLE_KEYWORD',
        detail: `重复关键字 "${kw} ${kw}"`,
        fixable: true,
        fix: { offsetInHTML: null, old: m[0], new: kw },
      });
    }
  }
  return errors;
}

// ── Check 2: Syntax via Node.js vm.Script ──
function checkSyntax(code, filename, lineOffset) {
  try {
    new vm.Script(code, { filename });
    return null; // ok
  } catch (e) {
    const lineMatch = e.stack && e.stack.match(new RegExp(`${filename.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}:(\\d+)`));
    const errLine = lineMatch ? parseInt(lineMatch[1]) : 1;
    return {
      file: filename, line: errLine + lineOffset,
      type: 'SYNTAX',
      detail: e.message.split('\n')[0],
      fixable: false,
    };
  }
}

// ── Auto-fix double keywords in HTML ──
function autoFix(html, errors) {
  // Sort by: first by the <script> block position (descending), 
  // then by offset within block (descending)
  const fixes = [];
  let lastScriptPos = 0;
  let scriptIndex = -1;
  
  const regex = /<script\b[^>]*>[\s\S]*?<\/script>/gi;
  let match;
  while ((match = regex.exec(html)) !== null) {
    scriptIndex++;
    const attrs = match[0].match(/type\s*=\s*["']([^"']+)["']/i);
    if (attrs) {
      const t = attrs[1].toLowerCase();
      if (t !== 'text/javascript' && t !== 'module' && t !== 'application/javascript') continue;
    }
    
    const scriptBodyMatch = match[0].match(/<script\b[^>]*>([\s\S]*?)<\/script>/i);
    if (!scriptBodyMatch) continue;
    const scriptBody = scriptBodyMatch[1];
    const bodyStart = match.index + match[0].indexOf(scriptBody);
    
    // Find errors in this block
    for (const err of errors) {
      if (err.fix && !err.fix.offsetInHTML && err.file === path.basename(err.file)) {
        // Try to find the match in this script block
        const idx = scriptBody.indexOf(err.fix.old);
        if (idx >= 0) {
          fixes.push({ pos: bodyStart + idx, old: err.fix.old, new: err.fix.new });
        }
      }
    }
  }
  
  fixes.sort((a, b) => b.pos - a.pos); // descending for safe replacement
  for (const f of fixes) {
    html = html.substring(0, f.pos) + f.new + html.substring(f.pos + f.old.length);
  }
  return html;
}

// ── Main ──
console.log('═'.repeat(60));
console.log('  CloudTech Frontend Validator v3');
console.log('═'.repeat(60) + '\n');

const fixMode = process.argv.includes('--fix');
let allErrors = [];

for (const htmlFile of HTML_FILES) {
  const filePath = path.join(LANDING, htmlFile);
  let html = fs.readFileSync(filePath, 'utf-8');
  const blocks = extractJSBlocks(html);
  
  if (blocks.length === 0) continue;
  
  let fileErrs = 0;
  
  for (const { code, lineOffset } of blocks) {
    // Double keyword check
    const kwErrs = checkDoubleKeywords(code, htmlFile, lineOffset);
    for (const err of kwErrs) {
      console.log(`  🔧 ${err.file}:${err.line}  [${err.type}] ${err.detail}`);
      fileErrs++;
      allErrors.push(err);
    }
    
    // Syntax check
    const synErr = checkSyntax(code, htmlFile, lineOffset);
    if (synErr) {
      console.log(`  ❌ ${synErr.file}:${synErr.line}  [${synErr.type}] ${synErr.detail}`);
      fileErrs++;
      allErrors.push(synErr);
    }
  }
  
  if (fileErrs > 0) {
    console.log(`  📄 ${htmlFile}: ${fileErrs} 个问题\n`);
    
    if (fixMode) {
      html = autoFix(html, allErrors.filter(e => e.file === htmlFile && e.fixable));
      fs.writeFileSync(filePath, html, 'utf-8');
    }
  }
  
  totalErrors += fileErrs;
}

console.log('═'.repeat(60));
if (totalErrors === 0) {
  console.log('  ✅ 全部通过！可以发布。');
} else if (fixMode) {
  console.log('  🔧 已自动修复，请重新运行验证确认。');
} else {
  const fixableCount = allErrors.filter(e => e.fixable).length;
  console.log(`  ❌ ${totalErrors} 个错误阻塞发布！`);
  if (fixableCount > 0) {
    console.log(`  其中 ${fixableCount} 个可自动修复: node validate_frontend.js --fix`);
  }
}
console.log('═'.repeat(60));

process.exit(totalErrors > 0 ? 1 : 0);
