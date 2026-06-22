"use client";
import { useRouter } from "next/navigation";
import { BACKEND_BASE } from "@/lib/graphql-client";
import { saveAuth } from "@/lib/auth";
import { SignInPage, type Testimonial } from "@/components/ui/sign-in";

const testimonials: Testimonial[] = [
  {
    avatarSrc: "https://randomuser.me/api/portraits/women/57.jpg",
    name: "Sarah Chen",
    handle: "@sarahdigital",
    text: "SelectPilot 的 AI 选品太强了，直接帮我找到了月销过万的蓝海品类！",
  },
  {
    avatarSrc: "https://randomuser.me/api/portraits/men/64.jpg",
    name: "Marcus Li",
    handle: "@marcustech",
    text: "一键对比 Amazon BSR 和 1688 采购成本，利润一目了然。",
  },
  {
    avatarSrc: "https://randomuser.me/api/portraits/men/32.jpg",
    name: "David Wang",
    handle: "@davidcreates",
    text: "9 级反爬引擎确实稳，之前用别的工具经常被封，这个从来没出过问题。",
  },
];

export default function LoginPage() {
  const router = useRouter();

  const handleLogin = async (data: Record<string, string>) => {
    const res = await fetch(`${BACKEND_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: data.email, password: data.password }),
    });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || "登录失败");
    saveAuth(json.token, json.email || data.email, json.plan || "free");
    router.push("/dashboard");
  };

  const handleSendCode = async (email: string) => {
    const res = await fetch(`${BACKEND_BASE}/auth/send-code`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, purpose: "login" }),
    });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || "发送失败");
  };

  const handleVerify = async (email: string, code: string) => {
    const res = await fetch(`${BACKEND_BASE}/auth/login-code`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, code }),
    });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || "验证失败");
    saveAuth(json.token, json.email || email, json.plan || "free");
    router.push("/dashboard");
  };

  return (
    <div className="bg-background text-foreground">
      <SignInPage
        mode="login"
        heroImageSrc="/images/login-hero.png"
        testimonials={testimonials}
        onSubmit={handleLogin}
        onSendCode={handleSendCode}
        onVerify={handleVerify}
        onSwitchMode={() => router.push("/register")}
      />
    </div>
  );
}
