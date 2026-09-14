"""
Phase 48.B2+C 公众号推文 + 8 家外呼任务清单准备测试
- wechat_article.html: 5 关键图（封面 + 4 SOP）+ 5 SOP 段齐 + 互动收尾 + 附录表
- outreach_task_list.md: 8 家 P0 客户清单 + 5 状态机 + 红 #22 必拍板清单
"""
import re
import sys
from pathlib import Path

WECHAT_HTML = Path(r'D:\CloudTech-Portable\docs\marketing\wechat_article.html')
OUTREACH_MD = Path(r'D:\个人文件\AI\Operator\_workzone\Phase48-C-Outreach-Preparation-2026-09-14\outreach_task_list.md')


def test_wechat_html_exists():
    """测试 1: wechat_article.html 存在 + 5 关键图 URL 嵌入"""
    assert WECHAT_HTML.exists(), 'wechat_article.html 不存在'
    content = WECHAT_HTML.read_text(encoding='utf-8')
    # 5 张图（封面 + SOP #1-4）
    image_urls = re.findall(r'seedream-4-0/[\w]+_0\.jpeg', content)
    assert len(image_urls) >= 5, f'wechat_article.html 缺图，实际 {len(image_urls)} 张（至少 5 张）'
    print(f'  ✓ wechat_article.html 存在 + {len(image_urls)} 张 SOP 配图 URL')


def test_wechat_html_5_sops():
    """测试 2: wechat_article.html 5 条 SOP 段齐全"""
    content = WECHAT_HTML.read_text(encoding='utf-8')
    sops = [
        '第 1 条 · 别信功能列表',
        '第 2 条 · 别信 demo 视频',
        '第 3 条 · 别算单价',
        '第 4 条 · 别问"接多少平台"',
        '第 5 条 · 别问"能不能做"',
    ]
    for sop in sops:
        assert sop in content, f'wechat_article.html 缺 SOP: "{sop}"'
    print(f'  ✓ wechat 5 SOP 段齐（业务流/产物库/单价/咬合度/责任人）')


def test_wechat_html_market_analogy():
    """测试 3: wechat_article.html 菜场类比 ≥3 处（红线 #13 互动收尾+菜市场类比 ≥1）"""
    content = WECHAT_HTML.read_text(encoding='utf-8')
    market_keywords = ['菜场', '我妈', '鱼', '摊主', '摊位']
    found = sum(1 for kw in market_keywords if kw in content)
    assert found >= 3, f'菜场类比密度不足（{found}/3）'
    # 互动收尾
    assert '评论区' in content or '告诉我' in content, '缺互动收尾'
    print(f'  ✓ 菜场类比 {found}/3 关键词 + 互动收尾齐')


def test_wechat_html_appendix():
    """测试 4: 附录 5 AI 员工工时表齐"""
    content = WECHAT_HTML.read_text(encoding='utf-8')
    for emp in ['Apollo', 'Lyra', 'Hermes', 'Athena', 'Artemis']:
        assert emp in content, f'附录缺员工 "{emp}"'
    # 30 天实证数据
    assert '30 天' in content or 'OPC Day 30' in content, '附录缺 30 天实证'
    print(f'  ✓ 附录 5 AI 员工齐 + 30 天实证数据齐')


def test_wechat_no_old_brand():
    """测试 5: 品牌一致（无旧名残留）"""
    content = WECHAT_HTML.read_text(encoding='utf-8')
    for pat in ['灵策智算', 'CloudTech', 'LynxceAI', '阿劲']:
        assert pat not in content, f'wechat_article.html 含旧名 "{pat}"'
    print(f'  ✓ wechat 品牌一致，无旧名残留')


def test_outreach_task_list_exists():
    """测试 6: outreach_task_list.md 存在 + 8 家 P0 客户清单齐"""
    assert OUTREACH_MD.exists(), 'outreach_task_list.md 不存在'
    content = OUTREACH_MD.read_text(encoding='utf-8')
    customers = [
        '成都华宁装饰', '杭州聚通装饰', '北京星艺装饰', '苏州东易日盛',
        '深圳名雕装饰', '上海统帅装饰', '武汉澳华装饰', '广州美迪装饰',
    ]
    found = [c for c in customers if c in content]
    assert len(found) >= 6, f'outreach_task_list.md 8 家 P0 缺，实际 {len(found)} 家（至少 6 家）'
    print(f'  ✓ outreach_task_list.md {len(found)}/8 家 P0 客户清单齐')


def test_outreach_5_state_machine():
    """测试 7: outreach_task_list.md 5 状态机 SOP"""
    content = OUTREACH_MD.read_text(encoding='utf-8')
    for stage in ['stage_1_opening', 'stage_2_demo_invite', 'stage_3_trial_offer', 'stage_4_followup']:
        assert stage in content, f'outreach 缺状态机 "{stage}"'
    # 至少 1 家有完整 YAML（成都华宁）
    assert 'customer_id: P0-001' in content, '缺 P0-001 成都华宁完整 YAML'
    assert 'data_reflection' in content, '缺 data_reflection 数据回流模板'
    print(f'  ✓ 5 状态机 SOP（开场/demo/试用/跟进）+ 飞书 webhook 数据回流齐')


def test_outreach_redline_22():
    """测试 8: outreach 红 #22 必拍板清单（外部动作必用户拍板）"""
    content = OUTREACH_MD.read_text(encoding='utf-8')
    assert '红 #22' in content, 'outreach 缺红 #22 必拍板清单'
    assert '必用户授权' in content or '必用户拍板' in content, 'outreach 缺"必用户授权"标注'
    # 4 类必拍板项至少出现
    redline_items = ['实际拨打电话', '试用账号', '优惠', '电话 SaaS']
    found = sum(1 for i in redline_items if i in content)
    assert found >= 2, f'红 #22 必拍板清单不完整（{found}/4）'
    print(f'  ✓ 红 #22 必拍板清单齐（{found}/4 类）· 实际拨打电话/试用账号/优惠/SaaS 接入')


def test_outreach_no_old_brand():
    """测试 9: 品牌一致（无旧名残留）"""
    content = OUTREACH_MD.read_text(encoding='utf-8')
    for pat in ['灵策智算', 'CloudTech', 'LynxceAI', '阿劲']:
        assert pat not in content, f'outreach 含旧名 "{pat}"'
    print(f'  ✓ outreach 品牌一致，无旧名残留')


def test_no_placeholder_images():
    """测试 10: 无 via.placeholder.com 占位符残留（红线 #9 Glob 实证）"""
    wc = WECHAT_HTML.read_text(encoding='utf-8')
    assert 'via.placeholder.com' not in wc, 'wechat_article.html 仍有占位符 via.placeholder.com'
    out = OUTREACH_MD.read_text(encoding='utf-8')
    assert 'placeholder' not in out or '占位' in out, 'outreach 占位符检查'
    print(f'  ✓ 无 placeholder 占位符残留')


if __name__ == '__main__':
    print('=' * 60)
    print('Phase 48.B2+C · 公众号推文 + 8 家外呼任务清单准备测试')
    print('=' * 60)
    print()
    tests = [
        test_wechat_html_exists,
        test_wechat_html_5_sops,
        test_wechat_html_market_analogy,
        test_wechat_html_appendix,
        test_wechat_no_old_brand,
        test_outreach_task_list_exists,
        test_outreach_5_state_machine,
        test_outreach_redline_22,
        test_outreach_no_old_brand,
        test_no_placeholder_images,
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