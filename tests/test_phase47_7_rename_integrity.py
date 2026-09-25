"""
Phase 47.7 — 全站改名完整性测试（红线 R2/R6 + 红线 #22）
- 创始人：阿劲 → 心之所向便是光
- 产品：灵策智算 / CloudTech / LynxceAI → Cloud
- 适用范围：SPA src + docs + Phase48.B workzone
- 反转 110 教训：双轨卡 = 形式 + 表达 + 合规；总评 = min
"""
import os
import re
import sys
from pathlib import Path

# === 配置 ===
FORBIDDEN = ['灵策智算', 'CloudTech', 'LynxceAI', '阿劲']
# 排除允许的例外（仅在对比/历史/合规引用中出现，不视为残留）
EXCEPTION_FILE_PATTERNS = [
    r'feedback-.*\.md$',          # 历史反馈文件允许引用
    r'CORE-RULES.*\.md$',          # 历史宪法允许引用
    r'CLAUDE.*\.md$',              # 全局 CLAUDE 允许引用
    r'MEMORY.*\.md$',              # MEMORY 索引允许引用
    r'_archived.*',                # 归档目录
    r'.*\.git/.*',                 # git 内部
]

SCAN_ROOTS = [
    Path(r'D:\CloudTech-Portable\web\vite-spa\src'),
    Path(r'D:\CloudTech-Portable\docs'),
    Path(r'D:\个人文件\AI\Operator\docs'),
    Path(r'D:\个人文件\AI\Operator\_workzone\Phase48-B-Content-Production-2026-09-14'),
]
SCAN_EXTS = {'.tsx', '.ts', '.js', '.jsx', '.md', '.json', '.css', '.html'}

# 必须出现的关键内容（防止误删导致空缺）
REQUIRED = [
    ('心之所向便是光', 1, '创始人名'),
    ('Cloud', 1, '产品名'),
]


def is_exception(filepath: str) -> bool:
    for pattern in EXCEPTION_FILE_PATTERNS:
        if re.search(pattern, filepath):
            return True
    return False


def scan_forbidden() -> list:
    """扫描所有目标目录中的禁用词"""
    hits = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for dirpath, dirs, files in os.walk(root):
            # 跳过 node_modules / .git / 归档
            dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', '_archived', 'dist', 'build')]
            for f in files:
                if not any(f.endswith(e) for e in SCAN_EXTS):
                    continue
                path = Path(dirpath) / f
                if is_exception(str(path)):
                    continue
                try:
                    content = path.read_text(encoding='utf-8')
                except (UnicodeDecodeError, PermissionError):
                    continue
                for pat in FORBIDDEN:
                    if pat in content:
                        n = content.count(pat)
                        hits.append((str(path), pat, n, content[:200]))
    return hits


def scan_required() -> list:
    """扫描必需的关键内容是否存在"""
    misses = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', '_archived', 'dist', 'build')]
            for f in files:
                if not any(f.endswith(e) for e in SCAN_EXTS):
                    continue
                path = Path(dirpath) / f
                if is_exception(str(path)):
                    continue
                try:
                    content = path.read_text(encoding='utf-8')
                except (UnicodeDecodeError, PermissionError):
                    continue
                for pat, min_count, desc in REQUIRED:
                    actual = content.count(pat)
                    if actual < min_count:
                        misses.append((str(path), pat, min_count, actual, desc))
    return misses


def check_duplicate_cloud() -> list:
    """检测双重 Cloud 重复（Phase 47.7 治本）"""
    duplicates = []
    patterns = ['Cloud / Cloud', 'Cloud · Cloud', 'Cloud · Cloud']
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', '_archived', 'dist', 'build')]
            for f in files:
                if not any(f.endswith(e) for e in SCAN_EXTS):
                    continue
                path = Path(dirpath) / f
                if is_exception(str(path)):
                    continue
                try:
                    content = path.read_text(encoding='utf-8')
                except (UnicodeDecodeError, PermissionError):
                    continue
                for pat in patterns:
                    n = content.count(pat)
                    if n > 0:
                        duplicates.append((str(path), pat, n))
    return duplicates


