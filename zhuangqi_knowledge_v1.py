"""
装企垂直知识库 v1 — Decoration Industry Knowledge Base
=========================================================
漳州本地装修知识库：小区数据、户型体系、工价标准、材料价格、政策法规、设计师资源

数据来源: 公开信息 + 行业经验 + 政策文件
更新频率: 季度更新
"""
import json
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
KB_DIR = BASE / "data" / "knowledge"
KB_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════
# 一、漳州小区数据库
# ═══════════════════════════════════

COMMUNITIES = {
    "龙文区": [
        {"name": "碧湖万达广场", "type": "商品房", "year": 2015, "avg_price": 12000, "units": 2000,
         "features": ["碧湖公园旁", "万达商圈", "学区房"], "common_area": [85, 120, 140]},
        {"name": "建发央著", "type": "商品房", "year": 2019, "avg_price": 15000, "units": 1500,
         "features": ["品牌开发商", "高端社区", "中式园林"], "common_area": [95, 125, 160]},
        {"name": "万科城", "type": "商品房", "year": 2018, "avg_price": 13500, "units": 3000,
         "features": ["万科物业", "大社区", "配套齐全"], "common_area": [88, 115, 140]},
        {"name": "龙文花园", "type": "安置房", "year": 2012, "avg_price": 8000, "units": 1500,
         "features": ["性价比高", "交通便利"], "common_area": [70, 90, 120]},
        {"name": "明发商业广场", "type": "商住", "year": 2014, "avg_price": 9500, "units": 1800,
         "features": ["商业配套", "地铁规划"], "common_area": [45, 65, 89]},
        {"name": "锦绣一方", "type": "商品房", "year": 2016, "avg_price": 11000, "units": 1200,
         "features": ["园林小区", "安静宜居"], "common_area": [90, 120, 140]},
        {"name": "龙江新苑", "type": "商品房", "year": 2020, "avg_price": 13000, "units": 800,
         "features": ["新小区", "户型好"], "common_area": [89, 110, 135]},
    ],
    "芗城区": [
        {"name": "建发缦云", "type": "商品房", "year": 2021, "avg_price": 16000, "units": 1200,
         "features": ["顶级楼盘", "景观好", "建发品牌"], "common_area": [105, 135, 180]},
        {"name": "大唐世家", "type": "商品房", "year": 2017, "avg_price": 12000, "units": 2500,
         "features": ["老城区", "配套成熟", "学区"], "common_area": [85, 110, 140]},
        {"name": "漳州万科城", "type": "商品房", "year": 2019, "avg_price": 14000, "units": 2000,
         "features": ["大社区", "万科品质"], "common_area": [88, 115, 143]},
        {"name": "新华西新村", "type": "老旧小区", "year": 2005, "avg_price": 7000, "units": 800,
         "features": ["市中心", "周边便利", "学区"], "common_area": [60, 80, 100]},
        {"name": "西湖生态园", "type": "商品房", "year": 2022, "avg_price": 12000, "units": 1000,
         "features": ["新盘", "西湖景观"], "common_area": [89, 115, 140]},
    ],
    "龙海区": [
        {"name": "港龙花园", "type": "商品房", "year": 2018, "avg_price": 9000, "units": 1000,
         "features": ["海边", "度假"], "common_area": [88, 110, 140]},
        {"name": "角美万达", "type": "商品房", "year": 2016, "avg_price": 10000, "units": 2000,
         "features": ["商业配套", "地铁规划"], "common_area": [85, 115, 140]},
    ],
    "漳州开发区": [
        {"name": "招商花园城", "type": "商品房", "year": 2019, "avg_price": 11000, "units": 1500,
         "features": ["招商品牌", "配套好"], "common_area": [89, 120, 145]},
    ],
}

# ═══════════════════════════════════
# 二、装修风格体系（含漳州本地流行度）
# ═══════════════════════════════════

