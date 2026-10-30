"use client";

import React from "react";
import Link from "next/link";
import { Dashboard } from "@/types/dashboard";
import {
  ArrowRight,
  BarChart3,
  Building2,
  Lock,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";

interface DashboardCardProps {
  dashboard: Dashboard;
}

export function DashboardCard({ dashboard }: DashboardCardProps) {
  const getCategoryIcon = (category: string) => {
    switch (category.toLowerCase()) {
      case "executive":
        return <TrendingUp className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />;
      case "operations":
        return <Building2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />;
      case "risk & compliance":
      case "risk":
        return <ShieldAlert className="h-5 w-5 text-amber-600 dark:text-amber-400" />;
      default:
        return <BarChart3 className="h-5 w-5 text-blue-600 dark:text-blue-400" />;
    }
  };

  return (
    <div className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-xs transition hover:border-slate-300 hover:shadow-md dark:border-slate-800 dark:bg-slate-800/90">
      <div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="rounded-lg bg-slate-100 p-2 dark:bg-slate-700">
              {getCategoryIcon(dashboard.category)}
            </div>
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700 dark:bg-slate-700 dark:text-slate-300">
              {dashboard.category}
            </span>
          </div>

          {dashboard.requires_branch_scope && (
            <span className="rounded-full bg-purple-50 px-2 py-0.5 text-xs font-medium text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
              Branch-Scoped
            </span>
          )}
        </div>

        <h3 className="mt-4 text-base font-bold text-slate-900 dark:text-white">
          {dashboard.title}
        </h3>
        <p className="mt-1.5 text-sm leading-relaxed text-slate-600 dark:text-slate-400 line-clamp-2">
          {dashboard.description}
        </p>
      </div>

      <div className="mt-5 pt-4 border-t border-slate-100 dark:border-slate-700/60 flex items-center justify-between">
        <div className="flex items-center gap-1 text-xs text-slate-500">
          <Lock className="h-3.5 w-3.5" />
          <span>
            {dashboard.allowed_roles.map((r) => r.name).join(", ") || "All roles"}
          </span>
        </div>

        <Link
          href={`/dashboard/${dashboard.id}`}
          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-700 px-3 py-1.5 text-xs font-semibold text-white shadow-xs transition hover:bg-blue-800"
        >
          View Dashboard
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </div>
  );
}
