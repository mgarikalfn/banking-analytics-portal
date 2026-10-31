"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { embedDashboard } from "@superset-ui/embedded-sdk";
import { fetchApi } from "@/lib/api";
import { GuestTokenResponse } from "@/types/dashboard";
import {
  AlertTriangle,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";

interface SupersetDashboardProps {
  dashboardId: number;
  dashboardTitle: string;
}

export function SupersetDashboard({
  dashboardId,
  dashboardTitle,
}: SupersetDashboardProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const [initialData, setInitialData] = useState<GuestTokenResponse | null>(null);

  const loadAndEmbed = useCallback(async () => {
    setIsLoading(true);
    setErrorDetail(null);

    try {
      // 1. Fetch the backend-issued guest token and browser-facing Superset URL.
      const tokenData = await fetchApi<GuestTokenResponse>(
        "/api/v1/superset/guest-token",
        {
          method: "POST",
          body: JSON.stringify({ dashboard_id: dashboardId }),
        }
      );
      setInitialData(tokenData);

      if (!containerRef.current) return;

      // Clear container before embedding
      containerRef.current.innerHTML = "";

      // 2. Embed dashboard using Apache Superset Embedded SDK
      await embedDashboard({
        id: tokenData.superset_dashboard_id,
        // The backend returns this URL for browser access; credentials stay server-side.
        supersetDomain: tokenData.superset_domain,
        mountPoint: containerRef.current,
        fetchGuestToken: async () => {
          // Callback invoked by the SDK when token needs initial fetch or refresh
          const res = await fetchApi<GuestTokenResponse>(
            "/api/v1/superset/guest-token",
            {
              method: "POST",
              body: JSON.stringify({ dashboard_id: dashboardId }),
            }
          );
          return res.token;
        },
        dashboardUiConfig: {
          hideTitle: false,
          hideTab: false,
          hideChartControls: false,
          filters: {
            expanded: true,
          },
        },
      });

      // Modify the generated iframe to take full height
      const iframe = containerRef.current.querySelector("iframe");
      if (iframe) {
        iframe.style.width = "100%";
        iframe.style.height = "calc(100vh - 16rem)";
        iframe.style.border = "none";
        iframe.style.minHeight = "800px";
        iframe.style.display = "block";
      }

      setIsLoading(false);
    } catch (err: unknown) {
      setIsLoading(false);
      if (err instanceof Error) {
        setErrorDetail(err.message);
      } else {
        setErrorDetail("Failed to establish secure connection to Superset service.");
      }
    }
  }, [dashboardId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadAndEmbed();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadAndEmbed]);

  return (
    <div className="flex flex-col gap-4">
      {/* Security Context Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-blue-100 bg-blue-50/70 p-4 text-xs dark:border-blue-900/40 dark:bg-blue-950/20">
        <div className="flex items-center gap-2 text-blue-900 dark:text-blue-300">
          <ShieldCheck className="h-4 w-4 shrink-0 text-blue-700 dark:text-blue-400" />
          <span>
            <strong>Backend Security Protocol:</strong> Portal verified your role authorization before requesting a scoped guest token. No admin credentials exposed to browser.
          </span>
        </div>
        {initialData && (
          <span className="rounded bg-blue-100 px-2 py-0.5 font-mono text-[11px] text-blue-800 dark:bg-blue-900 dark:text-blue-200">
            Target UUID: {initialData.superset_dashboard_id}
          </span>
        )}
      </div>

      {/* Error state / Superset Integration Helper Banner */}
      {errorDetail && (
        <div className="rounded-xl border border-amber-300 bg-amber-50 p-6 text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-6 w-6 shrink-0 text-amber-600 dark:text-amber-400" />
            <div className="space-y-3">
              <div>
                <h4 className="text-base font-bold text-amber-900 dark:text-amber-100">
                  Superset Service Integration Notice
                </h4>
                <p className="mt-1 text-sm leading-relaxed text-amber-800 dark:text-amber-300">
                  {errorDetail}
                </p>
              </div>

              <div className="rounded-lg border border-amber-200/80 bg-white/80 p-4 text-xs dark:border-amber-900/50 dark:bg-slate-900/60">
                <p className="font-semibold text-slate-800 dark:text-slate-200">
                  Required Superset Configuration Checklist:
                </p>
                <ul className="mt-2 list-disc space-y-1 pl-4 text-slate-600 dark:text-slate-400">
                  <li>
                    Ensure Apache Superset is running and accessible (e.g. at{" "}
                    <code className="font-mono bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded">
                      http://localhost:8088
                    </code>
                    ).
                  </li>
                  <li>
                    Configure real credentials in{" "}
                    <code className="font-mono bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded">
                      backend/.env
                    </code>
                    : <code className="font-mono">SUPERSET_ADMIN_USERNAME</code> and{" "}
                    <code className="font-mono">SUPERSET_ADMIN_PASSWORD</code>.
                  </li>
                  <li>
                    Enable feature flag in Superset{" "}
                    <code className="font-mono bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded">
                      superset_config.py
                    </code>
                    : <code className="font-mono">EMBEDDED_SUPERSET = True</code> and{" "}
                    <code className="font-mono">GUEST_ROLE_NAME = &quot;Public&quot;</code>.
                  </li>
                  <li>
                    In Superset, enable &quot;Embed Dashboard&quot; on the target dashboard to generate its unique Embedded UUID.
                  </li>
                </ul>
              </div>

              <button
                onClick={loadAndEmbed}
                className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-4 py-2 text-xs font-semibold text-white shadow-xs transition hover:bg-amber-700"
              >
                <RefreshCw className="h-3.5 w-3.5" /> Retry Connection
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Loading indicator */}
      {isLoading && (
        <div className="flex h-96 flex-col items-center justify-center rounded-xl border border-slate-200 bg-slate-50/50 dark:border-slate-800 dark:bg-slate-900/50">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-700 border-t-transparent" />
          <p className="mt-3 text-sm font-medium text-slate-600 dark:text-slate-400">
            Establishing secure guest session with Apache Superset...
          </p>
        </div>
      )}

      {/* Mount point for the Superset Embedded SDK */}
      <div
        ref={containerRef}
        aria-label={dashboardTitle}
        className={`w-full overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900 ${
          isLoading || errorDetail ? "hidden" : "block min-h-[800px]"
        }`}
      />
    </div>
  );
}
