import { FormEvent, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Brain, LogIn, UserPlus } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { ErrorMessage } from "../components/Layout";

export default function AuthPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const from = (location.state as { from?: Location } | null)?.from?.pathname || "/";

  const mutation = useMutation({
    mutationFn: () =>
      mode === "login" ? api.login(email, password) : api.register(email, password),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me"] });
      navigate(from, { replace: true });
    }
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    mutation.mutate();
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-paper px-4 py-8">
      <section className="w-full max-w-md rounded-lg border border-line bg-white p-6 shadow-sm">
        <div className="mb-6 flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-md bg-teal text-white">
            <Brain size={24} aria-hidden="true" />
          </span>
          <div>
            <h1 className="text-xl font-bold text-ink">APGL</h1>
            <p className="text-sm text-slate-500">Your AI private tutor workspace</p>
          </div>
        </div>

        <div className="mb-5 grid grid-cols-2 rounded-md border border-line bg-paper p-1">
          <button
            type="button"
            className={`focus-ring rounded px-3 py-2 text-sm font-semibold ${
              mode === "login" ? "bg-white text-teal shadow-sm" : "text-slate-600"
            }`}
            onClick={() => setMode("login")}
          >
            Log in
          </button>
          <button
            type="button"
            className={`focus-ring rounded px-3 py-2 text-sm font-semibold ${
              mode === "register" ? "bg-white text-teal shadow-sm" : "text-slate-600"
            }`}
            onClick={() => setMode("register")}
          >
            Register
          </button>
        </div>

        <form className="space-y-4" onSubmit={submit}>
          <label className="block">
            <span className="mb-1 block text-sm font-semibold text-ink">Email</span>
            <input
              className="field"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-semibold text-ink">Password</span>
            <input
              className="field"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={8}
              required
            />
          </label>
          {mutation.error ? <ErrorMessage message={mutation.error.message} /> : null}
          <button className="btn-primary w-full" disabled={mutation.isPending}>
            {mode === "login" ? <LogIn size={16} /> : <UserPlus size={16} />}
            {mutation.isPending ? "Working" : mode === "login" ? "Log in" : "Create account"}
          </button>
        </form>
      </section>
    </main>
  );
}

