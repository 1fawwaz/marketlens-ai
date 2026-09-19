"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { LoginForm } from "@/components/auth/LoginForm";
import { AnomalySection } from "@/components/dashboard/AnomalySection";
import { DashboardHeader } from "@/components/dashboard/DashboardHeader";
import { DashboardNav } from "@/components/dashboard/DashboardNav";
import { ForecastSection } from "@/components/dashboard/ForecastSection";
import { GlobalFilters } from "@/components/dashboard/GlobalFilters";
import { InsightsSection } from "@/components/dashboard/InsightsSection";
import { InvestigationPanel } from "@/components/dashboard/InvestigationPanel";
import { VarianceChart } from "@/components/dashboard/VarianceChart";
import { EvidenceDrawer } from "@/components/ui/EvidenceDrawer";
import { buildKpiCards, KpiCard } from "@/components/ui/KpiCard";
import { EmptyPanel, ErrorPanel } from "@/components/ui/StatePanels";
import { apiFetch, login } from "@/lib/api";
import {
  aggregateMonthlyChart,
  buildExecutiveInsights,
  extractFilterOptions,
  filterVariance,
} from "@/lib/insights";
import type {
  Anomaly,
  DashboardFilters,
  ExecutiveInsight,
  ForecastPoint,
  InvestigationResult,
  Kpis,
  NavSection,
  SystemStatus,
  VarianceRow,
} from "@/lib/types";

function insightToQuestion(insight: ExecutiveInsight): string {
  const row = insight.evidenceDetails?.row as { target_month?: string } | undefined;
  const targetMonth = row?.target_month;

  switch (insight.type) {
    case "TARGET MISS":
      if (targetMonth) {
        return `Investigate target miss for ${targetMonth} — what factors contributed to the gap?`;
      }
      return `We missed the sales target by 12%. What factors contributed to the gap?`;
    case "OPPORTUNITY":
      if (targetMonth) {
        return `What drove the positive variance for ${targetMonth}?`;
      }
      return `What drove the positive variance for ${insight.context}?`;
    case "ANOMALY":
      return `Investigate the unusual revenue signal for ${insight.context}.`;
    case "FORECAST":
      return `Why is the ${insight.context} forecast below target?`;
    default:
      return insight.headline;
  }
}

