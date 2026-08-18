const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export async function backendFetch(path: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (init?.body) headers.set("Content-Type", "application/json");
  if (process.env.API_KEY) headers.set("X-API-Key", process.env.API_KEY);

  return fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
}

export async function proxyResponse(response: Response): Promise<Response> {
  const body = await response.text();
  return new Response(body, {
    status: response.status,
    headers: { "Content-Type": response.headers.get("Content-Type") ?? "application/json" },
  });
}

