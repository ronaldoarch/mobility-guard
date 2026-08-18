import { backendFetch, proxyResponse } from "@/lib/backend";

type RouteContext = { params: Promise<{ customerId: string }> };

export async function GET(_: Request, context: RouteContext): Promise<Response> {
  const { customerId } = await context.params;
  const safeCustomerId = encodeURIComponent(customerId);
  return proxyResponse(
    await backendFetch(`/v1/customers/${safeCustomerId}/billing-summary`),
  );
}