export default function DashboardPage() {
  const [username, setUsername] = useState(
    process.env.NEXT_PUBLIC_DEV_USERNAME || "",
  );
  const [password, setPassword] = useState(
    process.env.NEXT_PUBLIC_DEV_PASSWORD || "",
  );
  const [loginLoading, setLoginLoading] = useState(false);
  const [token, setToken] = useState<string | null>(null);

  const [section, setSection] = useState<NavSection>("overview");
  const [filters, setFilters] = useState<DashboardFilters>({
    month: "",
    category: "",
    state: "",
    metric: "revenue",
  });
  const [headerMonth, setHeaderMonth] = useState("");
  const [darkMode, setDarkMode] = useState(false);
  const [showAllInsights, setShowAllInsights] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [kpis, setKpis] = useState<Kpis | null>(null);
  const [variance, setVariance] = useState<VarianceRow[]>([]);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [forecasts, setForecasts] = useState<ForecastPoint[]>([]);
  const [status, setStatus] = useState<SystemStatus | null>(null);

  const [question, setQuestion] = useState(
    "We missed the sales target by 12%. What factors contributed to the gap?",
  );
  const [investigation, setInvestigation] = useState<InvestigationResult | null>(null);
  const [investigationLoading, setInvestigationLoading] = useState(false);
  const [investigationError, setInvestigationError] = useState("");

  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [evidenceInsight, setEvidenceInsight] = useState<ExecutiveInsight | null>(null);
  const investigationRequestId = useRef(0);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  const loadDashboard = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const [k, v, a, s] = await Promise.all([
        apiFetch<Kpis>("/api/kpis", token),
        apiFetch<VarianceRow[]>("/api/variance", token),
        apiFetch<Anomaly[]>("/api/anomalies?dimension=state", token),
        apiFetch<SystemStatus>("/api/system/status", token).catch(() => null),
      ]);
      setKpis(k);
      setVariance(v);
      setAnomalies(a);
      setStatus(s);

      const worst = [...v]
        .filter((r) => Number(r.variance_pct) < 0)
        .sort((a, b) => Number(a.variance_pct) - Number(b.variance_pct))[0];
      const forecastCategory = worst?.category ?? v[0]?.category ?? "Clothing";

      const fc = await apiFetch<ForecastPoint[]>(
        `/api/forecasts/${encodeURIComponent(forecastCategory)}?horizon=30&model=xgboost`,
        token,
      ).catch(() => []);
      setForecasts(fc);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard data.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  async function handleLogin(e?: FormEvent) {
    e?.preventDefault();
    setLoginLoading(true);
    setError("");
    try {
      const auth = await login(username, password);
      setToken(auth.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setLoginLoading(false);
    }
  }

  const filterOptions = useMemo(
    () => extractFilterOptions(variance, anomalies),
    [variance, anomalies],
  );

  const activeFilters = useMemo(
    () => ({
      month: headerMonth || filters.month,
      category: filters.category,
      state: filters.state,
    }),
    [headerMonth, filters],
  );

  const filteredVariance = useMemo(
    () => filterVariance(variance, activeFilters),
    [variance, activeFilters],
  );

  const filteredAnomalies = useMemo(() => {
    return anomalies.filter((a) => {
      if (activeFilters.state && a.dimension_value !== activeFilters.state) {
        return false;
      }
      if (activeFilters.month && !String(a.anomaly_date).startsWith(activeFilters.month)) {
        return false;
      }
      return true;
    });
  }, [anomalies, activeFilters]);

  const { chartData, summary } = useMemo(
    () => aggregateMonthlyChart(filteredVariance),
    [filteredVariance],
  );

  const forecastCategory = useMemo(() => {
    if (filters.category) return filters.category;
    return summary.largestMissCategory !== "—"
      ? summary.largestMissCategory
      : variance[0]?.category ?? "Clothing";
  }, [filters.category, summary.largestMissCategory, variance]);

  useEffect(() => {
    if (!token || !forecastCategory) return;
    let cancelled = false;
    (async () => {
      try {
        const fc = await apiFetch<ForecastPoint[]>(
          `/api/forecasts/${encodeURIComponent(forecastCategory)}?horizon=30&model=xgboost`,
          token,
        );
        if (!cancelled) setForecasts(fc);
      } catch {
        if (!cancelled) setForecasts([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token, forecastCategory]);

  const forecastTarget = useMemo(() => {
    const rows = filteredVariance.filter((r) => r.category === forecastCategory);
    if (rows.length === 0) return 0;
    return rows.reduce((s, r) => s + Number(r.target_amount), 0);
  }, [filteredVariance, forecastCategory]);

  const executiveInsights = useMemo(
    () =>
      buildExecutiveInsights(
        filteredVariance,
        filteredAnomalies,
        forecasts,
        forecastCategory,
        forecastTarget,
      ),
    [filteredVariance, filteredAnomalies, forecasts, forecastCategory, forecastTarget],
  );

  const kpiCards = kpis ? buildKpiCards(kpis) : [];

  async function runInvestigation(questionText: string) {
    if (!token) return;

    const trimmed = questionText.trim();
    if (trimmed.length < 5) {
      setInvestigationError("Enter a question with at least 5 characters.");
      return;
    }

    const requestId = ++investigationRequestId.current;

    setInvestigationLoading(true);
    setInvestigationError("");
    setInvestigation(null);
    setEvidenceOpen(false);

    const contextMonth = (headerMonth || filters.month || "").trim();

    try {
      const result = await apiFetch<InvestigationResult>("/api/investigate", token, {
        method: "POST",
        body: JSON.stringify({
          question: trimmed,
          ...(contextMonth ? { context_month: contextMonth } : {}),
        }),
      });
      if (requestId !== investigationRequestId.current) return;
      setInvestigation(result);
      setQuestion(trimmed);
    } catch (err) {
      if (requestId !== investigationRequestId.current) return;
      setInvestigationError(
        err instanceof Error ? err.message : "Investigation failed.",
      );
    } finally {
      if (requestId === investigationRequestId.current) {
        setInvestigationLoading(false);
      }
    }
  }

  function handleInvestigateInsight(insight: ExecutiveInsight) {
    setQuestion(insightToQuestion(insight));
    setSection("investigations");
    setEvidenceInsight(insight);
  }

  function handleViewEvidence(insight: ExecutiveInsight) {
    setEvidenceInsight(insight);
    setEvidenceOpen(true);
  }

  function handleViewInvestigationEvidence() {
    setEvidenceOpen(true);
  }

  function handleLogout() {
    setToken(null);
    setKpis(null);
    setVariance([]);
    setInvestigation(null);
  }

  if (!token) {
    return (
      <LoginForm
        username={username}
        password={password}
        error={error}
        loading={loginLoading}
        onUsernameChange={setUsername}
        onPasswordChange={setPassword}
        onSubmit={handleLogin}
      />
    );
  }

  const backendUnavailable = error.includes("API error") || error.includes("Cannot reach");

  return (
    <div className="min-h-screen bg-panel">
      <main className="mx-auto max-w-7xl px-4 py-5 sm:px-6 lg:px-8">
        <DashboardHeader
          selectedMonth={headerMonth}
          months={filterOptions.months}
          onMonthChange={setHeaderMonth}
          onRefresh={loadDashboard}
          loading={loading}
          status={status}
          darkMode={darkMode}
          onToggleTheme={() => setDarkMode((d) => !d)}
          onLogout={handleLogout}
        />

        <div className="mt-4">
          <DashboardNav active={section} onChange={setSection} />
        </div>

        {error && !backendUnavailable && (
          <div className="mt-4">
            <ErrorPanel message={error} onRetry={loadDashboard} />
          </div>
        )}

        {backendUnavailable && (
          <div className="mt-6">
            <EmptyPanel
              title="Backend unavailable"
              description="Start the FastAPI server and refresh to load analytics."
              action={
                <button type="button" onClick={loadDashboard} className="btn-primary">
                  Retry connection
                </button>
              }
            />
          </div>
        )}

        {!backendUnavailable && (
          <>
            {(section === "overview" || section === "target") && (
              <div className="mt-5">
                <GlobalFilters
                  filters={filters}
                  months={filterOptions.months}
                  categories={filterOptions.categories}
                  states={filterOptions.states}
                  onChange={setFilters}
                />
              </div>
            )}

            {section === "overview" && (
              <div className="mt-6 space-y-6 animate-fade-in">
                <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {loading && !kpis
                    ? [1, 2, 3, 4].map((i) => <KpiCard key={i} label="" value="" loading />)
                    : kpiCards.map((card) => (
                        <KpiCard
                          key={card.label}
                          label={card.label}
                          value={card.value}
                          subtext={card.subtext}
                          trend={card.trend}
                        />
                      ))}
                </section>

                <VarianceChart data={chartData} summary={summary} loading={loading} />

                <InsightsSection
                  insights={executiveInsights}
                  loading={loading}
                  onInvestigate={handleInvestigateInsight}
                  onViewEvidence={handleViewEvidence}
                  onViewAll={() => setShowAllInsights(true)}
                />

                <div className="grid gap-6 lg:grid-cols-2">
                  <ForecastSection
                    category={forecastCategory}
                    forecasts={forecasts}
                    historical={filteredVariance}
                    targetTotal={forecastTarget}
                    loading={loading}
                    onViewDetails={() => setSection("forecasts")}
                  />
                  <AnomalySection anomalies={filteredAnomalies} loading={loading} limit={3} />
                </div>
              </div>
            )}

            {section === "target" && (
              <div className="mt-6 space-y-6 animate-fade-in">
                <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {kpiCards.map((card) => (
                    <KpiCard
                      key={card.label}
                      label={card.label}
                      value={card.value}
                      subtext={card.subtext}
                      trend={card.trend}
                    />
                  ))}
                </section>
                <VarianceChart data={chartData} summary={summary} loading={loading} />
              </div>
            )}

            {section === "forecasts" && (
              <div className="mt-6 animate-fade-in">
                <ForecastSection
                  category={forecastCategory}
                  forecasts={forecasts}
                  historical={filteredVariance}
                  targetTotal={forecastTarget}
                  loading={loading}
                />
              </div>
            )}

            {section === "anomalies" && (
              <div className="mt-6 animate-fade-in">
                <AnomalySection anomalies={filteredAnomalies} loading={loading} />
              </div>
            )}

            {section === "investigations" && (
              <div className="mt-6 animate-fade-in">
                <InvestigationPanel
                  question={question}
                  onQuestionChange={(q) => {
                    setQuestion(q);
                    setInvestigationError("");
                  }}
                  onRun={runInvestigation}
                  result={investigation}
                  loading={investigationLoading}
                  error={investigationError}
                  onViewEvidence={handleViewInvestigationEvidence}
                />
              </div>
            )}
          </>
        )}

        <p className="mt-8 text-center text-[11px] text-muted">
          Aggregated views only — no customer names
        </p>
      </main>

      <EvidenceDrawer
        open={evidenceOpen}
        onClose={() => {
          setEvidenceOpen(false);
          setEvidenceInsight(null);
        }}
        insight={evidenceInsight}
        investigation={investigation}
      />

      {showAllInsights && (
        <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center">
          <div
            className="absolute inset-0 bg-ink/40 backdrop-blur-sm"
            onClick={() => setShowAllInsights(false)}
            aria-hidden
          />
          <div className="relative z-10 max-h-[90vh] w-full max-w-5xl overflow-y-auto rounded-t-2xl bg-panel p-6 shadow-elevated sm:rounded-2xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-display text-lg font-semibold">All AI Insights</h2>
              <button
                type="button"
                onClick={() => setShowAllInsights(false)}
                className="btn-ghost"
              >
                Close
              </button>
            </div>
            <InsightsSection
              insights={executiveInsights}
              showAll
              onInvestigate={(insight) => {
                setShowAllInsights(false);
                handleInvestigateInsight(insight);
              }}
              onViewEvidence={handleViewEvidence}
            />
          </div>
        </div>
      )}
    </div>
  );
}