STYLE_SYSTEM = {
    "现代简约": {
        "local_popularity": "⭐⭐⭐⭐⭐",  # 漳州最流行
        "price_range": (800, 1500),  # 元/平
        "key_elements": ["大面积白色", "无主灯设计", "通铺瓷砖", "极简线条"],
        "suitable_areas": [80, 150],
        "avoid": ["过于复杂的吊顶", "深色大面积墙面", "欧式线条"],
    },
    "奶油风": {
        "local_popularity": "⭐⭐⭐⭐⭐",
        "price_range": (1000, 1800),
        "key_elements": ["奶咖色系", "弧形元素", "原木点缀", "柔和灯光"],
        "suitable_areas": [60, 140],
        "avoid": ["冷色调", "硬朗直线", "深色地板"],
    },
    "新中式": {
        "local_popularity": "⭐⭐⭐⭐",
        "price_range": (1500, 3000),
        "key_elements": ["实木家具", "水墨元素", "对称布局", "暖色灯光"],
        "suitable_areas": [100, 200],
        "avoid": ["过于繁复", "假中式", "红木泛滥"],
    },
    "侘寂风": {
        "local_popularity": "⭐⭐⭐",
        "price_range": (1200, 2500),
        "key_elements": ["微水泥", "自然材质", "做旧质感", "留白"],
        "suitable_areas": [80, 160],
        "avoid": ["光面材质", "鲜艳色彩", "复杂装饰"],
    },
    "轻法式": {
        "local_popularity": "⭐⭐⭐",
        "price_range": (1200, 2200),
        "key_elements": ["石膏线条", "拱门元素", "人字拼地板", "奶油色调"],
        "suitable_areas": [90, 160],
        "avoid": ["过于华丽", "大面积金色", "沉重家具"],
    },
    "工业风": {
        "local_popularity": "⭐⭐",
        "price_range": (800, 1500),
        "key_elements": ["裸露墙面", "金属元素", "轨道灯", "水泥质感"],
        "suitable_areas": [50, 120],
        "avoid": ["过度冰冷", "没有软装过渡"],
    },
}

# ═══════════════════════════════════
# 三、工价标准（漳州2026年参考）
# ═══════════════════════════════════

LABOR_COST = {
    "水电改造": {
        "price_range": (45, 65), "unit": "元/平",
        "includes": ["开槽", "布管", "穿线", "打压测试"],
        "tips": "按建筑面积算。老房水电全改约增加30%。",
        "duration_days": (3, 7),
    },
    "泥瓦工": {
        "price_range": (50, 80), "unit": "元/平",
        "includes": ["找平", "防水", "贴砖", "美缝"],
        "tips": "大砖（750×1500以上）工费加20%。美缝单独算8-15元/平。",
        "duration_days": (7, 15),
    },
    "木工": {
        "price_range": (60, 120), "unit": "元/平（投影面积）",
        "includes": ["吊顶", "柜体", "背景墙"],
        "tips": "定制柜体按投影面积算。生态板比颗粒板贵30%。",
        "duration_days": (7, 14),
    },
    "油漆工": {
        "price_range": (25, 40), "unit": "元/平",
        "includes": ["批灰", "打磨", "底漆", "面漆"],
        "tips": "腻子粉用耐水型。乳胶漆建议多乐士/立邦中端线以上。",
        "duration_days": (5, 10),
    },
    "全屋定制安装": {
        "price_range": (80, 150), "unit": "元/平",
        "tips": "含橱柜+衣柜+榻榻米。本地工厂比品牌便宜40%。",
        "duration_days": (3, 5),
    },
}

# ═══════════════════════════════════
# 四、材料价格参考（漳州本地市场）
# ═══════════════════════════════════

MATERIAL_PRICE = {
    "瓷砖": {
        "budget": (40, 80), "mid": (80, 150), "premium": (150, 400),
        "unit": "元/片(800×800)",
        "brands": ["马可波罗", "东鹏", "诺贝尔", "冠珠"],
        "本地购买": "漳州吉马国际家居广场/红星美凯龙",
        "tips": "广东砖质量好。运费约200-500元/车。",
    },
    "地板": {
        "实木": (200, 500), "多层实木": (150, 300), "强化": (60, 150),
        "unit": "元/平",
        "brands": ["圣象", "大自然", "德尔", "生活家"],
        "闽南适配": "漳州回南天严重，不建议纯实木，推荐多层实木/SPC石塑地板",
    },
    "橱柜": {
        "budget": (3000, 6000), "mid": (6000, 12000), "premium": (12000, 25000),
        "unit": "元/套（含台面）",
        "台面": {"石英石": (300, 600), "岩板": (800, 2000), "不锈钢": (400, 800)},
        "tips": "本地橱柜厂比欧派/金牌便宜50%，质量不差",
    },
    "卫浴": {
        "马桶": {"普通": (800, 2000), "智能": (2000, 8000)},
        "花洒": {"普通": (300, 800), "恒温": (800, 2500)},
        "浴室柜": {"成品": (1000, 3000), "定制": (1500, 5000)},
        "brands": ["九牧", "箭牌", "恒洁", "科勒", "TOTO"],
    },
    "油漆": {
        "乳胶漆": {"国产中端": (300, 600), "进口": (800, 2000)},
        "unit": "元/桶(18L)",
        "闽南适配": "回南天选防霉款。推荐多乐士抗甲醛/立邦净味",
        "用量": "100平房子约需3-4桶面漆+2桶底漆",
    },
    "门窗": {
        "断桥铝": (600, 1200), "unit": "元/平",
        "brands": ["凤铝", "中铝", "兴发"],
        "闽南适配": "台风区选≥1.8mm壁厚，5+20A+5中空钢化玻璃",
    },
}

