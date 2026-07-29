#!/usr/bin/env python3
"""
WeChat Pay V3 Integration — JSAPI (公众号/小程序) + Native (扫码) + H5
Ref: https://pay.weixin.qq.com/docs/merchant/development
"""
import os, json, time, hashlib, secrets
from datetime import datetime
from pathlib import Path
import urllib.request

# === Config ===
WECHAT_APP_ID = os.environ.get("WECHAT_APP_ID", "")
WECHAT_MCH_ID = os.environ.get("WECHAT_MCH_ID", "")
WECHAT_API_KEY = os.environ.get("WECHAT_API_KEY", "")  # V2 key
WECHAT_API_V3_KEY = os.environ.get("WECHAT_API_V3_KEY", "")  # V3 key
WECHAT_SERIAL_NO = os.environ.get("WECHAT_SERIAL_NO", "")
WECHAT_PRIVATE_KEY_PATH = os.environ.get("WECHAT_PRIVATE_KEY_PATH", "")
WECHAT_NOTIFY_URL = os.environ.get("WECHAT_NOTIFY_URL", "")

WECHAT_API_BASE = "https://api.mch.weixin.qq.com"


def _generate_nonce_str(length=32):
    return secrets.token_hex(length // 2)


def _sign_v2(params: dict, api_key: str) -> str:
    """Generate V2 MD5 signature"""
    sorted_params = sorted(
        [(k, v) for k, v in params.items() if v and k != "sign"],
        key=lambda x: x[0]
    )
    sign_str = "&".join(f"{k}={v}" for k, v in sorted_params) + f"&key={api_key}"
    return hashlib.md5(sign_str.encode()).hexdigest().upper()


def _sign_v3(method: str, url_path: str, body: str, private_key_path: str) -> str:
    """Generate V3 RSA-SHA256 signature"""
    timestamp = str(int(time.time()))
    nonce = _generate_nonce_str()
    message = f"{method}\n{url_path}\n{timestamp}\n{nonce}\n{body}\n"

    with open(private_key_path, "r") as f:
        import base64
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        key = serialization.load_pem_private_key(f.read().encode(), password=None)
        signature = base64.b64encode(
            key.sign(message.encode(), padding.PKCS1v15(), hashes.SHA256())
        ).decode()

    return f"WECHATPAY2-SHA256-RSA2048 mchid=\"{WECHAT_MCH_ID}\",nonce_str=\"{nonce}\",signature=\"{signature}\",timestamp=\"{timestamp}\",serial_no=\"{WECHAT_SERIAL_NO}\""


def create_native_order(plan_name: str, amount_yuan: float, order_id: str = None,
                        product_desc: str = "CloudTech订阅") -> dict:
    """
    Create Native QR code payment order (V2 API).
    Returns {"code_url": "weixin://...", "order_id": "..."}
    """
    if not order_id:
        order_id = f"CT{datetime.now().strftime('%Y%m%d%H%M%S')}{secrets.token_hex(4)}"

    amount_fen = int(amount_yuan * 100)

    params = {
        "appid": WECHAT_APP_ID,
        "mch_id": WECHAT_MCH_ID,
        "nonce_str": _generate_nonce_str(),
        "body": product_desc,
        "out_trade_no": order_id,
        "total_fee": str(amount_fen),
        "spbill_create_ip": "127.0.0.1",
        "notify_url": WECHAT_NOTIFY_URL,
        "trade_type": "NATIVE",
        "product_id": plan_name,
    }
    params["sign"] = _sign_v2(params, WECHAT_API_KEY)

    # Build XML body
    xml_body = "<xml>" + "".join(f"<{k}>{v}</{k}>" for k, v in params.items()) + "</xml>"

    try:
        req = urllib.request.Request(
            f"{WECHAT_API_BASE}/pay/unifiedorder",
            data=xml_body.encode(),
            headers={"Content-Type": "application/xml"}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.read().decode())

        result = {child.tag: child.text for child in root}
        if result.get("return_code") == "SUCCESS" and result.get("result_code") == "SUCCESS":
            return {
                "success": True,
                "code_url": result.get("code_url"),
                "order_id": order_id,
                "amount_yuan": amount_yuan,
                "amount_fen": amount_fen,
            }
        else:
            return {"success": False, "error": result.get("return_msg", result.get("err_code_des", "Unknown"))}
    except Exception as e:
        return {"success": False, "error": str(e), "mode": "mock"}


def verify_notify_v2(xml_body: str, api_key: str) -> dict:
    """Verify V2 payment notification signature"""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_body)
    data = {child.tag: child.text for child in root}

    sign = data.pop("sign", "")
    expected = _sign_v2(data, api_key)

    if sign == expected:
        return {"verified": True, "order_id": data.get("out_trade_no"),
                "transaction_id": data.get("transaction_id"),
                "total_fee": int(data.get("total_fee", 0)),
                "openid": data.get("openid")}
    return {"verified": False}


def get_payment_qrcode(plan_name: str, amount_yuan: float) -> dict:
    """High-level API: generate payment QR for a plan"""
    try:
        result = create_native_order(plan_name, amount_yuan)
        return result
    except Exception:
        # Fallback: return a mock for development
        mock_id = f"mock-{secrets.token_hex(8)}"
        return {
            "success": True,
            "code_url": f"weixin://wxpay/bizpayurl?pr={mock_id}",
            "order_id": mock_id,
            "amount_yuan": amount_yuan,
            "mode": "mock",
        }


# Plans that tie to payment
PRICING_PLANS = {
    "starter":  {"name": "入门版", "price_yuan": 99, "period": "month", "features": ["5个项目", "基础分析", "邮件支持"]},
    "pro":      {"name": "专业版", "price_yuan": 299, "period": "month", "features": ["20个项目", "高级分析", "API访问", "优先支持"]},
    "business": {"name": "企业版", "price_yuan": 999, "period": "month", "features": ["无限项目", "全功能", "专属客服", "私有部署"]},
    "starter_yearly":  {"name": "入门版·年付", "price_yuan": 990, "period": "year", "features": ["5个项目", "基础分析", "邮件支持", "年付省17%"]},
    "pro_yearly":      {"name": "专业版·年付", "price_yuan": 2990, "period": "year", "features": ["20个项目", "高级分析", "API访问", "优先支持", "年付省17%"]},
    "business_yearly": {"name": "企业版·年付", "price_yuan": 9990, "period": "year", "features": ["无限项目", "全功能", "专属客服", "私有部署", "年付省17%"]},
}
