"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/authContext";
import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  Lock,
  ShieldCheck,
  Building,
} from "lucide-react";

export default function Home() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push("/dashboard");
    }
  }, [isLoading, isAuthenticated, router]);

  return (
    <main className="flex-1">
      {/* Hero section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-blue-50/50 via-white to-slate-50 py-20 px-4 sm:px-6 lg:px-8 dark:from-slate-900 dark:via-slate-950 dark:to-slate-900">
        <div className="mx-auto max-w-5xl text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-100/60 px-4 py-1.5 text-xs font-semibold text-blue-800 dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-300">
            <ShieldCheck className="h-4 w-4" /> Enterprise Banking Intelligence
          </div>

          <h1 className="mt-6 text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl lg:text-6xl dark:text-white">
            Secure Banking Analytics Portal
          </h1>

          <p className="mx-auto mt-5 max-w-2xl text-lg text-slate-600 dark:text-slate-300">
            Unified financial dashboards, portfolio risk monitoring, and operational telemetry powered by Apache Superset and secured with role-based access control.
          </p>

          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <Link
              href="/login"
              className="inline-flex items-center gap-2 rounded-xl bg-blue-700 px-6 py-3.5 text-base font-semibold text-white shadow-md transition hover:bg-blue-800 hover:shadow-lg"
            >
              Access Analytics Portal
              <ArrowRight className="h-5 w-5" />
            </Link>
          </div>

          {/* Architecture highlights */}
          <div className="mt-16 grid grid-cols-1 gap-6 sm:grid-cols-3 text-left">
            <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-xs backdrop-blur dark:border-slate-800 dark:bg-slate-900/80">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                <Lock className="h-5 w-5" />
              </div>
              <h3 className="mt-4 text-base font-bold text-slate-900 dark:text-white">
                HTTP-Only Cookie Auth & CSRF
              </h3>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                Session tokens never stored in localStorage. Double-submit CSRF protection on state mutations with Argon2 password hashing.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-xs backdrop-blur dark:border-slate-800 dark:bg-slate-900/80">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
                <BarChart3 className="h-5 w-5" />
              </div>
              <h3 className="mt-4 text-base font-bold text-slate-900 dark:text-white">
                Superset Embedded SDK
              </h3>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                Backend signs guest tokens with strictly scoped dashboard permissions. Service credentials never touch the browser.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-xs backdrop-blur dark:border-slate-800 dark:bg-slate-900/80">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300">
                <Building className="h-5 w-5" />
              </div>
              <h3 className="mt-4 text-base font-bold text-slate-900 dark:text-white">
                Dedicated App Database
              </h3>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                Strict isolation: user credentials and portal metadata reside in a separate PostgreSQL database, keeping warehouse records untouched.
              </p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
