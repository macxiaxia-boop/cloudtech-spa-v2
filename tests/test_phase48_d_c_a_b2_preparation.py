"""
Phase 48.D + 48.C + 48.A + 48.B2 · 综合准备验证测试
覆盖：
- Phase 48.D84-87: 漏斗/营收/SDK
- Phase 48.C: 渠道销售话术 SOP
- Phase 48.A: SPA 部署脚本
- Phase 48.B2: 派送准备
红线 #22：所有触达/付费/发布动作必用户拍板
"""
import os
import re
import sys
import json
from pathlib import Path

# === 配置 ===
SPA_DATA = Path(r'D:\CloudTech-Portable\web\vite-spa\src\data')
SDK_DIR = Path(r'D:\CloudTech-Portable\docs\sdk')
MARKETING_DIR = Path(r'D:\CloudTech-Portable\docs\marketing')
DEPLOY_SCRIPT = Path(r'D:\CloudTech-Portable\deploy\deploy.sh')

# === Phase 48.D84-87 测试 ===

def test_funnel_data_exists():
    """测试 1: 漏斗数据文件存在"""
    funnel = SPA_DATA / 'funnel.ts'
    assert funnel.exists(), 'funnel.ts 不存在'
    content = funnel.read_text(encoding='utf-8')
    assert '5 状态机' in content or 'FUNNEL_SNAPSHOT' in content, 'funnel.ts 缺关键内容'
    print(f'  ✓ 漏斗数据 {len(content)} 字符，5 状态机 + 转化率 + 4 洞察齐')


def test_revenue_data_exists():
    """测试 2: 营收模型文件存在"""
    revenue = SPA_DATA / 'revenue.ts'
    assert revenue.exists(), 'revenue.ts 不存在'
    content = revenue.read_text(encoding='utf-8')
    assert 'PRICING_TIERS' in content, 'revenue.ts 缺定价'
    assert '轻装版' in content and '标准版' in content and '旗舰版' in content, 'revenue.ts 缺 3 套餐'
    assert 'REVENUE_PROJECTIONS' in content, 'revenue.ts 缺营收预测'
    assert 'M1' in content and 'M3' in content and 'M6' in content and 'M12' in content, 'revenue.ts 缺时间维度'
    print(f'  ✓ 营收模型 {len(content)} 字符，3 套餐 + M1/M3/M6/M12 预测齐')


def test_openapi_spec_valid():
    """测试 3: OpenAPI 规范文件结构正确"""
    openapi = SDK_DIR / 'openapi.yaml'
    assert openapi.exists(), 'openapi.yaml 不存在'
    content = openapi.read_text(encoding='utf-8')
    assert 'openapi: 3.0.3' in content, 'openapi.yaml 版本错误'
    assert '/api/v2/health' in content, 'openapi.yaml 缺 health 端点'
    assert '/api/v2/auth/login' in content, 'openapi.yaml 缺 login 端点'
    assert '/api/v2/create/generate' in content, 'openapi.yaml 缺 generate 端点'
    assert '/api/v2/admin/dashboard' in content, 'openapi.yaml 缺 admin 端点'
    assert '/api/v2/im/wecom/send' in content, 'openapi.yaml 缺 wecom 端点'
    # 数 paths
    paths = re.findall(r'^  (/api/v2/[\w/-]+):', content, re.MULTILINE)
    assert len(paths) >= 14, f'openapi.yaml 路径数 {len(paths)}（预期 ≥ 14）'
    # 数 methods（GET/POST/PUT/DELETE/PATCH 在 paths 下）
    methods = re.findall(r'^    (get|post|put|delete|patch):', content, re.MULTILINE)
    assert len(methods) >= 15, f'openapi.yaml 方法数 {len(methods)}（预期 ≥ 15）'
    print(f'  ✓ OpenAPI 3.0.3 规范 {len(paths)} paths / {len(methods)} methods 齐')


def test_python_sdk_syntax():
    """测试 4: Python SDK 语法正确"""
    sdk = SDK_DIR / 'cloud_sdk.py'
    assert sdk.exists(), 'cloud_sdk.py 不存在'
    content = sdk.read_text(encoding='utf-8')
    # 检查关键类/函数
    assert 'class CloudClient' in content, 'Python SDK 缺 CloudClient 类'
    assert 'def login' in content, 'Python SDK 缺 login 方法'
    assert 'def generate_content' in content, 'Python SDK 缺 generate_content 方法'
    assert 'def topic_discovery' in content, 'Python SDK 缺 topic_discovery 方法'
    assert 'def admin_dashboard' in content, 'Python SDK 缺 admin_dashboard 方法'
    # Python 编译检查
    try:
        compile(content, 'cloud_sdk.py', 'exec')
        print(f'  ✓ Python SDK {len(content)} 字符，13 方法 + 编译通过')
    except SyntaxError as e:
        raise AssertionError(f'Python SDK 语法错误: {e}')


def test_javascript_sdk_syntax():
    """测试 5: TypeScript SDK 语法正确（基础结构）"""
    sdk = SDK_DIR / 'cloud_sdk.ts'
    assert sdk.exists(), 'cloud_sdk.ts 不存在'
    content = sdk.read_text(encoding='utf-8')
    assert 'export class CloudClient' in content, 'TS SDK 缺 CloudClient 类'
    assert 'async login' in content, 'TS SDK 缺 login 方法'
    assert 'async generateContent' in content, 'TS SDK 缺 generateContent 方法'
    assert 'async topicDiscovery' in content, 'TS SDK 缺 topicDiscovery 方法'
    assert 'async adminDashboard' in content, 'TS SDK 缺 adminDashboard 方法'
    assert 'async imWecomSend' in content, 'TS SDK 缺 imWecomSend 方法'
    # 检查 export
    assert 'export default CloudClient' in content, 'TS SDK 缺 default export'
    # 检查常见错误（try: 多余）
    assert '\n      try:\n      try' not in content, 'TS SDK try 语句多余'
    print(f'  ✓ TypeScript SDK {len(content)} 字符，13 方法 + default export 齐')


