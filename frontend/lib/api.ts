const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function parseErrorMessage(resp: Response): Promise<string> {
  try {
    const body = await resp.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((item: { msg?: string }) => item.msg)
        .filter(Boolean)
        .join("; ");
    }
  } catch {
    // Response body is not JSON.
  }
  return `API error ${resp.status}`;
}

export async function apiFetch<T>(
  path: string,
  token: string,
  options: RequestInit = {},
): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...(options.headers || {}),
      },
    });
  } catch {
    throw new Error(
      `Cannot reach API at ${API_BASE}. Is the backend running?`,
    );
  }

  if (!resp.ok) {
    throw new Error(await parseErrorMessage(resp));
  }

  return resp.json();
}

export async function login(username: string, password: string) {
  let resp: Response;
  try {
    resp = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
  } catch {
    throw new Error(
      `Cannot reach API at ${API_BASE}. Is the backend running?`,
    );
  }
  if (resp.status === 401) {
    throw new Error(
      "Invalid username or password. Use ADMIN_USERNAME and ADMIN_PASSWORD from .env.",
    );
  }
  if (!resp.ok) {
    throw new Error(`Login failed (${resp.status})`);
  }
  return resp.json();
}
