"""
云数科技 — License 离线授权系统
==================================
RSA 公钥验证 · 机器指纹绑定 · 过期检测 · 防篡改降级
"""
import json, os, platform, hashlib, base64, subprocess, re
from datetime import datetime, timedelta
from pathlib import Path

HOME = Path(os.environ.get("USERPROFILE", os.path.expanduser("~")))
TOOLS = Path(__file__).parent

# ── 密钥路径 ──
PUBLIC_KEY_PATH = TOOLS / "license_public_key.pem"
LICENSE_FILE = HOME / ".openclaw" / "license.json"
LICENSE_DATA_DIR = HOME / ".openclaw" / "license_data"
LICENSE_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── 宽限期（天） ──
GRACE_DAYS = 3


# ═══════════════════════════════════════════════════════════
# 机器指纹
# ═══════════════════════════════════════════════════════════

def get_machine_id():
    """生成稳定的机器指纹: hostname + MAC 地址 + 卷序列号"""
    hostname = platform.node() or "unknown"

    mac = _get_mac_address()
    volume = _get_volume_serial()

    raw = f"{hostname}:::{mac}:::{volume}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_machine_fingerprint_detailed():
    """返回机器指纹详细组件（用于展示/调试）"""
    hostname = platform.node() or "unknown"
    mac = _get_mac_address()
    volume = _get_volume_serial()
    raw = f"{hostname}:::{mac}:::{volume}"

    return {
        "hostname": hostname,
        "mac": mac,
        "volume_serial": volume,
        "fingerprint": hashlib.sha256(raw.encode()).hexdigest(),
        "os": platform.system(),
        "os_version": platform.version(),
        "machine": platform.machine()
    }


