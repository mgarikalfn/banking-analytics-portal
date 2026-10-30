"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/authContext";
import {
  LayoutDashboard,
  ShieldAlert,
  Server,
  Layers,
  FileSpreadsheet,
} from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();

  const navigation = [
    {
      name: "Dashboards",
      href: "/dashboard",
      icon: LayoutDashboard,
      current: pathname.startsWith("/dashboard"),
    },
  ];

  if (user?.is_superuser) {
    navigation.push({
      name: "Admin & Roles",
      href: "/admin",
      icon: ShieldAlert,
      current: pathname.startsWith("/admin"),
    });
  }

  return (
    <aside className="w-64 shrink-0 border-r border-slate-200 bg-slate-50/50 p-4 dark:border-slate-800 dark:bg-slate-900/50 hidden md:block">
      <div className="space-y-6">
        <div>
          <h3 className="px-3 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Navigation
          </h3>
          <div className="mt-2 space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                    item.current
                      ? "bg-blue-700 text-white shadow-sm"
                      : "text-slate-700 hover:bg-slate-200/60 dark:text-slate-300 dark:hover:bg-slate-800"
                  }`}
                >
                  <Icon className="h-5 w-5 shrink-0" />
                  {item.name}
                </Link>
              );
            })}
          </div>
        </div>

        {/* User Roles Card */}
        {user && user.roles.length > 0 && (
          <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-xs dark:border-slate-800 dark:bg-slate-800/80">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-600 dark:text-slate-300">
              <Layers className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              <span>Assigned RBAC Roles</span>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {user.roles.map((r) => (
                <span
                  key={r.id}
                  className="rounded-md bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/40 dark:text-blue-300"
                >
                  {r.name}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Warehouse Isolation Security Reminder */}
        <div className="rounded-xl border border-emerald-200/80 bg-emerald-50/60 p-3.5 text-xs text-emerald-900 dark:border-emerald-800/40 dark:bg-emerald-950/30 dark:text-emerald-300">
          <div className="flex items-center gap-1.5 font-semibold">
            <Server className="h-4 w-4 text-emerald-600" />
            <span>Architecture Policy</span>
          </div>
          <p className="mt-1 text-[11px] leading-relaxed text-emerald-800 dark:text-emerald-400">
            Dedicated portal database. Real warehouse data is isolated and accessible only via secured Superset guest tokens.
          </p>
        </div>
      </div>
    </aside>
  );
}