# ═══════════════════════════════════
# 五、装修预算速算表
# ═══════════════════════════════════

BUDGET_REFERENCE = {
    "经济型": {
        "range": (800, 1200), "unit": "元/平",
        "description": "满足基本居住需求，材料以国产中端为主",
        "breakdown": {
            "设计费": "0（自己设计或免费设计）",
            "硬装": "60%（水电+泥瓦+木工+油漆）",
            "主材": "25%（瓷砖+地板+门窗+卫浴）",
            "软装": "10%（家具+窗帘+灯具）",
            "家电": "5%",
        },
    },
    "舒适型": {
        "range": (1200, 2000),
        "description": "品质装修，品牌材料+定制柜体+智能家居基础",
        "breakdown": {
            "设计费": "3-5%（约3000-8000元）",
            "硬装": "50%",
            "主材": "25%",
            "软装": "15%",
            "家电": "10%",
        },
    },
    "轻奢型": {
        "range": (2000, 3500),
        "description": "高端装修，进口材料+全屋智能+设计师全程跟进",
        "breakdown": {
            "设计费": "5-8%（约1-3万）",
            "硬装": "40%",
            "主材": "30%",
            "软装": "20%",
            "家电": "10%",
        },
    },
}

# ═══════════════════════════════════
# 六、装修流程标准工期
# ═══════════════════════════════════

TIMELINE = [
    {"stage": "设计确认", "days": (5, 10), "milestones": ["量房", "平面方案", "效果图", "施工图"]},
    {"stage": "主体拆改", "days": (3, 7), "milestones": ["拆墙", "砌墙", "铲墙皮"]},
    {"stage": "水电改造", "days": (5, 10), "milestones": ["定位", "开槽", "布管", "穿线", "打压"]},
    {"stage": "泥瓦施工", "days": (10, 20), "milestones": ["防水", "闭水试验", "贴砖", "美缝"]},
    {"stage": "木工施工", "days": (7, 15), "milestones": ["吊顶", "柜体", "背景墙"]},
    {"stage": "油漆施工", "days": (7, 14), "milestones": ["批灰", "打磨", "底漆", "面漆"]},
    {"stage": "安装收尾", "days": (5, 10), "milestones": ["灯具", "洁具", "开关面板", "开荒保洁"]},
    {"stage": "软装进场", "days": (3, 7), "milestones": ["家具", "窗帘", "装饰画", "绿植"]},
    {"stage": "通风验收", "days": (15, 30), "milestones": ["甲醛检测", "竣工验收"]},
]
TOTAL_DURATION_RANGE = (60, 120)  # 总工期范围(天)

# ═══════════════════════════════════
# 七、闽南装修特有问题
# ═══════════════════════════════════

LOCAL_ISSUES = {
    "回南天": {
        "months": "3-5月",
        "影响": ["墙面发霉", "木制品膨胀", "油漆难干"],
        "解决方案": [
            "墙面用耐水腻子+防霉乳胶漆",
            "地板选多层实木或SPC石塑",
            "柜体背板做防潮处理",
            "安装除湿机/新风系统",
            "回南天期间避免油漆施工",
        ],
        "content_angle": "漳州回南天装修避坑指南：这5个地方没做好，一年后全发霉",
    },
    "台风": {
        "months": "7-9月",
        "影响": ["漏水", "窗户损坏", "阳台积水"],
        "解决方案": [
            "窗户选1.8mm以上断桥铝",
            "阳台地漏做大尺寸+坡度",
            "外墙防水做足3遍",
            "空调外机加固安装",
        ],
        "content_angle": "漳州台风天装修：窗户选错一年白干",
    },
    "高温": {
        "months": "6-9月",
        "影响": ["油漆开裂", "瓷砖空鼓", "工人效率低"],
        "解决方案": [
            "瓷砖铺贴前充分泡水",
            "油漆施工避免高温时段",
            "水泥砂浆加缓凝剂",
            "合理安排工期避开酷暑关键节点",
        ],
    },
}

# ═══════════════════════════════════
# 八、政策法规（2026）
# ═══════════════════════════════════

