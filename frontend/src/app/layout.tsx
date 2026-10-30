import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/authContext";
import { Navbar } from "@/components/Navbar";

export const metadata: Metadata = {
  title: "Banking Analytics Portal | Enterprise BI & Intelligence",
  description:
    "Secure, role-based analytics portal powered by FastAPI and Apache Superset embedded dashboards.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased dark:bg-slate-950 dark:text-slate-100 flex flex-col">
        <AuthProvider>
          <Navbar />
          <div className="flex-1 flex flex-col">{children}</div>
        </AuthProvider>
      </body>
    </html>
  );
}
