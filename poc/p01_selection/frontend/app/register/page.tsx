"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Compass, Mail, Lock, User, ArrowRight, Loader2, Check } from "lucide-react";
import { BACKEND_BASE } from "@/lib/graphql-client";

export default function RegisterPage() {
  const router = useRouter();
  const [step, setStep] = useState<"form" | "verify">("form");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
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

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 6) { setError("密码至少 6 位"); return; }
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${BACKEND_BASE}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "注册失败");
      setStep("verify");
      startCountdown();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "注册失败");
    } finally {
      setLoading(false);
    }
  };

  const resendCode = async () => {
    try {
      await fetch(`${BACKEND_BASE}/auth/send-code`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, purpose: "verify" }),
      });
      startCountdown();
    } catch {}
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${BACKEND_BASE}/auth/verify-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, code }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "验证失败");
      localStorage.setItem("auth_token", data.token);
      localStorage.setItem("user_email", data.email);
      localStorage.setItem("user_plan", data.plan || "free");
      router.push("/");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "验证失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-orange-50/30 to-slate-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <Link href="/" className="flex items-center justify-center gap-2.5 mb-10">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center shadow-lg shadow-orange-500/25">
            <Compass className="w-6 h-6 text-white" />
          </div>
          <span className="text-xl font-bold text-slate-900">蓝海罗盘</span>
        </Link>

        <div className="bg-white rounded-2xl border border-slate-200/60 shadow-xl shadow-slate-200/40 p-8">
          {step === "form" ? (
            <>
              <h1 className="text-2xl font-bold text-slate-900 text-center mb-2">创建账号</h1>
              <p className="text-sm text-slate-500 text-center mb-8">免费开始使用蓝海罗盘</p>

              {error && (
                <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
                  {error}
                </div>
              )}

              <form onSubmit={handleRegister} className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-slate-700 mb-1.5 block">昵称</label>
                  <div className="relative">
                    <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                      type="text"
                      value={name}
                      onChange={e => setName(e.target.value)}
                      placeholder="你的昵称"
                      required
                      className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 focus:border-orange-400 focus:ring-2 focus:ring-orange-400/20 outline-none text-sm transition-all"
                    />
                  </div>
                </div>
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
                <div>
                  <label className="text-sm font-medium text-slate-700 mb-1.5 block">密码</label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                      type="password"
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      placeholder="至少 6 位密码"
                      required
                      minLength={6}
                      className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 focus:border-orange-400 focus:ring-2 focus:ring-orange-400/20 outline-none text-sm transition-all"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 py-3.5 bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white font-semibold rounded-xl shadow-lg shadow-orange-500/25 transition-all disabled:opacity-70"
                >
                  {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <>注册 <ArrowRight className="w-4 h-4" /></>}
                </button>
              </form>

              <p className="mt-6 text-center text-sm text-slate-500">
                已有账号？
                <Link href="/login" className="text-orange-600 font-medium hover:text-orange-700 ml-1">
                  去登录
                </Link>
              </p>
            </>
          ) : (
            <>
              <div className="flex items-center justify-center mb-6">
                <div className="w-16 h-16 rounded-full bg-orange-100 flex items-center justify-center">
                  <Mail className="w-8 h-8 text-orange-500" />
                </div>
              </div>
              <h1 className="text-2xl font-bold text-slate-900 text-center mb-2">验证邮箱</h1>
              <p className="text-sm text-slate-500 text-center mb-8">
                验证码已发送到 <span className="font-medium text-slate-700">{email}</span>
              </p>

              {error && (
                <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
                  {error}
                </div>
              )}

              <form onSubmit={handleVerify} className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-slate-700 mb-1.5 block">验证码</label>
                  <input
                    type="text"
                    value={code}
                    onChange={e => setCode(e.target.value)}
                    placeholder="输入 6 位验证码"
                    maxLength={6}
                    required
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-orange-400 focus:ring-2 focus:ring-orange-400/20 outline-none text-sm text-center tracking-[0.5em] text-lg font-mono transition-all"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 py-3.5 bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white font-semibold rounded-xl shadow-lg shadow-orange-500/25 transition-all disabled:opacity-70"
                >
                  {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <><Check className="w-4 h-4" /> 验证并登录</>}
                </button>

                <button
                  type="button"
                  onClick={resendCode}
                  disabled={countdown > 0}
                  className="w-full py-2.5 text-sm text-slate-500 hover:text-slate-700 disabled:opacity-50 transition-colors"
                >
                  {countdown > 0 ? `${countdown} 秒后重新发送` : "重新发送验证码"}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