# === 测试用例 ===

def test_no_forbidden_names():
    """测试1: 无禁用旧名（灵策智算/CloudTech/LynxceAI/阿劲）"""
    hits = scan_forbidden()
    if hits:
        msg = f'发现 {len(hits)} 处禁用旧名残留:\n'
        for path, pat, n, _ in hits[:10]:
            msg += f'  [{n}] {path}: "{pat}"\n'
        if len(hits) > 10:
            msg += f'  ... +{len(hits)-10} more\n'
        raise AssertionError(msg)
    print(f'  ✓ 全站无 {len(FORBIDDEN)} 类禁用旧名')


def test_no_duplicate_cloud():
    """测试2: 无双重 Cloud 重复（"Cloud / Cloud" / "Cloud · Cloud"）"""
    dups = check_duplicate_cloud()
    if dups:
        msg = f'发现 {len(dups)} 处双重 Cloud 重复:\n'
        for path, pat, n in dups[:10]:
            msg += f'  [{n}] {path}: "{pat}"\n'
        raise AssertionError(msg)
    print(f'  ✓ 全站无双重 Cloud 重复')


def test_required_names_present():
    """测试3: 必需的新名（心之所向便是光 + Cloud）存在"""
    misses = scan_required()
    # 只统计 SPA src 中是否至少有 1 处出现
    spa_root = Path(r'D:\CloudTech-Portable\web\vite-spa\src')
    spa_creator_count = 0
    spa_product_count = 0
    if spa_root.exists():
        for dirpath, dirs, files in os.walk(spa_root):
            dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', 'dist', 'build')]
            for f in files:
                if not any(f.endswith(e) for e in SCAN_EXTS):
                    continue
                path = Path(dirpath) / f
                try:
                    content = path.read_text(encoding='utf-8')
                except (UnicodeDecodeError, PermissionError):
                    continue
                spa_creator_count += content.count('心之所向便是光')
                spa_product_count += content.count('Cloud')
    if spa_creator_count == 0:
        raise AssertionError('SPA 中无"心之所向便是光" - 创始人改名丢失')
    if spa_product_count == 0:
        raise AssertionError('SPA 中无"Cloud" - 产品改名丢失')
    print(f'  ✓ SPA 中"心之所向便是光"出现 {spa_creator_count} 次')
    print(f'  ✓ SPA 中"Cloud"出现 {spa_product_count} 次')


def test_rename_scope():
    """测试4: 改名范围覆盖 SPA + docs + workzone"""
    total_files_scanned = 0
    total_files_with_content = 0
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', '_archived', 'dist', 'build')]
            for f in files:
                if not any(f.endswith(e) for e in SCAN_EXTS):
                    continue
                total_files_scanned += 1
                path = Path(dirpath) / f
                try:
                    content = path.read_text(encoding='utf-8')
                    if 'Cloud' in content or '心之所向便是光' in content:
                        total_files_with_content += 1
                except (UnicodeDecodeError, PermissionError):
                    continue
    if total_files_scanned == 0:
        raise AssertionError('扫描范围为空 - 检查 SCAN_ROOTS 配置')
    print(f'  ✓ 扫描 {total_files_scanned} 文件，{total_files_with_content} 文件含 Cloud/心之所向便是光')


def test_footer_signature():
    """测试5: Footer.tsx 含新签名（不是 Cloud · Cloud SaaS）"""
    footer = Path(r'D:\CloudTech-Portable\web\vite-spa\src\components\Footer.tsx')
    if not footer.exists():
        raise AssertionError('Footer.tsx 不存在')
    content = footer.read_text(encoding='utf-8')
    # 必须包含"© 2026 Cloud"（不带 · Cloud SaaS 重复）
    if '© 2026 Cloud · Cloud SaaS' in content:
        raise AssertionError('Footer.tsx 仍有双重 Cloud 重复')
    if '© 2026 Cloud' not in content:
        raise AssertionError('Footer.tsx 缺少 © 2026 Cloud 签名')
    print(f'  ✓ Footer.tsx 签名正常（© 2026 Cloud SaaS）')


