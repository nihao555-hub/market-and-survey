"use client";
import { Sidebar } from "@/components/Sidebar";
import { ChatView } from "@/components/ChatView";

export default function Home() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-white">
      <Sidebar />
      <main className="flex-1 overflow-hidden">
        <ChatView />
      </main>
    </div>
  );
}
