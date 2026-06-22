"use client";
import { AppShell } from "@/components/AppShell";
import { AuthGuard } from "@/components/AuthGuard";

export default function DashboardPage() {
  return (
    <AuthGuard>
      <AppShell />
    </AuthGuard>
  );
}