def test_blog_creator_name():
    """测试6: Blog.tsx 作者字段全部为心之所向便是光"""
    blog = Path(r'D:\CloudTech-Portable\web\vite-spa\src\pages\Blog.tsx')
    if not blog.exists():
        raise AssertionError('Blog.tsx 不存在')
    content = blog.read_text(encoding='utf-8')
    if '阿劲' in content:
        raise AssertionError('Blog.tsx 仍有"阿劲"残留')
    if '心之所向便是光' not in content:
        raise AssertionError('Blog.tsx 缺少"心之所向便是光"作者字段')
    creator_count = content.count('心之所向便是光')
    if creator_count < 5:
        raise AssertionError(f'Blog.tsx "心之所向便是光"出现 {creator_count} 次（预期 ≥ 5）')
    print(f'  ✓ Blog.tsx 含 {creator_count} 处"心之所向便是光"')


def test_faq_creator_name():
    """测试7: FAQ.tsx OPC 模式问题含新创始人名"""
    faq = Path(r'D:\CloudTech-Portable\web\vite-spa\src\pages\FAQ.tsx')
    if not faq.exists():
        raise AssertionError('FAQ.tsx 不存在')
    content = faq.read_text(encoding='utf-8')
    if '阿劲' in content or 'CloudTech' in content:
        raise AssertionError('FAQ.tsx 含旧名残留')
    if '心之所向便是光' not in content:
        raise AssertionError('FAQ.tsx 缺少"心之所向便是光"')
    if 'Cloud' not in content:
        raise AssertionError('FAQ.tsx 缺少"Cloud"产品名')
    print(f'  ✓ FAQ.tsx OPC 模式描述已含新创始人 + 新产品名')


def test_workzone_phase48b():
    """测试8: Phase48.B 3 文件全部含新名"""
    workzone = Path(r'D:\个人文件\AI\Operator\_workzone\Phase48-B-Content-Production-2026-09-14')
    if not workzone.exists():
        raise AssertionError('Phase48.B workzone 不存在')
    files = list(workzone.glob('*.md'))
    if len(files) < 3:
        raise AssertionError(f'Phase48.B workzone 文件数 {len(files)}（预期 ≥ 3）')
    for f in files:
        content = f.read_text(encoding='utf-8')
        if '阿劲' in content or 'CloudTech' in content or '灵策智算' in content:
            raise AssertionError(f'{f.name} 含旧名残留')
        if '心之所向便是光' not in content:
            raise AssertionError(f'{f.name} 缺少"心之所向便是光"')
    print(f'  ✓ Phase48.B {len(files)} 文件全部含新创始人 + 无旧名残留')


# === 主程序 ===
if __name__ == '__main__':
    print('=' * 60)
    print('Phase 47.7 · 全站改名完整性测试')
    print('=' * 60)
    print()
    tests = [
        test_no_forbidden_names,
        test_no_duplicate_cloud,
        test_required_names_present,
        test_rename_scope,
        test_footer_signature,
        test_blog_creator_name,
        test_faq_creator_name,
        test_workzone_phase48b,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            print(f'[{t.__name__}]')
            t()
            passed += 1
        except AssertionError as e:
            print(f'  ❌ FAIL: {e}')
            failed += 1
        except Exception as e:
            print(f'  ❌ ERROR: {e}')
            failed += 1
        print()
    print('=' * 60)
    print(f'结果: {passed}/{len(tests)} PASS, {failed}/{len(tests)} FAIL')
    print('=' * 60)
    sys.exit(0 if failed == 0 else 1)
