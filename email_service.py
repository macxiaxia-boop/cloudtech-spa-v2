"""
Email Service — SMTP with HTML templates
Supports: verification, password reset, billing, welcome
"""
import os, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "noreply@cloudtech.com")


def _send(to_email: str, subject: str, html_body: str) -> bool:
    """Send HTML email via SMTP"""
    if not SMTP_HOST:
        print(f"[EMAIL MOCK] To: {to_email} | {subject}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = SMTP_FROM
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


def send_verification(to_email: str, name: str, code: str) -> bool:
    subject = "验证您的云数科技账号"
    body = f"""<div style="max-width:480px;margin:0 auto;font-family:Arial,sans-serif">
<h2 style="color:#6c5ce7">云数科技 · 邮箱验证</h2>
<p>{name}，您好！</p>
<p>感谢注册云数科技。您的验证码是：</p>
<h1 style="color:#6c5ce7;font-size:2rem;letter-spacing:4px">{code}</h1>
<p>验证码30分钟内有效。</p>
<hr style="border-color:#1e1e2a">
<p style="color:#777;font-size:0.8rem">此邮件由系统自动发送，请勿回复。</p>
</div>"""
    return _send(to_email, subject, body)


def send_welcome(to_email: str, name: str, plan: str) -> bool:
    subject = "欢迎加入云数科技！"
    body = f"""<div style="max-width:480px;margin:0 auto;font-family:Arial,sans-serif">
<h2 style="color:#6c5ce7">欢迎加入云数科技！</h2>
<p>{name}，您好！</p>
<p>您的 <b>{plan}</b> 套餐已激活，7天免费试用开始。</p>
<p>立即开始：<a href="http://localhost:5099/admin" style="color:#6c5ce7">进入管理后台</a></p>
<hr style="border-color:#1e1e2a">
<p style="color:#777;font-size:0.8rem">如需帮助，回复此邮件或联系客服。</p>
</div>"""
    return _send(to_email, subject, body)


def send_password_reset(to_email: str, name: str, reset_link: str) -> bool:
    subject = "重置您的云数科技密码"
    body = f"""<div style="max-width:480px;margin:0 auto;font-family:Arial,sans-serif">
<h2 style="color:#6c5ce7">密码重置</h2>
<p>{name}，您好！</p>
<p>点击下方链接重置密码（30分钟内有效）：</p>
<p><a href="{reset_link}" style="color:#6c5ce7;font-size:1.1rem">重置密码</a></p>
<p style="color:#777;font-size:0.8rem">如果不是您本人操作，请忽略此邮件。</p>
</div>"""
    return _send(to_email, subject, body)


def send_billing(to_email: str, name: str, plan: str, amount: float,
                 next_billing: str, invoice_url: str = "") -> bool:
    subject = f"云数科技 · 账单确认 ({plan})"
    body = f"""<div style="max-width:480px;margin:0 auto;font-family:Arial,sans-serif">
<h2 style="color:#6c5ce7">账单确认</h2>
<p>{name}，您好！</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
<tr><td style="padding:8px;border-bottom:1px solid #1e1e2a">套餐</td><td style="padding:8px;border-bottom:1px solid #1e1e2a"><b>{plan}</b></td></tr>
<tr><td style="padding:8px;border-bottom:1px solid #1e1e2a">金额</td><td style="padding:8px;border-bottom:1px solid #1e1e2a"><b>¥{amount:.2f}</b></td></tr>
<tr><td style="padding:8px;border-bottom:1px solid #1e1e2a">下次扣款</td><td style="padding:8px;border-bottom:1px solid #1e1e2a">{next_billing}</td></tr>
</table>
{"<p><a href=\"" + invoice_url + "\" style=\"color:#6c5ce7\">查看发票</a></p>" if invoice_url else ""}
</div>"""
    return _send(to_email, subject, body)
