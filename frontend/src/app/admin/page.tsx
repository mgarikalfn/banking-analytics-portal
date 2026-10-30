"use client";

import React, { useEffect, useState } from "react";
import { AdminGuard } from "@/components/AdminGuard";
import { Sidebar } from "@/components/Sidebar";
import { fetchApi } from "@/lib/api";
import { User, Role } from "@/types/auth";
import { SupersetStatus } from "@/types/dashboard";
import {
  ShieldAlert,
  Users,
  Server,
  UserPlus,
  CheckCircle2,
  XCircle,
  RefreshCw,
  MapPin,
  Lock,
} from "lucide-react";

export default function AdminPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [supersetStatus, setSupersetStatus] = useState<SupersetStatus | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [statusLoading, setStatusLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // New user form state
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [branchId, setBranchId] = useState("");
  const [selectedRoleIds, setSelectedRoleIds] = useState<number[]>([]);
  const [isSuperuser, setIsSuperuser] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [usersData, rolesData] = await Promise.all([
        fetchApi<User[]>("/api/v1/users/"),
        fetchApi<Role[]>("/api/v1/roles/"),
      ]);
      setUsers(usersData);
      setRoles(rolesData);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load admin data";
      setMessage({ type: "error", text: msg });
    } finally {
      setIsLoading(false);
    }
  };

  const checkSupersetHealth = async () => {
    setStatusLoading(true);
    try {
      const status = await fetchApi<SupersetStatus>("/api/v1/superset/status");
      setSupersetStatus(status);
    } catch (err: unknown) {
      setSupersetStatus({
        configured: false,
        connected: false,
        superset_url: "http://localhost:8088",
        status_detail: "Failed to communicate with portal backend.",
      });
    } finally {
      setStatusLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    checkSupersetHealth();
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setMessage(null);

    try {
      await fetchApi<User>("/api/v1/users/", {
        method: "POST",
        body: JSON.stringify({
          email,
          full_name: fullName,
          password,
          assigned_branch_id: branchId.trim() || null,
          is_superuser: isSuperuser,
          role_ids: selectedRoleIds,
        }),
      });

      setMessage({ type: "success", text: `User ${email} created successfully!` });
      setEmail("");
      setFullName("");
      setPassword("");
      setBranchId("");
      setSelectedRoleIds([]);
      setIsSuperuser(false);
      loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create user";
      setMessage({ type: "error", text: msg });
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleRoleSelection = (roleId: number) => {
    setSelectedRoleIds((prev) =>
      prev.includes(roleId) ? prev.filter((id) => id !== roleId) : [...prev, roleId]
    );
  };

  return (
    <AdminGuard>
      <div className="flex flex-1">
        <Sidebar />

        <main className="flex-1 p-6 sm:p-8 lg:p-10 max-w-7xl mx-auto w-full space-y-8">
          {/* Header */}
          <div className="pb-6 border-b border-slate-200 dark:border-slate-800">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
              <ShieldAlert className="h-6 w-6 text-blue-700 dark:text-blue-400" />
              Administration & RBAC Management
            </h1>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              Manage portal personnel, role assignments, and check Apache Superset embedding status.
            </p>
          </div>

          {message && (
            <div
              className={`rounded-xl p-4 text-sm font-medium border ${
                message.type === "success"
                  ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300"
                  : "border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300"
              }`}
            >
              {message.text}
            </div>
          )}

          {/* Superset Diagnostic Card */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2.5">
                <Server className="h-5 w-5 text-indigo-600" />
                <h2 className="text-base font-bold text-slate-900 dark:text-white">
                  Apache Superset Diagnostic Telemetry
                </h2>
              </div>
              <button
                onClick={checkSupersetHealth}
                disabled={statusLoading}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${statusLoading ? "animate-spin" : ""}`} />
                Test Superset Ping
              </button>
            </div>

            {supersetStatus && (
              <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3 text-sm">
                <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-800/50">
                  <span className="text-xs text-slate-500 uppercase font-semibold">Base URL</span>
                  <p className="mt-1 font-mono text-xs font-medium text-slate-800 dark:text-slate-200">
                    {supersetStatus.superset_url}
                  </p>
                </div>

                <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-800/50">
                  <span className="text-xs text-slate-500 uppercase font-semibold">Service Credentials</span>
                  <div className="mt-1 flex items-center gap-1.5 font-medium">
                    {supersetStatus.configured ? (
                      <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 text-xs">
                        <CheckCircle2 className="h-4 w-4" /> Production Configured
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400 text-xs">
                        <XCircle className="h-4 w-4" /> Placeholder Credentials
                      </span>
                    )}
                  </div>
                </div>

                <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-800/50">
                  <span className="text-xs text-slate-500 uppercase font-semibold">Connection Status</span>
                  <div className="mt-1 flex items-center gap-1.5 font-medium">
                    {supersetStatus.connected ? (
                      <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 text-xs">
                        <CheckCircle2 className="h-4 w-4" /> Service Reachable
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-red-600 dark:text-red-400 text-xs" title={supersetStatus.status_detail}>
                        <XCircle className="h-4 w-4" /> {supersetStatus.status_detail.slice(0, 30)}...
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* User Registration Form */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center gap-2.5 pb-4 border-b border-slate-100 dark:border-slate-800">
              <UserPlus className="h-5 w-5 text-blue-700" />
              <h2 className="text-base font-bold text-slate-900 dark:text-white">
                Create New Authorized User
              </h2>
            </div>

            <form onSubmit={handleCreateUser} className="mt-5 space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-semibold uppercase text-slate-700 dark:text-slate-300">
                    Full Name
                  </label>
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Jane Doe"
                    className="mt-1.5 block w-full rounded-lg border border-slate-300 bg-white py-2 px-3 text-sm focus:border-blue-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase text-slate-700 dark:text-slate-300">
                    Email Address
                  </label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="jdoe@bankportal.internal"
                    className="mt-1.5 block w-full rounded-lg border border-slate-300 bg-white py-2 px-3 text-sm focus:border-blue-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase text-slate-700 dark:text-slate-300">
                    Temporary Password (Argon2 Hashed)
                  </label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Minimum 8 characters"
                    className="mt-1.5 block w-full rounded-lg border border-slate-300 bg-white py-2 px-3 text-sm focus:border-blue-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase text-slate-700 dark:text-slate-300">
                    Assigned Branch ID (Optional)
                  </label>
                  <input
                    type="text"
                    value={branchId}
                    onChange={(e) => setBranchId(e.target.value)}
                    placeholder="e.g. BR-101"
                    className="mt-1.5 block w-full rounded-lg border border-slate-300 bg-white py-2 px-3 text-sm focus:border-blue-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                  />
                </div>
              </div>

              {/* Roles selection */}
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-700 dark:text-slate-300 mb-2">
                  Assign RBAC Roles
                </label>
                <div className="flex flex-wrap gap-2">
                  {roles.map((r) => {
                    const isSelected = selectedRoleIds.includes(r.id);
                    return (
                      <button
                        type="button"
                        key={r.id}
                        onClick={() => toggleRoleSelection(r.id)}
                        className={`rounded-lg px-3 py-1.5 text-xs font-medium border transition ${
                          isSelected
                            ? "bg-blue-700 text-white border-blue-700 shadow-xs"
                            : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-300"
                        }`}
                      >
                        {r.name}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input
                  id="isSuperuser"
                  type="checkbox"
                  checked={isSuperuser}
                  onChange={(e) => setIsSuperuser(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="isSuperuser" className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Grant Full Superuser Privileges
                </label>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-700 px-5 py-2.5 text-sm font-semibold text-white shadow-xs transition hover:bg-blue-800 disabled:opacity-50"
              >
                <UserPlus className="h-4 w-4" /> Create User
              </button>
            </form>
          </div>

          {/* Users Table */}
          <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden dark:border-slate-800 dark:bg-slate-900">
            <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Users className="h-5 w-5 text-blue-700" />
                <h2 className="text-base font-bold text-slate-900 dark:text-white">
                  Registered Personnel ({users.length})
                </h2>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
                <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-400 dark:bg-slate-800/60 dark:text-slate-400">
                  <tr>
                    <th className="px-6 py-3.5">User</th>
                    <th className="px-6 py-3.5">Branch</th>
                    <th className="px-6 py-3.5">Assigned Roles</th>
                    <th className="px-6 py-3.5">Type</th>
                    <th className="px-6 py-3.5">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                      <td className="px-6 py-4">
                        <div className="font-semibold text-slate-900 dark:text-white">
                          {u.full_name}
                        </div>
                        <div className="text-xs text-slate-400">{u.email}</div>
                      </td>
                      <td className="px-6 py-4">
                        {u.assigned_branch_id ? (
                          <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                            <MapPin className="h-3 w-3" />
                            {u.assigned_branch_id}
                          </span>
                        ) : (
                          <span className="text-xs text-slate-400">—</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-wrap gap-1">
                          {u.roles.map((r) => (
                            <span
                              key={r.id}
                              className="rounded bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/40 dark:text-blue-300"
                            >
                              {r.name}
                            </span>
                          ))}
                          {u.roles.length === 0 && (
                            <span className="text-xs text-slate-400">None</span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        {u.is_superuser ? (
                          <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                            Superuser
                          </span>
                        ) : (
                          <span className="text-xs text-slate-500">Standard</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {u.is_active ? (
                          <span className="inline-flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
                            <CheckCircle2 className="h-3.5 w-3.5" /> Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs text-red-500">
                            <XCircle className="h-3.5 w-3.5" /> Suspended
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </main>
      </div>
    </AdminGuard>
  );
}
