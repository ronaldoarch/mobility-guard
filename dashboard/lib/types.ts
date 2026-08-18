export type AnomalyReason = {
  kind: string;
  weight: number;
  message: string;
};

export type Transaction = {
  id: string;
  external_id: string;
  customer_id: string;
  amount: string;
  occurred_at: string;
  category: "toll" | "parking" | "fuel" | "drive_thru";
  merchant: string;
  enrichment_status: "skipped" | "pending" | "completed" | "failed";
  anomaly: {
    is_anomaly: boolean;
    score: number;
    threshold: number;
    reasons: AnomalyReason[];
    explanation: string;
  };
};

export type BillingSummary = {
  customer_id: string;
  transaction_count: number;
  anomaly_count: number;
  total_amount: string;
  by_category: Record<string, string>;
};

