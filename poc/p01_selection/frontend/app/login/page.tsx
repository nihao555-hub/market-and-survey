"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Compass, Mail, Lock, ArrowRight, Loader2 } from "lucide-react";
import { BACKEND_BASE } from "@/lib/graphql-client";

type LoginMode = "password" | "code";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<LoginMode>("password");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);
  const [error, setError] = useState("");
  const [countdown, setCountdown] = useState(0);

  const startCountdown = () => {
    setCountdown(60);
    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) { clearInterval(timer); return 0; }
        return prev - 1;
      });
    }, 1000);
  };

  const sendCode = async () => {
    if (!email) { setError("请输入邮箱"); return; }
    setSendingCode(true);
    setError("");
    try {
      const res = await fetch(`${BACKEND_BASE}/auth/send-code`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, purpose: "login" }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "发送失败");
      setCodeSent(true);
      startCountdown();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "发送验证码失败");
    } finally {
      setSendingCode(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const endpoint = mode === "password" ? "/auth/login" : "/auth/login-code";
      const body = mode === "password"
        ? { email, password }
        : { email, code };
      const res = await fetch(`${BACKEND_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "登录失败");
      localStorage.setItem("auth_token", data.token);
      localStorage.setItem("user_email", data.email);
      localStorage.setItem("user_plan", data.plan || "free");
      router.push("/");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "登录失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-orange-50/30 to-slate-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <Link href="/" className="flex items-center justify-center gap-2.5 mb-10">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center shadow-lg shadow-orange-500/25">
            <Compass className="w-6 h-6 text-white" />
          </div>
          <span className="text-xl font-bold text-slate-900">蓝海罗盘</span>
        </Link>

        {/* Card */}
        <div className="bg-white rounded-2xl border border-slate-200/60 shadow-xl shadow-slate-200/40 p-8">
          <h1 className="text-2xl font-bold text-slate-900 text-center mb-2">欢迎回来</h1>
          <p className="text-sm text-slate-500 text-center mb-8">登录你的蓝海罗盘账号</p>

          {/* Mode toggle */}
          <div className="flex bg-slate-100 rounded-xl p-1 mb-6">
            <button
              onClick={() => { setMode("password"); setError(""); }}
              className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all ${mode === "password" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500"}`}
            >
              密码登录
            </button>
            <button
              onClick={() => { setMode("code"); setError(""); }}
              className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all ${mode === "code" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500"}`}
            >
              验证码登录
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium text-slate-700 mb-1.5 block">邮箱</label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  required
                  className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 focus:border-orange-400 focus:ring-2 focus:ring-orange-400/20 outline-none text-sm transition-all"
                />
              </div>
            </div>

            {mode === "password" ? (
              <div>
                <label className="text-sm font-medium text-slate-700 mb-1.5 block">密码</label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="输入密码"
                    required
                    className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 focus:border-orange-400 focus:ring-2 focus:ring-orange-400/20 outline-none text-sm transition-all"
                  />
                </div>
              </div>
            ) : (
              <div>
                <label className="text-sm font-medium text-slate-700 mb-1.5 block">验证码</label>
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={code}
                    onChange={e => setCode(e.target.value)}
                    placeholder="6 位验证码"
                    maxLength={6}
                    required
                    className="flex-1 px-4 py-3 rounded-xl border border-slate-200 focus:border-orange-400 focus:ring-2 focus:ring-orange-400/20 outline-none text-sm transition-all"
                  />
                  <button
                    type="button"
                    onClick={sendCode}
                    disabled={sendingCode || countdown > 0}
                    className="px-4 py-3 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-slate-700 text-sm font-medium rounded-xl transition-colors whitespace-nowrap"
                  >
                    {sendingCode ? <Loader2 className="w-4 h-4 animate-spin" /> : countdown > 0 ? `${countdown}s` : "发送验证码"}
                  </button>
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3.5 bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white font-semibold rounded-xl shadow-lg shadow-orange-500/25 transition-all disabled:opacity-70"
            >
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <>登录 <ArrowRight className="w-4 h-4" /></>}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500">
            还没有账号？
            <Link href="/register" className="text-orange-600 font-medium hover:text-orange-700 ml-1">
              免费注册
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
