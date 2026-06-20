"use client";
import { useEffect, useState } from "react";
import { LandingPage } from "@/components/landing/LandingPage";
import { AppShell } from "@/components/AppShell";

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const t = localStorage.getItem("auth_token");
    setToken(t);
    setChecking(false);
  }, []);

  if (checking) return null;
  if (token) return <AppShell />;
  return <LandingPage />;
}
