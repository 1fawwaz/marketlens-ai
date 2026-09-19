"use client";

import { FormEvent } from "react";

type LoginFormProps = {
  username: string;
  password: string;
  error: string;
  loading: boolean;
  onUsernameChange: (v: string) => void;
  onPasswordChange: (v: string) => void;
  onSubmit: (e?: FormEvent) => void;
};

export function LoginForm({
  username,
  password,
  error,
  loading,
  onUsernameChange,
  onPasswordChange,
  onSubmit,
}: LoginFormProps) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-panel p-6">
      <div className="w-full max-w-md animate-fade-in">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-accent font-display text-lg font-bold text-white">
            ML
          </div>
          <h1 className="font-display text-2xl font-semibold tracking-tight">MarketLens AI</h1>
          <p className="mt-1 text-sm text-muted">AI-powered target variance intelligence</p>
        </div>

        <form onSubmit={onSubmit} className="card space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-muted" htmlFor="username">
              Username
            </label>
            <input
              id="username"
              className="w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm focus:border-accent"
              placeholder="Enter username"
              value={username}
              onChange={(e) => onUsernameChange(e.target.value)}
              autoComplete="username"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              className="w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm focus:border-accent"
              placeholder="Enter password"
              type="password"
              value={password}
              onChange={(e) => onPasswordChange(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          <button className="btn-primary w-full py-2.5" type="submit" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"}
          </button>
          {error && (
            <p className="rounded-lg bg-negative-muted px-3 py-2 text-sm text-negative">
              {error}
            </p>
          )}
        </form>

        <p className="mt-6 text-center text-xs text-muted">
          Aggregated views only — no customer names
        </p>
      </div>
    </main>
  );
}
