import { backendFetch, proxyResponse } from "@/lib/backend";

export async function GET(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const customerId = url.searchParams.get("customer_id") ?? "demo-customer";
  const limit = url.searchParams.get("limit") ?? "100";
  const query = new URLSearchParams({ customer_id: customerId, limit });
  return proxyResponse(await backendFetch(`/v1/transactions?${query}`));
}

export async function POST(request: Request): Promise<Response> {
  const body: unknown = await request.json();
  return proxyResponse(
    await backendFetch("/v1/transactions", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  );
}

