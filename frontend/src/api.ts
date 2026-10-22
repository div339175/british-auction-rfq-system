import { CreateQuotePayload, CreateRFQPayload, RFQDetail, RFQSummary } from "./types";

const BASE_URL = "/api/v1";

export async function fetchRFQs(status?: string): Promise<RFQSummary[]> {
  const url = status ? `${BASE_URL}/rfqs?status=${encodeURIComponent(status)}` : `${BASE_URL}/rfqs`;
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to fetch RFQs" }));
    throw new Error(err.detail || "Failed to fetch RFQs");
  }
  return res.json();
}

export async function fetchRFQDetails(rfqId: string): Promise<RFQDetail> {
  const res = await fetch(`${BASE_URL}/rfqs/${rfqId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to fetch RFQ details" }));
    throw new Error(err.detail || "Failed to fetch RFQ details");
  }
  return res.json();
}

export async function createRFQ(payload: CreateRFQPayload): Promise<RFQDetail> {
  const res = await fetch(`${BASE_URL}/rfqs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to create RFQ" }));
    throw new Error(err.detail || "Failed to create RFQ");
  }
  return res.json();
}

export async function submitQuote(
  rfqId: string,
  payload: CreateQuotePayload
): Promise<{ quote: any; extension_occurred: boolean; new_close_time: string; message: string }> {
  const res = await fetch(`${BASE_URL}/rfqs/${rfqId}/quotes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to submit quote" }));
    throw new Error(err.detail || "Failed to submit quote");
  }
  return res.json();
}
