"use client";

import React, { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AuthGuard } from "@/components/AuthGuard";
import { Sidebar } from "@/components/Sidebar";
import { SupersetDashboard } from "@/components/SupersetDashboard";
import { fetchApi } from "@/lib/api";
import { Dashboard } from "@/types/dashboard";
import { ArrowLeft, MapPin } from "lucide-react";

function DashboardDetailView() {
  const params = useParams();
  const rawId = params?.id;
  const dashboardId = typeof rawId === "string" ? parseInt(rawId, 10) : 0;

  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!dashboardId) return;

    async function loadDashboard() {
      try {
        const data = await fetchApi<Dashboard>(`/api/v1/dashboards/${dashboardId}`);
        setDashboard(data);
      } catch (err: unknown) {
        if (err instanceof Error) {
          setErrorMessage(err.message);
        } else {
          setErrorMessage("Failed to load dashboard information");
        }
      } finally {
        setIsLoading(false);
      }
    }
    loadDashboard();
  }, [dashboardId]);

  return (
    <div className="flex flex-1">
      <Sidebar />

      <main className="flex-1 w-full min-w-0 p-4 sm:p-6 lg:p-8">
        {/* Breadcrumb & Navigation */}
        <div className="mb-4">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-blue-700 dark:text-slate-400 dark:hover:text-blue-400 transition"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back to Dashboards
          </Link>
        </div>

        {isLoading && (
          <div className="flex h-64 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-700 border-t-transparent" />
          </div>
        )}

        {errorMessage && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-900 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-300">
            <h3 className="font-bold">Access Verification Error</h3>
            <p className="mt-1 text-sm">{errorMessage}</p>
            <Link
              href="/dashboard"
              className="mt-4 inline-block rounded-lg bg-red-600 px-4 py-2 text-xs font-semibold text-white"
            >
              Return to Dashboard Catalog
            </Link>
          </div>
        )}

        {dashboard && !isLoading && (
          <div className="space-y-6">
            {/* Dashboard Title & Metadata Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-200 dark:border-slate-800">
              <div>
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-semibold text-blue-800 dark:bg-blue-900/50 dark:text-blue-300">
                    {dashboard.category}
                  </span>
                  {dashboard.requires_branch_scope && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-semibold text-purple-800 dark:bg-purple-900/50 dark:text-purple-300">
                      <MapPin className="h-3 w-3" /> Branch Scoped
                    </span>
                  )}
                </div>
                <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                  {dashboard.title}
                </h1>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                  {dashboard.description}
                </p>
              </div>
            </div>

            {/* Superset Embedded SDK Component */}
            <SupersetDashboard
              dashboardId={dashboard.id}
              dashboardTitle={dashboard.title}
            />
          </div>
        )}
      </main>
    </div>
  );
}

export default function DashboardDetailPage() {
  return (
    <AuthGuard>
      <Suspense
        fallback={
          <div className="flex min-h-[60vh] items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-700 border-t-transparent" />
          </div>
        }
      >
        <DashboardDetailView />
      </Suspense>
    </AuthGuard>
  );
}