POLICIES = {
    "公积金装修提取": {
        "政策": "漳州公积金支持装修提取",
        "条件": ["购房5年内", "公积金连续缴存满6个月", "1年内未提取过"],
        "额度": "1400元/㎡ × 房屋面积，最高20万元",
        "材料": ["身份证", "房产证/购房合同", "装修合同", "装修预算清单"],
        "办理": "漳州市住房公积金管理中心（漳福路46号）",
        "时效": "材料齐全约5个工作日",
        "限制": "资金使用率>95%时可能暂停受理",
    },
    "以旧换新补贴": {
        "政策": "2026年消费品以旧换新——家装类",
        "范围": ["厨卫改造", "门窗更换", "墙面翻新"],
        "补贴": "按实际消费金额10-15%补贴，最高5000元",
        "申请": "通过云闪付APP或线下指定渠道",
        "注意": "需在政府指定商户消费，保留发票",
    },
    "装修消费贷": {
        "政策": "多家银行推出装修消费贷",
        "利率": "年化3.5-5.5%（2026年）",
        "额度": "5-50万",
        "条件": ["稳定收入", "征信良好"],
        "推荐": "建行装修分期、招行消费贷、工行家装贷",
    },
}

# ═══════════════════════════════════
# 查询 API
# ═══════════════════════════════════

def search_community(query: str = None, district: str = None) -> dict:
    """搜索小区"""
    results = []
    for dist, comms in COMMUNITIES.items():
        if district and district != dist:
            continue
        for c in comms:
            if query:
                if query in c["name"] or query in c.get("features", []):
                    results.append({"district": dist, **c})
            else:
                results.append({"district": dist, **c})
    return {"ok": True, "total": len(results), "results": results}


def get_style_guide(style: str) -> dict:
    """获取风格指南"""
    s = STYLE_SYSTEM.get(style)
    if not s:
        return {"ok": False, "error": f"风格不存在。可用: {list(STYLE_SYSTEM.keys())}"}
    return {"ok": True, "style": style, **s}


def estimate_budget(area: float, level: str = "舒适型", style: str = "现代简约") -> dict:
    """估算装修预算"""
    budget_ref = BUDGET_REFERENCE.get(level, BUDGET_REFERENCE["舒适型"])
    low, high = budget_ref["range"]
    total_low = area * low
    total_high = area * high

    # 风格修正
    style_multiplier = 1.0
    style_info = STYLE_SYSTEM.get(style, {})
    if style_info:
        sl, sh = style_info.get("price_range", (1000, 1500))
        style_multiplier = (sl + sh) / 2 / ((low + high) / 2)

    return {
        "ok": True,
        "area": area,
        "level": level,
        "style": style,
        "unit_price_range": (low, high),
        "total_range": (round(total_low), round(total_high)),
        "style_adjusted_range": (
            round(total_low * style_multiplier),
            round(total_high * style_multiplier),
        ),
        "breakdown": {
            k: f"≈{round(total_low * float(v.replace('%', '')) / 100) if '%' in v and v.replace('%', '').isdigit() else v}元 — {round(total_high * float(v.replace('%', '')) / 100) if '%' in v and v.replace('%', '').isdigit() else v}元"
            for k, v in budget_ref["breakdown"].items()
        },
        "timeline_days": TOTAL_DURATION_RANGE,
    }


def get_material_guide(material: str = None) -> dict:
    """获取材料选购指南"""
    if material:
        m = MATERIAL_PRICE.get(material)
        if not m:
            return {"ok": False, "error": f"材料类型不存在。可用: {list(MATERIAL_PRICE.keys())}"}
        return {"ok": True, "material": material, **m}
    return {"ok": True, "materials": list(MATERIAL_PRICE.keys()), "data": MATERIAL_PRICE}


def get_local_issues() -> dict:
    """获取闽南本地装修特有问题及解决方案"""
    return {"ok": True, "issues": LOCAL_ISSUES}


def get_policies() -> dict:
    """获取装修相关政策"""
    return {"ok": True, "policies": POLICIES}


def get_labor_cost() -> dict:
    """获取工价参考"""
    return {"ok": True, "labor_costs": LABOR_COST}


def get_timeline() -> dict:
    """获取装修标准工期"""
    return {
        "ok": True,
        "timeline": TIMELINE,
        "total_days_range": TOTAL_DURATION_RANGE,
    }


