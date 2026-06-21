"""
User authentication system: email/password registration, email verification,
login via password or verification code.

Uses Vercel API route for email sending (Render blocks SMTP).
Falls back to direct SMTP if Vercel endpoint unavailable.
Token-based sessions stored in SQLite.
"""
from __future__ import annotations
import os, time, random, string, hashlib, secrets, sqlite3, smtplib, json
import urllib.request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from contextlib import contextmanager
from loguru import logger
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.163.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "15571870062@163.com")
SMTP_PASS = os.getenv("SMTP_PASS", "WSdQhddWrar9TGny")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)

# Vercel email API endpoint (used when direct SMTP is blocked, e.g. on Render)
VERCEL_EMAIL_URL = os.getenv("VERCEL_EMAIL_URL", "https://market-survey-nu.vercel.app/api/send-email")
EMAIL_API_SECRET = os.getenv("EMAIL_API_SECRET", "selectpilot_email_2024")

DB_PATH = Path(__file__).parent.parent / "data" / "users.sqlite"

# Subscription plan limits
PLAN_LIMITS = {
    "free":       {"reports_per_month": 5,   "categories": 1,   "price_cny": 0},
    "pro":        {"reports_per_month": 100, "categories": 10,  "price_cny": 99},
    "enterprise": {"reports_per_month": -1,  "categories": -1,  "price_cny": 299},
}


