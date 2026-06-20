import { NextRequest, NextResponse } from "next/server";
import * as nodemailer from "nodemailer";

const SMTP_HOST = process.env.SMTP_HOST || "smtp.163.com";
const SMTP_PORT = parseInt(process.env.SMTP_PORT || "465");
const SMTP_USER = process.env.SMTP_USER || "15571870062@163.com";
const SMTP_PASS = process.env.SMTP_PASS || "WSdQhddWrar9TGny";
const EMAIL_API_SECRET = process.env.EMAIL_API_SECRET || "selectpilot_email_2024";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { to, subject, html, secret } = body;

    if (secret !== EMAIL_API_SECRET) {
      return NextResponse.json({ ok: false, detail: "Unauthorized" }, { status: 401 });
    }
    if (!to || !subject || !html) {
      return NextResponse.json({ ok: false, detail: "Missing required fields" }, { status: 400 });
    }

    const transporter = nodemailer.createTransport({
      host: SMTP_HOST,
      port: SMTP_PORT,
      secure: SMTP_PORT === 465,
      auth: { user: SMTP_USER, pass: SMTP_PASS },
      tls: { rejectUnauthorized: false },
    });

    await transporter.sendMail({
      from: `SelectPilot <${SMTP_USER}>`,
      to,
      subject,
      html,
    });

    return NextResponse.json({ ok: true, message: "Email sent" });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    console.error("Email send error:", msg);
    return NextResponse.json({ ok: false, detail: msg }, { status: 500 });
  }
}
