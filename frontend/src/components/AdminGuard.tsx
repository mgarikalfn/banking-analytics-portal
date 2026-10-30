"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/authContext";
import { ShieldAlert } from "lucide-react";

export function AdminGuard({ children }: { children: React.ReactNode }) {
  const { user, isLoading, isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-700 border-t-transparent" />
      </div>
    );
  }

  if (!user?.is_superuser) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center text-center p-6">
        <div className="rounded-full bg-red-100 p-4 text-red-600 dark:bg-red-950/50">
          <ShieldAlert className="h-10 w-10" />
        </div>
        <h2 className="mt-4 text-xl font-bold text-slate-900 dark:text-white">
          Administrator Privileges Required
        </h2>
        <p className="mt-2 max-w-md text-sm text-slate-600 dark:text-slate-400">
          Your account does not possess superuser privileges to access the administrative configuration portal.
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
