"use client";
import React from "react";
import { cn } from "@/lib/utils";

/** 进行中文案的水波光效（steering §4.4） */
export function ShimmeringText({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <span className={cn("shimmering-text", className)}>{children}</span>;
}