def full_knowledge_dump(topic: str = None) -> dict:
    """
    按主题获取知识库内容（给 AI 生成用的上下文注入）

    topic: community/style/budget/material/labor/issues/policies/all
    """
    if topic == "community" or topic == "all":
        return {"ok": True, "topic": topic, "knowledge": _format_knowledge_for_ai(topic)}

    mappers = {
        "style": lambda: STYLE_SYSTEM,
        "budget": lambda: BUDGET_REFERENCE,
        "material": lambda: MATERIAL_PRICE,
        "labor": lambda: LABOR_COST,
        "issues": lambda: LOCAL_ISSUES,
        "policies": lambda: POLICIES,
    }

    if topic in mappers:
        return {"ok": True, "topic": topic, "knowledge": mappers[topic]()}

    return {"ok": False, "error": f"未知主题。可用: {list(mappers.keys())} + community/all"}


def _format_knowledge_for_ai(topic: str) -> str:
    """将知识库内容格式化为 AI 可读的上下文字符串"""
    parts = []

    if topic in ("community", "all"):
        parts.append("## 漳州小区数据")
        for dist, comms in COMMUNITIES.items():
            parts.append(f"\n### {dist}")
            for c in comms[:5]:
                parts.append(f"- {c['name']} | {c['type']} | {c['year']}年 | 均价{c['avg_price']}元 | 常见户型: {c['common_area']}平 | {', '.join(c['features'])}")

    if topic in ("style", "all"):
        parts.append("\n## 装修风格体系")
        for name, info in STYLE_SYSTEM.items():
            parts.append(f"- {name}: 流行度{info['local_popularity']} | 造价{info['price_range'][0]}-{info['price_range'][1]}元/平 | 适合{info['suitable_areas'][0]}-{info['suitable_areas'][1]}平")

    if topic in ("budget", "all"):
        parts.append("\n## 预算参考")
        for level, info in BUDGET_REFERENCE.items():
            parts.append(f"- {level}: {info['range'][0]}-{info['range'][1]}元/平 | {info['description']}")

    if topic in ("material", "all"):
        parts.append("\n## 材料价格参考（漳州）")
        for name, info in MATERIAL_PRICE.items():
            parts.append(f"- {name}: {json.dumps(info, ensure_ascii=False)[:150]}")

    if topic in ("labor", "all"):
        parts.append("\n## 人工费用参考")
        for name, info in LABOR_COST.items():
            parts.append(f"- {name}: {info['price_range'][0]}-{info['price_range'][1]}{info['unit']} | {info.get('tips', '')[:80]}")

    if topic in ("issues", "all"):
        parts.append("\n## 闽南装修特有问题")
        for name, info in LOCAL_ISSUES.items():
            parts.append(f"- {name}({info['months']}): {'; '.join(info['解决方案'][:2])}")

    if topic in ("policies", "all"):
        parts.append("\n## 装修政策")
        for name, info in POLICIES.items():
            parts.append(f"- {name}: {info.get('额度', info.get('利率', info.get('补贴', '')))}")

    return "\n".join(parts)


# ═══════════════════════════════════
# 数据持久化
# ═══════════════════════════════════

def save_knowledge_base():
    """保存知识库到 JSON 文件"""
    data = {
        "communities": COMMUNITIES,
        "styles": STYLE_SYSTEM,
        "labor_costs": LABOR_COST,
        "material_prices": MATERIAL_PRICE,
        "budget_reference": BUDGET_REFERENCE,
        "timeline": TIMELINE,
        "local_issues": LOCAL_ISSUES,
        "policies": POLICIES,
        "updated_at": datetime.now().isoformat()[:19],
    }
    kb_file = KB_DIR / "zhuangqi_knowledge_v1.json"
    kb_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "path": str(kb_file), "size_kb": round(len(json.dumps(data, ensure_ascii=False)) / 1024, 1)}


def load_knowledge_base() -> dict:
    """加载知识库"""
    kb_file = KB_DIR / "zhuangqi_knowledge_v1.json"
    if kb_file.exists():
        return json.loads(kb_file.read_text(encoding="utf-8"))
    return None


# ═══════════════════════════════════
# CLI 测试
# ═══════════════════════════════════

if __name__ == "__main__":
    # 小区搜索
    print(json.dumps(search_community("碧湖"), ensure_ascii=False, indent=2))

    # 预算估算
    budget = estimate_budget(100, "舒适型", "奶油风")
    print(f"\n100平奶油风预算: {budget['total_range'][0]}-{budget['total_range'][1]}万")

    # 保存知识库
    print(json.dumps(save_knowledge_base(), ensure_ascii=False, indent=2))

    # 知识库注入
    kb_context = full_knowledge_dump("all")
    print(f"\n知识库总长度: {len(kb_context.get('knowledge', ''))} 字符")
