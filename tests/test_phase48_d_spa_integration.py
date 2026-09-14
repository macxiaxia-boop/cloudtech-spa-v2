"""
Phase 48.D84-87 SPA 集成测试
- FunnelPage 接入 SPA（/funnel）
- RevenuePage 接入 SPA（/pricing 增强）
- Homepage 顶部嵌入 4 关键数字
"""
import re
import sys
from pathlib import Path

WEB_ROOT = Path(r'D:\CloudTech-Portable\web\vite-spa\src')


def test_funnel_page_exists():
    """测试 1: FunnelPage.tsx 存在 + 关键内容"""
    funnel_page = WEB_ROOT / 'pages' / 'Funnel.tsx'
    assert funnel_page.exists(), 'Funnel.tsx 不存在'
    content = funnel_page.read_text(encoding='utf-8')
    assert 'export function FunnelPage' in content, 'FunnelPage 未导出'
    assert 'FUNNEL_SNAPSHOT' in content, 'FunnelPage 未引入漏斗数据'
    assert 'FUNNEL_INSIGHTS' in content, 'FunnelPage 未引入洞察数据'
    assert 'OVERALL_CONVERSION' in content, 'FunnelPage 未引入总转化率'
    # 5 状态机关键词（在 funnel.ts 数据中）— 这里只检查页面有"5 状态"概念
    assert '5 状态' in content or '5 状态机' in content or '漏斗' in content, 'FunnelPage 缺漏斗核心概念'
    # funnel.ts 数据文件应有 5 状态机
    funnel_data = (WEB_ROOT / 'data' / 'funnel.ts').read_text(encoding='utf-8')
    for stage in ['待跟进', '已联系', '已演示', '试用中', '已签约']:
        assert stage in funnel_data, f'funnel.ts 缺状态机 "{stage}"'
    print(f'  ✓ FunnelPage {len(content)} 字符 + funnel.ts 5 状态机齐')


def test_pricing_enhanced():
    """测试 2: Pricing.tsx 加 Revenue 段"""
    pricing = WEB_ROOT / 'pages' / 'Pricing.tsx'
    assert pricing.exists(), 'Pricing.tsx 不存在'
    content = pricing.read_text(encoding='utf-8')
    assert 'PRICING_TIERS' in content, 'Pricing.tsx 未引入 PRICING_TIERS'
    assert 'REVENUE_PROJECTIONS' in content, 'Pricing.tsx 未引入 REVENUE_PROJECTIONS'
    assert 'REVENUE_KEY_METRICS' in content, 'Pricing.tsx 未引入 KEY_METRICS'
    assert '营收预测' in content, 'Pricing.tsx 缺营收预测段标题'
    assert 'ARPU' in content, 'Pricing.tsx 缺 ARPU 关键数字'
    assert 'LTV' in content, 'Pricing.tsx 缺 LTV 关键数字'
    assert 'M1' in content and 'M3' in content and 'M6' in content and 'M12' in content, 'Pricing.tsx 缺时间维度'
    assert '红线 #22' in content, 'Pricing.tsx 缺红 #22 边界'
    print(f'  ✓ Pricing 增强 {len(content)} 字符，Revenue 段 + 4 关键数字 + 红 #22 齐')


def test_marketing_4_metrics():
    """测试 3: Marketing.tsx 嵌入 4 关键数字（80/1.25%/¥999/3.99）"""
    marketing = WEB_ROOT / 'pages' / 'Marketing.tsx'
    assert marketing.exists(), 'Marketing.tsx 不存在'
    content = marketing.read_text(encoding='utf-8')
    # 4 关键数字
    assert '>80<' in content or '>80 ' in content, 'Marketing.tsx 缺"80 P0 客户清单"'
    assert '1.25%' in content, 'Marketing.tsx 缺"1.25% 漏斗转化率"'
    assert '¥999' in content, 'Marketing.tsx 缺"¥999 标准版"'
    assert '3.99' in content, 'Marketing.tsx 缺"3.99 LTV/CAC"'
    # 必须没有老数字 210+
    assert '210+' not in content, 'Marketing.tsx 仍有老数字 210+'
    assert '1500+' not in content, 'Marketing.tsx 仍有老数字 1500+'
    print(f'  ✓ Marketing 4 关键数字嵌入（80/1.25%/¥999/3.99）')


def test_funnel_route_registered():
    """测试 4: App.tsx 注册 /funnel 路由"""
    app = WEB_ROOT / 'App.tsx'
    assert app.exists(), 'App.tsx 不存在'
    content = app.read_text(encoding='utf-8')
    assert 'FunnelPage' in content, 'App.tsx 未引入 FunnelPage'
    assert 'path="/funnel"' in content, 'App.tsx 未注册 /funnel 路由'
    print(f'  ✓ App.tsx /funnel 路由已注册')


def test_header_funnel_link():
    """测试 5: Header.tsx 加漏斗转化入口"""
    header = WEB_ROOT / 'components' / 'Header.tsx'
    assert header.exists(), 'Header.tsx 不存在'
    content = header.read_text(encoding='utf-8')
    assert "/funnel" in content, 'Header.tsx 漏斗入口缺失'
    assert '漏斗转化' in content, 'Header.tsx 漏斗标签缺失'
    print(f'  ✓ Header 漏斗转化入口已加（产品大区 · NEW badge）')


def test_consistent_data_imports():
    """测试 6: 数据导入一致性"""
    funnel_page = (WEB_ROOT / 'pages' / 'Funnel.tsx').read_text(encoding='utf-8')
    pricing = (WEB_ROOT / 'pages' / 'Pricing.tsx').read_text(encoding='utf-8')
    assert "from '../data/funnel'" in funnel_page, 'Funnel.tsx 漏斗数据导入路径错'
    assert "from '../data/revenue'" in pricing, 'Pricing.tsx 营收数据导入路径错'
    print(f'  ✓ 数据导入路径一致（funnel + revenue）')


def test_no_old_brand_names():
    """测试 7: 品牌一致（无旧名残留）"""
    files = ['Funnel.tsx', 'Pricing.tsx', 'Marketing.tsx', 'App.tsx', 'Header.tsx']
    issues = []
    for f in files:
        path = WEB_ROOT / 'pages' / f if f != 'Header.tsx' and f != 'App.tsx' else WEB_ROOT / ('pages' if f == 'Funnel.tsx' else 'components' if f == 'Header.tsx' else '') / f
        if not path.exists():
            issues.append(f'{f} 不存在')
            continue
        content = path.read_text(encoding='utf-8')
        for pat in ['灵策智算', 'CloudTech', 'LynxceAI', '阿劲']:
            if pat in content:
                issues.append(f'{f}: 含旧名 "{pat}"')
    assert len(issues) == 0, '品牌一致性问题:\n  ' + '\n  '.join(issues)
    print(f'  ✓ 全 5 文件品牌一致，无旧名残留')


if __name__ == '__main__':
    print('=' * 60)
    print('Phase 48.D84-87 · SPA 集成测试')
    print('=' * 60)
    print()
    tests = [
        test_funnel_page_exists,
        test_pricing_enhanced,
        test_marketing_4_metrics,
        test_funnel_route_registered,
        test_header_funnel_link,
        test_consistent_data_imports,
        test_no_old_brand_names,
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