def _get_mac_address():
    """获取 MAC 地址（跨平台）"""
    try:
        if os.name == "nt":
            # Windows
            r = subprocess.run(
                ["getmac", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=5
            )
            for line in r.stdout.split("\n"):
                if line.strip():
                    parts = line.strip().strip('"').split('","')
                    if parts and '-' in parts[0]:
                        return parts[0].replace('-', ':').lower()
        else:
            # Linux/Mac
            r = subprocess.run(
                ["ip", "link"], capture_output=True, text=True, timeout=5
            )
            for line in r.stdout.split("\n"):
                if "link/ether" in line:
                    return line.split("link/ether")[1].strip().split()[0]
    except Exception:
        pass

    # 后备：使用 uuid.getnode
    import uuid
    mac_int = uuid.getnode()
    if mac_int and (mac_int >> 40) % 2 == 0:
        mac_hex = hex(mac_int)[2:].zfill(12)
        return ":".join(mac_hex[i:i+2] for i in range(0, 12, 2))
    return "00:00:00:00:00:00"


def _get_volume_serial():
    """获取系统盘卷序列号"""
    try:
        if os.name == "nt":
            r = subprocess.run(
                ["wmic", "path", "win32_logicaldisk", "where", "DeviceID='C:'",
                 "get", "VolumeSerialNumber", "/value"],
                capture_output=True, text=True, timeout=5
            )
            for line in r.stdout.split("\n"):
                if "VolumeSerialNumber" in line:
                    return line.split("=")[1].strip()
        else:
            # Linux: 使用 blkid 或 stat /
            r = subprocess.run(
                ["stat", "-f", "--format=%S", "/"],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0:
                return r.stdout.strip()
    except Exception:
        pass
    return "NOSERIAL"


# ═══════════════════════════════════════════════════════════
# RSA 操作
# ═══════════════════════════════════════════════════════════

def _load_public_key():
    """加载 RSA 公钥"""
    if not PUBLIC_KEY_PATH.exists():
        return None
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
        with open(PUBLIC_KEY_PATH, "rb") as f:
            return serialization.load_pem_public_key(f.read(), backend=default_backend())
    except ImportError:
        # 无 cryptography -> 回退到 rsa 库
        try:
            import rsa
            with open(PUBLIC_KEY_PATH, "rb") as f:
                return rsa.PublicKey.load_pkcs1(f.read())
        except ImportError:
            return None
    except Exception:
        return None


def _verify_signature(data_bytes, signature_b64):
    """验证 RSA 签名"""
    pub_key = _load_public_key()
    if not pub_key:
        # 无公钥 = 无法验证 -> 返回 False（安全优先）
        return False

    try:
        sig = base64.b64decode(signature_b64)
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding, rsa as rsa_crypto

        if isinstance(pub_key, rsa_crypto.RSAPublicKey):
            pub_key.verify(
                sig,
                data_bytes,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return True
    except (ImportError, Exception):
        pass

    # 回退到 rsa 库
    try:
        import rsa
        sig = base64.b64decode(signature_b64)
        rsa.verify(data_bytes, sig, pub_key)
        return True
    except (ImportError, Exception):
        return False


# ═══════════════════════════════════════════════════════════
# License 核心功能
# ═══════════════════════════════════════════════════════════

def _parse_license_key(license_key):
    """解析 License Key（Base64 JSON 含签名）"""
    try:
        decoded = json.loads(base64.b64decode(license_key).decode("utf-8"))
        required = ["machine_id", "expiry", "features", "signature"]
        for field in required:
            if field not in decoded:
                return {"error": f"License Key 缺少字段: {field}"}

        return decoded
    except Exception as e:
        return {"error": f"License Key 格式错误: {str(e)}"}


def verify_license_key(license_key):
    """
    验证 License Key 的完整性和有效性
    返回: {"valid": bool, "reason": str, "data": dict}
    """
    parsed = _parse_license_key(license_key)
    if "error" in parsed:
        return {"valid": False, "reason": parsed["error"], "data": None}

    # 1. 验证签名
    sig_data = {
        "machine_id": parsed["machine_id"],
        "expiry": parsed["expiry"],
        "features": parsed["features"]
    }
    data_bytes = json.dumps(sig_data, separators=(",", ":"), sort_keys=True).encode("utf-8")

    if not _verify_signature(data_bytes, parsed["signature"]):
        return {"valid": False, "reason": "签名验证失败（License 可能被篡改）", "data": parsed}

    # 2. 验证机器指纹
    current_machine_id = get_machine_id()
    if parsed["machine_id"] != "ANY" and parsed["machine_id"] != current_machine_id:
        return {"valid": False, "reason": "机器指纹不匹配（License 绑定其他设备）", "data": parsed}

    # 3. 验证过期
    try:
        expiry = datetime.fromisoformat(parsed["expiry"])
        if datetime.now() > expiry:
            return {"valid": False, "reason": f"License 已过期（{parsed['expiry']}）", "data": parsed}
    except (ValueError, TypeError):
        return {"valid": False, "reason": "License 过期日期格式错误", "data": parsed}

    return {"valid": True, "reason": "License 有效", "data": parsed}


def activate_license(license_key):
    """
    激活 License
    返回: {"success": bool, "message": str, "license": dict}
    """
    result = verify_license_key(license_key)
    if not result["valid"]:
        return {"success": False, "message": result["reason"]}

    # 保存 License 到本地
    license_data = result["data"]
    license_record = {
        "machine_id": get_machine_id(),
        "license_key_sha256": hashlib.sha256(license_key.encode()).hexdigest(),
        "activated_at": datetime.now().isoformat(),
        "expiry": license_data["expiry"],
        "features": license_data["features"],
        "status": "active"
    }

    LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    LICENSE_FILE.write_text(json.dumps(license_record, ensure_ascii=False, indent=2), "utf-8")

    return {
        "success": True,
        "message": f"License 激活成功，有效期至 {license_data['expiry']}",
        "license": {
            "expiry": license_data["expiry"],
            "features": license_data["features"],
            "status": "active"
        }
    }


def deactivate_license():
    """
    反激活 License（换机器时使用）
    返回: {"success": bool, "message": str}
    """
    if not LICENSE_FILE.exists():
        return {"success": False, "message": "没有已激活的 License"}

    # 读取当前 License 信息
    try:
        license_data = json.loads(LICENSE_FILE.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        license_data = {}

    # 删除本地 License 文件
    try:
        LICENSE_FILE.unlink()
    except OSError:
        pass

    # 记录反激活日志
    deactivate_log = LICENSE_DATA_DIR / "deactivate_log.json"
    logs = []
    if deactivate_log.exists():
        try:
            logs = json.loads(deactivate_log.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    logs.append({
        "machine_id": license_data.get("machine_id", get_machine_id()),
        "deactivated_at": datetime.now().isoformat(),
        "previous_expiry": license_data.get("expiry", "")
    })
    deactivate_log.write_text(json.dumps(logs, ensure_ascii=False, indent=2), "utf-8")

    return {"success": True, "message": "License 已反激活，可在此设备或新设备上重新激活"}


def get_license_status():
    """
    获取当前授权状态（含宽限期计算）
    返回: {"licensed": bool, "plan": str, "tier": str, "expiry": str, "grace_days_left": int, ...}
    """
    if not LICENSE_FILE.exists():
        # 免费版
        return _free_status()

    try:
        license_data = json.loads(LICENSE_FILE.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return _free_status("License 文件损坏")

    # 验证状态
    machine_id = get_machine_id()
    stored_machine = license_data.get("machine_id", "")
    if stored_machine != machine_id:
        return _free_status("机器指纹不匹配")

    # 检查过期
    expiry_str = license_data.get("expiry", "")
    if not expiry_str:
        return _free_status("License 缺少过期日期")

    try:
        expiry = datetime.fromisoformat(expiry_str)
    except (ValueError, TypeError):
        return _free_status("License 过期日期格式错误")

    now = datetime.now()

    if now > expiry:
        # 过期 — 检查宽限期
        grace_end = expiry + timedelta(days=GRACE_DAYS)
        if now <= grace_end:
            # 宽限期内
            grace_days_left = (grace_end - now).days
            features = license_data.get("features", [])
            return {
                "licensed": True,
                "plan": "grace",
                "tier": "专业版（宽限期）",
                "expiry": expiry_str,
                "grace_days_left": grace_days_left,
                "grace_end": grace_end.isoformat(),
                "features": features,
                "status": "grace",
                "message": f"License 已过期，剩余宽限期 {grace_days_left} 天"
            }
        else:
            return _free_status(f"License 已过期（{expiry_str}）")

    # 有效
    days_left = (expiry - now).days
    features = license_data.get("features", [])

    # 判断 tier
    if "enterprise" in features or "all" in features:
        tier = "企业版"
        plan = "enterprise"
    elif "pro" in features or "premium" in features:
        tier = "专业版"
        plan = "pro"
    else:
        tier = "标准版"
        plan = "standard"

    return {
        "licensed": True,
        "plan": plan,
        "tier": tier,
        "expiry": expiry_str,
        "days_left": days_left,
        "features": features,
        "status": "active",
        "message": f"License 有效，剩余 {days_left} 天"
    }


def _free_status(reason=None):
    """返回免费版状态"""
    status = {
        "licensed": False,
        "plan": "free",
        "tier": "免费版",
        "expiry": None,
        "days_left": 0,
        "features": ["basic_tools"],
        "status": "free",
        "message": reason or "未激活 License，使用免费版"
    }
    return status


def check_feature_access(feature_name):
    """
    检查当前 License 是否有权限访问某个功能
    返回: bool
    """
    status = get_license_status()
    if not status.get("licensed"):
        # 免费版：只允许 basic_tools
        return feature_name == "basic_tools"

    features = status.get("features", [])
    if "all" in features or "enterprise" in features:
        return True
    return feature_name in features


def get_daily_limit():
    """
    根据当前授权返回每日限额
    返回: int (-1 = 无限)
    """
    status = get_license_status()
    plan = status.get("plan", "free")

    limits = {
        "free": 5,
        "grace": 50,
        "standard": 50,
        "pro": 50,
        "enterprise": -1
    }

    return limits.get(plan, 5)
