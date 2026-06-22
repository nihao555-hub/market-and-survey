"use client";
import { useRouter } from "next/navigation";
import { BACKEND_BASE } from "@/lib/graphql-client";
import { saveAuth } from "@/lib/auth";
import { SignInPage, type Testimonial } from "@/components/ui/sign-in";

const testimonials: Testimonial[] = [
  {
    avatarSrc: "https://randomuser.me/api/portraits/women/44.jpg",
    name: "Emily Zhang",
    handle: "@emilyzhang",
    text: "注册 3 分钟就跑完了第一份选品报告，数据比我花三天调研的还详细。",
  },
  {
    avatarSrc: "https://randomuser.me/api/portraits/men/22.jpg",
    name: "Kevin Liu",
    handle: "@kevinliu_ecom",
    text: "免费版就够我个人卖家用了，升级专业版后 ECharts 报告直接给投资人看。",
  },
  {
    avatarSrc: "https://randomuser.me/api/portraits/women/68.jpg",
    name: "Anna Kim",
    handle: "@annakim",
    text: "覆盖 26 个国家的市场数据，终于不用一个个站点去扒数据了。",
  },
];

export default function RegisterPage() {
  const router = useRouter();

  const handleRegister = async (data: Record<string, string>) => {
    const res = await fetch(`${BACKEND_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: data.name, email: data.email, password: data.password }),
    });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || "注册失败");
  };

  const handleSendCode = async (email: string) => {
    const res = await fetch(`${BACKEND_BASE}/auth/send-code`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, purpose: "verify" }),
    });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || "发送失败");
  };

  const handleVerify = async (email: string, code: string) => {
    const res = await fetch(`${BACKEND_BASE}/auth/verify-email`, {
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
        mode="register"
        heroImageSrc="/images/login-hero.png"
        testimonials={testimonials}
        onSubmit={handleRegister}
        onSendCode={handleSendCode}
        onVerify={handleVerify}
        onSwitchMode={() => router.push("/login")}
      />
    </div>
  );
}
