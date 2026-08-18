"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import type { BillingSummary, Transaction } from "@/lib/types";

const categoryLabels: Record<Transaction["category"], string> = {
  toll: "Pedágio",
  parking: "Estacionamento",
  fuel: "Combustível",
  drive_thru: "Drive-thru",
};

const money = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

const dateTime = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
});

function errorMessage(payload: unknown): string {
  if (payload && typeof payload === "object") {
    if ("message" in payload && typeof payload.message === "string") return payload.message;
    if ("detail" in payload && typeof payload.detail === "string") return payload.detail;
  }
  return "Não foi possível concluir a operação.";
}

async function readJson<T>(response: Response): Promise<T> {
  const payload: unknown = await response.json();
  if (!response.ok) throw new Error(errorMessage(payload));
  return payload as T;
}

export function Dashboard() {
  const [customerId, setCustomerId] = useState("demo-customer");
  const [customerDraft, setCustomerDraft] = useState("demo-customer");
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [summary, setSummary] = useState<BillingSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [mutating, setMutating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [form, setForm] = useState({
    amount: "12.50",
    category: "toll" as Transaction["category"],
    merchant: "Rodovia SP-123 Km 42",
  });

  const loadData = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const encoded = encodeURIComponent(customerId);
      const [transactionsResponse, summaryResponse] = await Promise.all([
        fetch(`/api/transactions?customer_id=${encoded}&limit=100`, { cache: "no-store" }),
        fetch(`/api/summary/${encoded}`, { cache: "no-store" }),
      ]);
      const [nextTransactions, nextSummary] = await Promise.all([
        readJson<Transaction[]>(transactionsResponse),
        readJson<BillingSummary>(summaryResponse),
      ]);
      setTransactions(nextTransactions.reverse());
      setSummary(nextSummary);
      setMessage(null);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao carregar o dashboard.");
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    const initialLoad = window.setTimeout(() => void loadData(true), 0);
    const interval = window.setInterval(() => void loadData(true), 8000);
    return () => {
      window.clearTimeout(initialLoad);
      window.clearInterval(interval);
    };
  }, [loadData]);

  const highestScore = useMemo(
    () => Math.max(0, ...transactions.map((transaction) => transaction.anomaly.score)),
    [transactions],
  );

  const submitTransaction = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMutating(true);
    try {
      const response = await fetch("/api/transactions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          external_id: `web-${Date.now()}`,
          customer_id: customerId,
          amount: form.amount,
          occurred_at: new Date().toISOString(),
          category: form.category,
          merchant: form.merchant,
        }),
      });
      await readJson<Transaction>(response);
      setMessage("Cobrança analisada com sucesso.");
      await loadData(true);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao registrar cobrança.");
    } finally {
      setMutating(false);
    }
  };

  const populateDemo = async () => {
    setMutating(true);
    setMessage("Criando histórico sintético…");
    const today = new Date();
    const base = Date.UTC(
      today.getUTCFullYear(),
      today.getUTCMonth(),
      today.getUTCDate() - 6,
      15,
    );
    const samples = [
      ["10.00", "toll", "Rodovia SP-123 Km 42", 0],
      ["10.50", "toll", "Rodovia SP-123 Km 42", 1],
      ["9.80", "parking", "Estacionamento Centro", 2],
      ["11.00", "toll", "Rodovia SP-123 Km 42", 3],
      ["10.20", "toll", "Rodovia SP-123 Km 42", 4],
      ["48.90", "toll", "Rodovia SP-123 Km 42", 5],
    ] as const;
    try {
      for (const [amount, category, merchant, day] of samples) {
        const response = await fetch("/api/transactions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            external_id: `demo-${Date.now()}-${day}`,
            customer_id: customerId,
            amount,
            occurred_at: new Date(base + day * 86_400_000).toISOString(),
            category,
            merchant,
          }),
        });
        await readJson<Transaction>(response);
      }
      setMessage("Cenário sintético criado: a cobrança de R$ 48,90 deve gerar um alerta.");
      await loadData(true);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha ao criar a demonstração.");
    } finally {
      setMutating(false);
    }
  };

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Mobility Guard — início">
          <span className="brand-mark">MG</span>
          <span><strong>Mobility</strong> Guard</span>
        </a>
        <div className="system-status"><span /> Sistema operacional</div>
      </header>

      <div className="page" id="top">
        <section className="hero">
          <div>
            <p className="eyebrow">Inteligência operacional</p>
            <h1>Cobranças sob controle.<br /><em>Riscos sob contexto.</em></h1>
            <p className="hero-copy">
              Monitoramento explicável de transações de mobilidade, com análise em tempo real
              e enriquecimento assíncrono por IA.
            </p>
          </div>
          <form
            className="customer-search"
            onSubmit={(event) => {
              event.preventDefault();
              if (customerDraft.trim()) setCustomerId(customerDraft.trim());
            }}
          >
            <label htmlFor="customer">Cliente monitorado</label>
            <div>
              <input
                id="customer"
                value={customerDraft}
                onChange={(event) => setCustomerDraft(event.target.value)}
                maxLength={120}
              />
              <button type="submit">Carregar</button>
            </div>
          </form>
        </section>

        {message && <div className="notice" role="status">{message}</div>}

        <section className="metrics" aria-label="Resumo do cliente">
          <article>
            <span>Volume analisado</span>
            <strong>{money.format(Number(summary?.total_amount ?? 0))}</strong>
            <small>{summary?.transaction_count ?? 0} transações</small>
          </article>
          <article>
            <span>Alertas ativos</span>
            <strong className="risk-value">{summary?.anomaly_count ?? 0}</strong>
            <small>Acima do limiar operacional</small>
          </article>
          <article>
            <span>Maior score</span>
            <strong>{Math.round(highestScore * 100)}%</strong>
            <small>Risco observado no período</small>
          </article>
          <article>
            <span>Motor de análise</span>
            <strong className="online">Online</strong>
            <small>Atualização automática a cada 8s</small>
          </article>
        </section>

        <section className="content-grid">
          <div className="panel transactions-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Atividade recente</p>
                <h2>Transações</h2>
              </div>
              <button className="ghost-button" onClick={() => void loadData()} disabled={loading}>
                Atualizar
              </button>
            </div>

            {loading ? (
              <div className="empty-state">Carregando análises…</div>
            ) : transactions.length === 0 ? (
              <div className="empty-state">
                <span>◎</span>
                <h3>Nenhuma cobrança encontrada</h3>
                <p>Registre uma transação ou gere o cenário sintético ao lado.</p>
              </div>
            ) : (
              <div className="transaction-list">
                {transactions.map((transaction) => (
                  <article className="transaction-row" key={transaction.id}>
                    <div className={`category-icon ${transaction.category}`}>
                      {transaction.category === "toll" ? "↗" : transaction.category === "parking" ? "P" : "◆"}
                    </div>
                    <div className="transaction-main">
                      <strong>{transaction.merchant}</strong>
                      <span>{categoryLabels[transaction.category]} · {dateTime.format(new Date(transaction.occurred_at))}</span>
                      <p>{transaction.anomaly.explanation}</p>
                    </div>
                    <div className="transaction-value">
                      <strong>{money.format(Number(transaction.amount))}</strong>
                      <span className={transaction.anomaly.is_anomaly ? "risk-badge" : "safe-badge"}>
                        {transaction.anomaly.is_anomaly ? "Revisar" : "Regular"} · {Math.round(transaction.anomaly.score * 100)}%
                      </span>
                      <small className={`enrichment ${transaction.enrichment_status}`}>
                        IA: {transaction.enrichment_status}
                      </small>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>

          <aside className="side-stack">
            <section className="panel create-panel">
              <p className="eyebrow">Simulador</p>
              <h2>Nova cobrança</h2>
              <form onSubmit={submitTransaction}>
                <label>
                  Valor
                  <div className="money-input"><span>R$</span><input type="number" min="0.01" step="0.01" required value={form.amount} onChange={(event) => setForm({ ...form, amount: event.target.value })} /></div>
                </label>
                <label>
                  Categoria
                  <select value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value as Transaction["category"] })}>
                    {Object.entries(categoryLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                  </select>
                </label>
                <label>
                  Estabelecimento
                  <input required maxLength={120} value={form.merchant} onChange={(event) => setForm({ ...form, merchant: event.target.value })} />
                </label>
                <button className="primary-button" disabled={mutating} type="submit">
                  {mutating ? "Processando…" : "Analisar cobrança"}
                </button>
              </form>
              <button className="demo-button" onClick={populateDemo} disabled={mutating}>
                Gerar cenário sintético
              </button>
            </section>

            <section className="panel distribution-panel">
              <p className="eyebrow">Distribuição</p>
              <h2>Por categoria</h2>
              {Object.keys(summary?.by_category ?? {}).length === 0 ? (
                <p className="muted">Sem dados suficientes.</p>
              ) : Object.entries(summary?.by_category ?? {}).map(([category, amount]) => {
                const total = Math.max(Number(summary?.total_amount ?? 0), 1);
                const width = Math.max(4, (Number(amount) / total) * 100);
                return (
                  <div className="bar-row" key={category}>
                    <div><span>{categoryLabels[category as Transaction["category"]] ?? category}</span><strong>{money.format(Number(amount))}</strong></div>
                    <div className="bar-track"><span style={{ width: `${width}%` }} /></div>
                  </div>
                );
              })}
            </section>
          </aside>
        </section>
      </div>
    </main>
  );
}
