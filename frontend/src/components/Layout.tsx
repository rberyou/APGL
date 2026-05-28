import type { PropsWithChildren, ReactNode } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  ClipboardCheck,
  Home,
  LogOut,
  Plus,
  RotateCcw,
  TriangleAlert
} from "lucide-react";
import { api } from "../api/client";

const navItems = [
  { to: "/", label: "Dashboard", icon: Home },
  { to: "/projects/new", label: "New project", icon: Plus },
  { to: "/reviews", label: "Review", icon: RotateCcw },
  { to: "/mistakes", label: "Mistakes", icon: TriangleAlert }
];

export function Layout({ children }: PropsWithChildren) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  async function logout() {
    await api.logout();
    queryClient.clear();
    navigate("/login");
  }

  return (
    <div className="min-h-screen bg-paper">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <Link to="/" className="flex items-center gap-3 text-ink">
            <span className="flex h-10 w-10 items-center justify-center rounded-md bg-teal text-white">
              <BookOpen size={22} aria-hidden="true" />
            </span>
            <span>
              <span className="block text-base font-bold">APGL</span>
              <span className="block text-xs text-slate-500">AI guided learning</span>
            </span>
          </Link>
          <nav className="flex flex-wrap items-center gap-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    [
                      "focus-ring inline-flex min-h-10 items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold transition",
                      isActive
                        ? "bg-teal text-white"
                        : "border border-line bg-white text-ink hover:border-teal hover:text-teal"
                    ].join(" ")
                  }
                >
                  <Icon size={16} aria-hidden="true" />
                  {item.label}
                </NavLink>
              );
            })}
            <button className="btn-secondary" onClick={logout} title="Log out">
              <LogOut size={16} aria-hidden="true" />
              Log out
            </button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
    </div>
  );
}

export function EmptyState({
  title,
  body,
  action
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <div className="panel flex min-h-56 flex-col items-center justify-center text-center">
      <ClipboardCheck className="mb-3 text-teal" size={32} aria-hidden="true" />
      <h2 className="text-lg font-bold text-ink">{title}</h2>
      <p className="mt-2 max-w-xl text-sm leading-6 text-slate-600">{body}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {message}
    </div>
  );
}

export function LoadingBlock({ label = "Loading" }: { label?: string }) {
  return (
    <div className="panel flex min-h-40 items-center justify-center text-sm font-semibold text-slate-500">
      {label}
    </div>
  );
}
