"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/lib/authContext";
import { Landmark, LogOut, ShieldCheck, UserCheck, MapPin } from "lucide-react";

export function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-200 bg-white/95 backdrop-blur dark:border-slate-800 dark:bg-slate-900/95">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand / Logo */}
        <div className="flex items-center gap-3">
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-700 text-white shadow-sm">
              <Landmark className="h-6 w-6" />
            </div>
            <div>
              <span className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">
                ApexBank
              </span>
              <span className="ml-1 text-xs font-semibold uppercase tracking-wider text-blue-700 dark:text-blue-400">
                Analytics Portal
              </span>
            </div>
          </Link>
        </div>

        {/* User profile & actions */}
        {user ? (
          <div className="flex items-center gap-4">
            <div className="hidden sm:flex flex-col text-right">
              <div className="flex items-center justify-end gap-1.5">
                <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                  {user.full_name}
                </span>
                {user.is_superuser && (
                  <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                    <ShieldCheck className="mr-1 h-3 w-3" /> Admin
                  </span>
                )}
              </div>
              <div className="flex items-center justify-end gap-2 text-xs text-slate-500 dark:text-slate-400">
                <span>{user.email}</span>
                {user.assigned_branch_id && (
                  <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-1.5 py-0.5 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                    <MapPin className="h-3 w-3" />
                    Branch: {user.assigned_branch_id}
                  </span>
                )}
              </div>
            </div>

            {/* Logout button */}
            <button
              onClick={() => logout()}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 hover:text-red-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
              title="Sign Out"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden md:inline">Sign Out</span>
            </button>
          </div>
        ) : (
          <Link
            href="/login"
            className="inline-flex items-center gap-2 rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white shadow transition hover:bg-blue-800"
          >
            <UserCheck className="h-4 w-4" /> Sign In
          </Link>
        )}
      </div>
    </header>
  );
}
