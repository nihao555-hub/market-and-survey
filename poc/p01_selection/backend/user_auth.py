"""
User authentication system: email/password registration, email verification,
login via password or verification code.

Uses 163 SMTP for sending verification emails.
Token-based sessions stored in SQLite.
"""
from __future__ import annotations
import os, time, random, string, hashlib, secrets, sqlite3, smtplib, json
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


def _send_email(to: str, subject: str, html_body: str) -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"SelectPilot <{SMTP_FROM}>"
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
            server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_FROM, [to], msg.as_string())
        server.quit()
        logger.info(f"Email sent to {to}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Email send failed to {to}: {e}")
        return False


def _verification_email_html(code: str, purpose: str) -> str:
    action = "注册" if purpose == "verify" else "登录"
    return f"""
    <div style="font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px;">
      <div style="text-align: center; margin-bottom: 32px;">
        <div style="display: inline-block; width: 48px; height: 48px; background: linear-gradient(135deg, #F97316, #F59E0B); border-radius: 12px; line-height: 48px; color: white; font-size: 24px;">&#x1F9ED;</div>
        <h2 style="margin: 12px 0 0; color: #0F172A; font-size: 20px;">SelectPilot</h2>
      </div>
      <div style="background: #fff; border: 1px solid #E2E8F0; border-radius: 16px; padding: 32px; text-align: center;">
        <p style="color: #64748B; font-size: 14px; margin: 0 0 24px;">你正在{action} SelectPilot 账号，请使用以下验证码：</p>
        <div style="background: #FFF7ED; border: 2px solid #FDBA74; border-radius: 12px; padding: 20px; margin: 0 auto; display: inline-block;">
          <span style="font-family: 'JetBrains Mono', monospace; font-size: 32px; font-weight: 700; letter-spacing: 8px; color: #EA580C;">{code}</span>
        </div>
        <p style="color: #94A3B8; font-size: 12px; margin: 24px 0 0;">验证码 10 分钟内有效，请勿泄露给他人。</p>
      </div>
      <p style="color: #CBD5E1; font-size: 11px; text-align: center; margin-top: 24px;">如果这不是你的操作，请忽略此邮件。</p>
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

    _send_email(email, f"【SelectPilot】验证码：{code}", _verification_email_html(code, "verify"))
    return {"ok": True, "message": "验证码已发送到邮箱"}


def send_code(email: str, purpose: str = "login") -> dict:
    if purpose == "login":
        with _db() as conn:
            user = conn.execute("SELECT id FROM users WHERE email = ? AND email_verified = 1", (email,)).fetchone()
            if not user:
                return {"ok": False, "detail": "该邮箱未注册或未验证"}

    code = _generate_code()
    with _db() as conn:
        conn.execute("INSERT INTO verification_codes (email, code, purpose) VALUES (?, ?, ?)",
                     (email, code, purpose))

    _send_email(email, f"【SelectPilot】验证码：{code}", _verification_email_html(code, purpose))
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
        if not user["email_verified"]:
            return {"ok": False, "detail": "请先验证邮箱"}
        if not _check_password(password, user["password_hash"]):
            return {"ok": False, "detail": "邮箱或密码错误"}

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
        user = conn.execute("SELECT id, email, name, plan FROM users WHERE email = ? AND email_verified = 1",
                            (email,)).fetchone()
        if not user:
            return {"ok": False, "detail": "该邮箱未注册"}

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
