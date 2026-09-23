"""邮件发送模块。

- 配置了 SMTP 时用 smtplib 真实发送（生产）。
- 未配置 SMTP 时进入「调试模式」：验证码写入 backend/data/mail_outbox/*.txt，
  并在 /send-code 响应的 data.code 中回显（仅调试模式），便于课程设计演示。
"""
from __future__ import annotations

import os
import smtplib
import ssl
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

from core.config import ROOT_DIR

SMTP_HOST = os.environ.get("KESE_SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("KESE_SMTP_PORT", "465"))
SMTP_USER = os.environ.get("KESE_SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("KESE_SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("KESE_SMTP_FROM", SMTP_USER) or "no-reply@example.com"
SMTP_TLS = os.environ.get("KESE_SMTP_TLS", "1") not in ("0", "false", "False")

_OUTBOX = ROOT_DIR / "data" / "mail_outbox"


def smtp_enabled() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def debug_mode() -> bool:
    return not smtp_enabled()


def send_code_email(to_email: str, code: str, purpose_label: str) -> None:
    """发送验证码邮件。真实发送失败时回落到调试模式落盘。"""
    subject = f"【智能导购系统】{purpose_label}验证码"
    body = (
        f"您好：\n\n"
        f"您正在进行「{purpose_label}」，验证码为：{code}\n"
        f"验证码 10 分钟内有效，请勿泄露给他人。\n\n"
        f"若非本人操作，请忽略本邮件。\n"
    )

    if smtp_enabled():
        try:
            _send_smtp(to_email, subject, body)
            return
        except Exception:
            # 发送失败回落到调试模式，不影响演示
            _write_outbox(to_email, subject, body, code)
            return

    _write_outbox(to_email, subject, body, code)


def _send_smtp(to_email: str, subject: str, body: str) -> None:
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr(("智能导购系统", SMTP_FROM))
    msg["To"] = to_email

    port = SMTP_PORT
    if port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, port, context=context, timeout=15) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [to_email], msg.as_string())
    else:
        with smtplib.SMTP(SMTP_HOST, port, timeout=15) as server:
            if SMTP_TLS:
                server.starttls(context=ssl.create_default_context())
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [to_email], msg.as_string())


def _write_outbox(to_email: str, subject: str, body: str, code: str) -> None:
    _OUTBOX.mkdir(parents=True, exist_ok=True)
    import time
    filename = f"{int(time.time())}_{to_email.replace('@', '_at_')}.txt"
    (_OUTBOX / filename).write_text(
        f"To: {to_email}\nSubject: {subject}\n\n{body}\n\n[调试模式] 验证码：{code}\n",
        encoding="utf-8",
    )
