"use client";

import React, { useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { Sidebar } from "@/components/Sidebar";
import { DashboardCard } from "@/components/DashboardCard";
import { useDashboards } from "@/hooks/useDashboards";
import { useAuth } from "@/lib/authContext";
import {
  LayoutDashboard,
  Filter,
  RefreshCw,
  FolderOpen,
  ShieldCheck,
} from "lucide-react";

export default function DashboardCatalogPage() {
  const { user } = useAuth();
  const { dashboards, isLoading, error, refetch } = useDashboards();
  const [selectedCategory, setSelectedCategory] = useState<string>("All");

  const categories = [
    "All",
    ...Array.from(new Set(dashboards.map((d) => d.category))),
  ];

  const filteredDashboards =
    selectedCategory === "All"
      ? dashboards
      : dashboards.filter((d) => d.category === selectedCategory);

  return (
    <AuthGuard>
      <div className="flex flex-1">
        <Sidebar />

        <main className="flex-1 p-6 sm:p-8 lg:p-10 max-w-7xl mx-auto w-full">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-200 dark:border-slate-800">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
                <LayoutDashboard className="h-6 w-6 text-blue-700 dark:text-blue-400" />
                Analytics Dashboards
              </h1>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                Authorized financial and operational intelligence dashboards tailored to your profile.
              </p>
            </div>

            <button
              onClick={() => refetch()}
              className="inline-flex items-center gap-1.5 self-start sm:self-auto rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
            >
              <RefreshCw className="h-3.5 w-3.5" /> Refresh List
            </button>
          </div>

          {/* Category Filter Pills */}
          <div className="mt-6 flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1 mr-2">
              <Filter className="h-3.5 w-3.5" /> Filter:
            </span>
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`rounded-full px-3.5 py-1 text-xs font-semibold transition ${
                  selectedCategory === cat
                    ? "bg-blue-700 text-white shadow-xs"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Error Banner */}
          {error && (
            <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-300">
              {error}
            </div>
          )}

          {/* Loading state */}
          {isLoading && (
            <div className="mt-12 flex flex-col items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-700 border-t-transparent" />
              <p className="mt-3 text-sm text-slate-500">Loading authorized dashboards...</p>
            </div>
          )}

          {/* Dashboards Grid */}
          {!isLoading && (
            <>
              {filteredDashboards.length === 0 ? (
                <div className="mt-12 flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 p-12 text-center dark:border-slate-800">
                  <FolderOpen className="h-10 w-10 text-slate-400" />
                  <h3 className="mt-3 text-base font-semibold text-slate-800 dark:text-slate-200">
                    No Dashboards Found
                  </h3>
                  <p className="mt-1 text-sm text-slate-500 max-w-sm">
                    No active dashboards match the selected category or your assigned roles.
                  </p>
                </div>
              ) : (
                <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
                  {filteredDashboards.map((dashboard) => (
                    <DashboardCard key={dashboard.id} dashboard={dashboard} />
                  ))}
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </AuthGuard>
  );
}
