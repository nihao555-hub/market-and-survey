"use client";
import React, { useState } from "react";
import { Eye, EyeOff, Mail, Lock, ArrowRight, Loader2, KeyRound, User } from "lucide-react";

export interface Testimonial {
  avatarSrc: string;
  name: string;
  handle: string;
  text: string;
}

interface SignInPageProps {
  mode: "login" | "register";
  heroImageSrc?: string;
  testimonials?: Testimonial[];
  onSubmit?: (data: Record<string, string>) => Promise<void>;
  onSendCode?: (email: string) => Promise<void>;
  onVerify?: (email: string, code: string) => Promise<void>;
  onSwitchMode?: () => void;
  onResetPassword?: () => void;
  error?: string;
}

const GlassInputWrapper = ({ children }: { children: React.ReactNode }) => (
  <div className="rounded-lg border border-neutral-200 bg-neutral-50 transition-colors focus-within:border-neutral-400 focus-within:bg-white">
    {children}
  </div>
);

const TestimonialCard = ({ testimonial, delay }: { testimonial: Testimonial; delay: string }) => (
  <div className={`animate-testimonial ${delay} flex items-start gap-3 rounded-xl bg-white/90 backdrop-blur-sm border border-neutral-200 p-4 w-64 shadow-sm`}>
    <img src={testimonial.avatarSrc} className="h-9 w-9 object-cover rounded-full" alt="avatar" />
    <div className="text-sm leading-snug">
      <p className="flex items-center gap-1 font-medium text-neutral-900">{testimonial.name}</p>
      <p className="text-neutral-400 text-[12px]">{testimonial.handle}</p>
      <p className="mt-1 text-neutral-600 text-[13px]">{testimonial.text}</p>
    </div>
  </div>
);

