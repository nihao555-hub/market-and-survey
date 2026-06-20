"use client";
import { useEffect, useState } from "react";
import { LandingPage } from "@/components/landing/LandingPage";
import { AppShell } from "@/components/AppShell";
import { AuthGuard } from "@/components/AuthGuard";
import { isAuthenticated } from "@/lib/auth";

export default function Home() {
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    setAuthed(isAuthenticated());
  }, []);

  if (authed === null) return null;
  if (authed) {
    return (
      <AuthGuard>
        <AppShell />
      </AuthGuard>
    );
  }
  return <LandingPage />;
}