def _init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL DEFAULT '',
        password_hash TEXT NOT NULL DEFAULT '',
        email_verified INTEGER NOT NULL DEFAULT 0,
        plan TEXT NOT NULL DEFAULT 'free',
        plan_expires_at REAL DEFAULT NULL,
        created_at REAL NOT NULL DEFAULT (strftime('%s','now')),
        updated_at REAL NOT NULL DEFAULT (strftime('%s','now')),
        reports_used_this_month INTEGER NOT NULL DEFAULT 0,
        reports_month TEXT NOT NULL DEFAULT ''
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS verification_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        code TEXT NOT NULL,
        purpose TEXT NOT NULL DEFAULT 'verify',
        created_at REAL NOT NULL DEFAULT (strftime('%s','now')),
        used INTEGER NOT NULL DEFAULT 0
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at REAL NOT NULL DEFAULT (strftime('%s','now')),
        expires_at REAL NOT NULL
    )""")
    conn.commit()
    conn.close()


_init_db()


@contextmanager
def _db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"{salt}:{h.hex()}"


def _check_password(password: str, stored: str) -> bool:
    if not stored or ":" not in stored:
        return False
    salt, h = stored.split(":", 1)
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return check.hex() == h


def _generate_code() -> str:
    return "".join(random.choices(string.digits, k=6))


def _generate_token() -> str:
    return secrets.token_urlsafe(32)


def _send_email_via_vercel(to: str, subject: str, html_body: str) -> bool:
    """Send email via Vercel API route (bypasses Render's SMTP block)."""
    try:
        payload = json.dumps({
            "to": to,
            "subject": subject,
            "html": html_body,
            "secret": EMAIL_API_SECRET,
        }).encode("utf-8")
        req = urllib.request.Request(
            VERCEL_EMAIL_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                logger.info(f"Email sent via Vercel API to {to}: {subject}")
                return True
            logger.error(f"Vercel email API error: {result}")
            return False
    except Exception as e:
        logger.error(f"Vercel email API failed for {to}: {type(e).__name__}: {e}")
        return False


def _send_email_via_smtp(to: str, subject: str, html_body: str) -> bool:
    """Direct SMTP sending (works when not blocked by network)."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"SelectPilot <{SMTP_FROM}>"
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    attempts = [
        ("SSL", SMTP_HOST, 465),
        ("STARTTLS", SMTP_HOST, 587),
    ]
    for method, host, port in attempts:
        try:
            if method == "SSL":
                server = smtplib.SMTP_SSL(host, port, timeout=15)
            else:
                server = smtplib.SMTP(host, port, timeout=15)
                server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, [to], msg.as_string())
            server.quit()
            logger.info(f"Email sent via SMTP {method}:{port} to {to}: {subject}")
            return True
        except Exception as e:
            logger.warning(f"SMTP {method}:{port} failed for {to}: {type(e).__name__}: {e}")
            continue
    return False


def _send_email(to: str, subject: str, html_body: str) -> bool:
    """Send email: try Vercel API first, fall back to direct SMTP."""
    if _send_email_via_vercel(to, subject, html_body):
        return True
    logger.warning("Vercel API failed, trying direct SMTP...")
    return _send_email_via_smtp(to, subject, html_body)


def _verification_email_html(code: str, purpose: str) -> str:
    action = "注册" if purpose == "verify" else "登录"
    return f"""
    <div style="font-family: -apple-system, 'PingFang SC', 'Helvetica Neue', sans-serif; max-width: 420px; margin: 0 auto; padding: 48px 24px; background: #ffffff;">
      <div style="text-align: center; margin-bottom: 36px;">
        <div style="display: inline-block; width: 40px; height: 40px; background: #333333; border-radius: 8px; line-height: 40px; color: white; font-size: 18px;">S</div>
        <h2 style="margin: 10px 0 0; color: #333333; font-size: 17px; font-weight: 600; letter-spacing: -0.2px;">SelectPilot</h2>
      </div>
      <div style="background: #f9f9f9; border: 1px solid #ebebeb; border-radius: 8px; padding: 28px 24px; text-align: center;">
        <p style="color: #666666; font-size: 14px; line-height: 1.5; margin: 0 0 20px;">你正在{action} SelectPilot 账号</p>
        <div style="background: #ffffff; border: 1px solid #d6d6d6; border-radius: 6px; padding: 16px 24px; margin: 0 auto; display: inline-block;">
          <span style="font-family: 'SF Mono', 'JetBrains Mono', monospace; font-size: 28px; font-weight: 700; letter-spacing: 6px; color: #333333;">{code}</span>
        </div>
        <p style="color: #999999; font-size: 12px; margin: 20px 0 0;">验证码 10 分钟内有效</p>
      </div>
      <p style="color: #cccccc; font-size: 11px; text-align: center; margin-top: 20px;">如非本人操作，请忽略此邮件。</p>
    </div>
    """


def register(email: str, name: str, password: str) -> dict:
    with _db() as conn:
        existing = conn.execute("SELECT id, email_verified FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            if existing["email_verified"]:
                return {"ok": False, "detail": "该邮箱已注册"}
            conn.execute("UPDATE users SET name=?, password_hash=?, updated_at=? WHERE id=?",
                         (name, _hash_password(password), time.time(), existing["id"]))
        else:
            conn.execute("INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)",
                         (email, name, _hash_password(password)))

    code = _generate_code()
    with _db() as conn:
        conn.execute("INSERT INTO verification_codes (email, code, purpose) VALUES (?, ?, 'verify')",
                     (email, code))

    sent = _send_email(email, f"【SelectPilot】验证码：{code}", _verification_email_html(code, "verify"))
    if not sent:
        return {"ok": False, "detail": "邮件发送失败，请稍后重试"}
    return {"ok": True, "message": "验证码已发送到邮箱"}


def send_code(email: str, purpose: str = "login") -> dict:
    if purpose == "login":
        with _db() as conn:
            user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if not user:
                return {"ok": False, "detail": "该邮箱未注册"}

    code = _generate_code()
    with _db() as conn:
        conn.execute("INSERT INTO verification_codes (email, code, purpose) VALUES (?, ?, ?)",
                     (email, code, purpose))

    sent = _send_email(email, f"【SelectPilot】验证码：{code}", _verification_email_html(code, purpose))
    if not sent:
        return {"ok": False, "detail": "邮件发送失败，请稍后重试"}
    return {"ok": True, "message": "验证码已发送"}


def verify_email(email: str, code: str) -> dict:
    with _db() as conn:
        row = conn.execute(
            "SELECT id, code FROM verification_codes WHERE email = ? AND purpose = 'verify' AND used = 0 "
            "AND created_at > ? ORDER BY created_at DESC LIMIT 1",
            (email, time.time() - 600)
        ).fetchone()
        if not row or row["code"] != code:
            return {"ok": False, "detail": "验证码无效或已过期"}

        conn.execute("UPDATE verification_codes SET used = 1 WHERE id = ?", (row["id"],))
        conn.execute("UPDATE users SET email_verified = 1, updated_at = ? WHERE email = ?",
                     (time.time(), email))

        user = conn.execute("SELECT id, email, name, plan FROM users WHERE email = ?", (email,)).fetchone()
        token = _generate_token()
        conn.execute("INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
                     (token, user["id"], time.time() + 30 * 86400))

    return {"ok": True, "token": token, "email": user["email"], "name": user["name"], "plan": user["plan"]}


def login_password(email: str, password: str) -> dict:
    with _db() as conn:
        user = conn.execute("SELECT id, email, name, password_hash, email_verified, plan FROM users WHERE email = ?",
                            (email,)).fetchone()
        if not user:
            return {"ok": False, "detail": "邮箱或密码错误"}
        if not _check_password(password, user["password_hash"]):
            return {"ok": False, "detail": "邮箱或密码错误"}
        if not user["email_verified"]:
            # Auto-send verification code and tell user to verify
            send_code(email, "verify")
            return {"ok": False, "detail": "请先验证邮箱，验证码已重新发送"}

        token = _generate_token()
        conn.execute("INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
                     (token, user["id"], time.time() + 30 * 86400))

    return {"ok": True, "token": token, "email": user["email"], "name": user["name"], "plan": user["plan"]}


def login_code(email: str, code: str) -> dict:
    with _db() as conn:
        row = conn.execute(
            "SELECT id, code FROM verification_codes WHERE email = ? AND purpose = 'login' AND used = 0 "
            "AND created_at > ? ORDER BY created_at DESC LIMIT 1",
            (email, time.time() - 600)
        ).fetchone()
        if not row or row["code"] != code:
            return {"ok": False, "detail": "验证码无效或已过期"}

        conn.execute("UPDATE verification_codes SET used = 1 WHERE id = ?", (row["id"],))
        user = conn.execute("SELECT id, email, name, plan, email_verified FROM users WHERE email = ?",
                            (email,)).fetchone()
        if not user:
            return {"ok": False, "detail": "该邮箱未注册"}
        # Auto-verify email if user successfully uses a login code
        if not user["email_verified"]:
            conn.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (user["id"],))

        token = _generate_token()
        conn.execute("INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
                     (token, user["id"], time.time() + 30 * 86400))

    return {"ok": True, "token": token, "email": user["email"], "name": user["name"], "plan": user["plan"]}


def get_user_by_token(token: str) -> dict | None:
    with _db() as conn:
        row = conn.execute(
            "SELECT s.user_id, s.expires_at, u.email, u.name, u.plan, u.reports_used_this_month, u.reports_month "
            "FROM sessions s JOIN users u ON s.user_id = u.id WHERE s.token = ?",
            (token,)
        ).fetchone()
        if not row or row["expires_at"] < time.time():
            return None
        return dict(row)


def get_plan_limits(plan: str) -> dict:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])


def check_usage(token: str) -> dict:
    user = get_user_by_token(token)
    if not user:
        return {"ok": False, "detail": "未登录"}
    limits = get_plan_limits(user["plan"])
    current_month = time.strftime("%Y-%m")
    used = user["reports_used_this_month"] if user["reports_month"] == current_month else 0
    max_reports = limits["reports_per_month"]
    can_use = max_reports < 0 or used < max_reports
    return {
        "ok": True,
        "plan": user["plan"],
        "reports_used": used,
        "reports_limit": max_reports,
        "can_use": can_use,
    }


def increment_usage(token: str):
    user = get_user_by_token(token)
    if not user:
        return
    current_month = time.strftime("%Y-%m")
    with _db() as conn:
        if user["reports_month"] != current_month:
            conn.execute("UPDATE users SET reports_used_this_month = 1, reports_month = ? WHERE id = ?",
                         (current_month, user["user_id"]))
        else:
            conn.execute("UPDATE users SET reports_used_this_month = reports_used_this_month + 1 WHERE id = ?",
                         (user["user_id"],))