export const SignInPage: React.FC<SignInPageProps> = ({
  mode,
  heroImageSrc,
  testimonials = [],
  onSubmit,
  onSendCode,
  onVerify,
  onSwitchMode,
  onResetPassword,
  error,
}) => {
  const [showPassword, setShowPassword] = useState(false);
  const [loginTab, setLoginTab] = useState<"password" | "code">("password");
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<"form" | "verify">("form");
  const [email, setEmail] = useState("");
  const [countdown, setCountdown] = useState(0);
  const [localError, setLocalError] = useState("");

  const startCountdown = () => {
    setCountdown(60);
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) { clearInterval(timer); return 0; }
        return prev - 1;
      });
    }, 1000);
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data = Object.fromEntries(formData.entries()) as Record<string, string>;
    setEmail(data.email || "");
    setLocalError("");
    setLoading(true);
    try {
      if (mode === "register") {
        await onSubmit?.(data);
        setStep("verify");
        startCountdown();
      } else if (loginTab === "code") {
        await onSendCode?.(data.email || "");
        setEmail(data.email || "");
        setStep("verify");
        startCountdown();
      } else {
        await onSubmit?.(data);
      }
    } catch (err: unknown) {
      setLocalError(err instanceof Error ? err.message : "操作失败");
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const code = formData.get("code") as string;
    setLocalError("");
    setLoading(true);
    try {
      await onVerify?.(email, code);
    } catch (err: unknown) {
      setLocalError(err instanceof Error ? err.message : "验证失败");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    try {
      await onSendCode?.(email);
      startCountdown();
    } catch {}
  };

  const displayError = error || localError;
  const isLogin = mode === "login";

  return (
    <div className="h-[100dvh] flex flex-col md:flex-row font-geist w-[100dvw]">
      {/* Left column: form */}
      <section className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <div className="flex flex-col gap-6">
            {/* Logo */}
            <div className="animate-element animate-delay-100 flex items-center gap-3 mb-2">
              <img src="/images/logo-icon.png" alt="SelectPilot" className="h-9 w-9 rounded-xl" />
              <span className="text-xl font-semibold tracking-tight">SelectPilot</span>
            </div>

            {step === "verify" ? (
              /* ── Verification step ── */
              <>
                <div className="animate-element animate-delay-100 flex flex-col items-center gap-3">
                  <div className="w-14 h-14 rounded-xl bg-neutral-100 flex items-center justify-center">
                    <Mail className="w-7 h-7 text-neutral-600" />
                  </div>
                  <h1 className="text-2xl font-semibold">验证邮箱</h1>
                  <p className="text-muted-foreground text-sm text-center">
                    验证码已发送到 <span className="text-foreground font-medium">{email}</span>
                  </p>
                </div>

                {displayError && (
                  <div className="animate-element animate-delay-200 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
                    {displayError}
                  </div>
                )}

                <form className="space-y-5" onSubmit={handleVerify}>
                  <div className="animate-element animate-delay-300">
                    <label className="text-sm font-medium text-muted-foreground">验证码</label>
                    <GlassInputWrapper>
                      <input name="code" type="text" placeholder="输入 6 位验证码" maxLength={6}
                        className="w-full bg-transparent text-sm p-4 rounded-2xl focus:outline-none tracking-[0.3em] text-center font-mono text-lg" />
                    </GlassInputWrapper>
                  </div>

                  <button type="submit" disabled={loading}
                    className="animate-element animate-delay-400 w-full rounded-lg bg-neutral-900 py-3.5 text-[14px] font-medium text-white hover:bg-neutral-800 transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <><KeyRound className="w-4 h-4" /> 验证并登录</>}
                  </button>
                </form>

                <p className="animate-element animate-delay-500 text-center text-sm text-muted-foreground">
  {countdown > 0 ? `${countdown}秒后可重发` : (
                    <button onClick={handleResend} className="text-neutral-900 hover:underline">重新发送验证码</button>
                  )}
                </p>
              </>
            ) : (
              /* ── Main form ── */
              <>
                <h1 className="animate-element animate-delay-100 text-[28px] md:text-[32px] font-semibold leading-tight tracking-tight">
                  {isLogin ? (
                    <span className="text-neutral-900">欢迎回来</span>
                  ) : (
                    <span className="text-neutral-900">创建你的账户</span>
                  )}
                </h1>
                <p className="animate-element animate-delay-200 text-neutral-500 text-[14px]">
                  {isLogin ? "登录以继续你的选品调研" : "免费开始。AI 驱动的智能选品。"}
                </p>

                {/* Login tab switcher */}
                {isLogin && (
                  <div className="animate-element animate-delay-200 flex rounded-lg border border-neutral-200 p-0.5 bg-neutral-50">
                    <button type="button" onClick={() => setLoginTab("password")}
                      className={`flex-1 rounded-md py-2 text-[13px] font-medium transition-all ${loginTab === "password" ? "bg-white shadow-sm text-neutral-900" : "text-neutral-500 hover:text-neutral-900"}`}>
                      密码登录
                    </button>
                    <button type="button" onClick={() => setLoginTab("code")}
                      className={`flex-1 rounded-md py-2 text-[13px] font-medium transition-all ${loginTab === "code" ? "bg-white shadow-sm text-neutral-900" : "text-neutral-500 hover:text-neutral-900"}`}>
                      邮箱验证码
                    </button>
                  </div>
                )}

                {displayError && (
                  <div className="animate-element animate-delay-200 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
                    {displayError}
                  </div>
                )}

                <form className="space-y-5" onSubmit={handleSubmit}>
                  {/* Name (register only) */}
                  {!isLogin && (
                    <div className="animate-element animate-delay-300">
                      <label className="text-sm font-medium text-muted-foreground">昵称</label>
                      <GlassInputWrapper>
                        <div className="relative">
                          <User className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                          <input name="name" type="text" placeholder="你的昵称" required
                            className="w-full bg-transparent text-sm p-4 pl-11 rounded-2xl focus:outline-none" />
                        </div>
                      </GlassInputWrapper>
                    </div>
                  )}

                  {/* Email */}
                  <div className={`animate-element ${isLogin ? "animate-delay-300" : "animate-delay-400"}`}>
                    <label className="text-sm font-medium text-muted-foreground">邮箱</label>
                    <GlassInputWrapper>
                      <div className="relative">
                        <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                        <input name="email" type="email" placeholder="your@email.com" required
                          className="w-full bg-transparent text-sm p-4 pl-11 rounded-2xl focus:outline-none" />
                      </div>
                    </GlassInputWrapper>
                  </div>

                  {/* Password (not for code login) */}
                  {(isLogin ? loginTab === "password" : true) && (
                    <div className={`animate-element ${isLogin ? "animate-delay-400" : "animate-delay-500"}`}>
                      <label className="text-sm font-medium text-muted-foreground">密码</label>
                      <GlassInputWrapper>
                        <div className="relative">
                          <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                          <input name="password" type={showPassword ? "text" : "password"}
                            placeholder={isLogin ? "输入密码" : "至少 6 位密码"} required minLength={6}
                            className="w-full bg-transparent text-sm p-4 pl-11 pr-12 rounded-2xl focus:outline-none" />
                          <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute inset-y-0 right-3 flex items-center">
                            {showPassword ? <EyeOff className="w-5 h-5 text-muted-foreground hover:text-foreground transition-colors" /> : <Eye className="w-5 h-5 text-muted-foreground hover:text-foreground transition-colors" />}
                          </button>
                        </div>
                      </GlassInputWrapper>
                    </div>
                  )}

                  {/* Remember + Reset (login password mode) */}
                  {isLogin && loginTab === "password" && (
                    <div className="animate-element animate-delay-500 flex items-center justify-between text-sm">
                      <label className="flex items-center gap-3 cursor-pointer">
                        <input type="checkbox" name="rememberMe" className="custom-checkbox" />
                        <span className="text-foreground/90">保持登录</span>
                      </label>
                      <button type="button" onClick={onResetPassword} className="hover:underline text-neutral-900 transition-colors text-[13px]">
                        忘记密码？
                      </button>
                    </div>
                  )}

                  <button type="submit" disabled={loading}
                    className={`animate-element ${isLogin ? "animate-delay-600" : "animate-delay-600"} w-full rounded-lg bg-neutral-900 py-3.5 text-[14px] font-medium text-white hover:bg-neutral-800 transition-colors disabled:opacity-50 flex items-center justify-center gap-2`}>
                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : (
                      <>
                        {isLogin ? (loginTab === "code" ? "发送验证码" : "登录") : "创建账户"}
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </form>

                <p className="animate-element animate-delay-800 text-center text-[13px] text-neutral-500">
                  {isLogin ? (
                    <>还没有账户？ <button onClick={onSwitchMode} className="text-neutral-900 font-medium hover:underline transition-colors">注册</button></>
                  ) : (
                    <>已有账户？ <button onClick={onSwitchMode} className="text-neutral-900 font-medium hover:underline transition-colors">登录</button></>
                  )}
                </p>
              </>
            )}
          </div>
        </div>
      </section>

      {/* Right column: hero image + testimonials */}
      {heroImageSrc && (
        <section className="hidden md:block flex-1 relative p-4">
          <div className="animate-slide-right animate-delay-300 absolute inset-4 rounded-2xl bg-cover bg-center" style={{ backgroundImage: `url(${heroImageSrc})` }} />
          <div className="absolute inset-4 rounded-2xl bg-gradient-to-t from-black/20 via-transparent to-transparent" />
          {testimonials.length > 0 && (
            <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex gap-4 px-8 w-full justify-center">
              <TestimonialCard testimonial={testimonials[0]} delay="animate-delay-1000" />
              {testimonials[1] && <div className="hidden xl:flex"><TestimonialCard testimonial={testimonials[1]} delay="animate-delay-1200" /></div>}
              {testimonials[2] && <div className="hidden 2xl:flex"><TestimonialCard testimonial={testimonials[2]} delay="animate-delay-1400" /></div>}
            </div>
          )}
        </section>
      )}
    </div>
  );
};