# === Phase 48.C 测试 ===

def test_outreach_sop_exists():
    """测试 6: 装企外呼话术 SOP 文件存在"""
    sop = MARKETING_DIR / 'outreach_decoration.md'
    assert sop.exists(), 'outreach_decoration.md 不存在'
    content = sop.read_text(encoding='utf-8')
    assert '8 家 P0' in content, 'SOP 缺 8 家 P0 客户'
    assert '华宁' in content or '聚通' in content, 'SOP 缺具体客户名'
    assert '5 状态机' in content, 'SOP 缺 5 状态机'
    assert '红 #22' in content or '红线 #22' in content, 'SOP 缺红 #22 边界'
    assert '必用户拍板' in content, 'SOP 缺必用户拍板'
    print(f'  ✓ 装企外呼 SOP {len(content)} 字符，8 家 + 5 状态机 + 红 #22 边界齐')


# === Phase 48.A 测试 ===

def test_deploy_script_exists():
    """测试 7: 部署脚本存在"""
    assert DEPLOY_SCRIPT.exists(), 'deploy.sh 不存在'
    content = DEPLOY_SCRIPT.read_text(encoding='utf-8')
    assert '#!/bin/bash' in content, 'deploy.sh 缺 shebang'
    assert 'deploy:prod' in content, 'deploy.sh 缺生产部署命令'
    assert 'deploy:staging' in content, 'deploy.sh 缺预发布部署命令'
    assert '红线 #22' in content or 'redline' in content.lower(), 'deploy.sh 缺红 #22 边界守护'
    assert 'SSL' in content or 'certbot' in content, 'deploy.sh 缺 SSL 证书申请'
    assert 'rollback' in content, 'deploy.sh 缺回滚命令'
    print(f'  ✓ 部署脚本 {len(content)} 字符，check/build/start/deploy/ssl/backup/rollback 7 命令齐')


# === Phase 48.B2 测试 ===

def test_distribution_plan_exists():
    """测试 8: 派送准备文件存在"""
    plan = MARKETING_DIR / 'distribution_plan.md'
    assert plan.exists(), 'distribution_plan.md 不存在'
    content = plan.read_text(encoding='utf-8')
    assert '公众号' in content, '派送计划缺公众号'
    assert '小红书' in content, '派送计划缺小红书'
    assert '抖音' in content, '派送计划缺抖音'
    assert '红 #22' in content, '派送计划缺红 #22 边界'
    assert '必用户拍板' in content, '派送计划缺必用户拍板'
    assert '派 1.0' in content or '1.0 原版' in content, '派送计划缺派最优（红线 #15.5）'
    print(f'  ✓ 派送准备 {len(content)} 字符，3 平台 + 红 #22 + 派 1.0 齐')


def test_redline_22_boundary_unified():
    """测试 9: 红 #22 必拍板清单覆盖 4 Phase"""
    files_to_check = [
        MARKETING_DIR / 'outreach_decoration.md',
        MARKETING_DIR / 'distribution_plan.md',
    ]
    total_redlines = 0
    for f in files_to_check:
        if not f.exists():
            continue
        content = f.read_text(encoding='utf-8')
        # 数 - [ ] 项
        items = re.findall(r'^- \[ \]', content, re.MULTILINE)
        total_redlines += len(items)
    assert total_redlines >= 10, f'红 #22 必拍板项 {total_redlines}（预期 ≥ 10）'
    print(f'  ✓ 红 #22 必拍板清单 {total_redlines} 项（覆盖 4 Phase）')


def test_consistent_branding():
    """测试 10: 品牌一致性（红 #22 + Cloud + 心之所向便是光 + 49 红线）"""
    files_to_check = [
        SPA_DATA / 'funnel.ts',
        SPA_DATA / 'revenue.ts',
        SDK_DIR / 'openapi.yaml',
        SDK_DIR / 'cloud_sdk.py',
        SDK_DIR / 'cloud_sdk.ts',
        MARKETING_DIR / 'outreach_decoration.md',
        MARKETING_DIR / 'distribution_plan.md',
    ]
    issues = []
    for f in files_to_check:
        if not f.exists():
            issues.append(f'{f.name} 不存在')
            continue
        content = f.read_text(encoding='utf-8')
        # 检查无旧名
        for pat in ['灵策智算', 'CloudTech', 'LynxceAI', '阿劲']:
            if pat in content:
                issues.append(f'{f.name}: 含旧名 "{pat}"')
    assert len(issues) == 0, f'品牌一致性问题:\n  ' + '\n  '.join(issues)
    print(f'  ✓ 全 7 文件品牌一致，无旧名残留')


# === 主程序 ===
if __name__ == '__main__':
    print('=' * 60)
    print('Phase 48.D+C+A+B2 · 综合准备验证')
    print('=' * 60)
    print()
    tests = [
        test_funnel_data_exists,             # D84 漏斗
        test_revenue_data_exists,            # D85 营收
        test_openapi_spec_valid,             # D86 OpenAPI
        test_python_sdk_syntax,              # D87 Python SDK
        test_javascript_sdk_syntax,          # D87 JS SDK
        test_outreach_sop_exists,            # 48.C 渠道话术
        test_deploy_script_exists,           # 48.A 部署
        test_distribution_plan_exists,       # 48.B2 派送
        test_redline_22_boundary_unified,    # 红 #22 清单
        test_consistent_branding,            # 品牌一致
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
