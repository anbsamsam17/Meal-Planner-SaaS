// apps/web/src/lib/api/client.ts
// Client HTTP vers le backend FastAPI
// Auth via JWT Supabase, gestion erreurs typées, rate limit FR user-friendly
//
// FIX 2026-04-12 : getAuthToken() utilise supabase.auth.getSession() au lieu
// de parser localStorage manuellement (plus robuste, compatible avec les futures
// versions du SDK Supabase qui peuvent changer le format de la clé localStorage)
import { z } from "zod";
import { toast } from "@/components/ui/toast";
import { createBrowserClient } from "@/lib/supabase/client";
import type { ApiError } from "./types";

// BUG 6 FIX : fallback Railway hardcodé si NEXT_PUBLIC_API_URL non défini
// Cela couvre le cas où la variable n'est pas configurée sur Vercel
const RAILWAY_API_URL = "https://meal-planner-saas-production.up.railway.app";

function getApiBaseUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!envUrl || envUrl.includes("localhost") || envUrl.includes("127.0.0.1")) {
    return RAILWAY_API_URL;
  }
  return envUrl;
}

const API_BASE_URL = typeof window !== "undefined" ? getApiBaseUrl() : RAILWAY_API_URL;

// Schéma de validation pour les erreurs API (format FastAPI)
const apiErrorSchema = z.object({
  status_code: z.number(),
  detail: z.string(),
  correlation_id: z.string().optional(),
});

// Classe d'erreur typée pour les erreurs API
export class ApiRequestError extends Error {
  constructor(
    public readonly statusCode: number,
    public readonly detail: string,
    public readonly correlationId?: string,
  ) {
    super(`Erreur API ${statusCode}: ${detail}`);
    this.name = "ApiRequestError";
  }
}

// Récupère le token JWT Supabase via le SDK (client-side uniquement)
// Utilise supabase.auth.getSession() — plus fiable que de parser localStorage manuellement
// NE PAS utiliser côté serveur — utiliser createServerClient à la place
async function getAuthToken(): Promise<string | null> {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const supabase = createBrowserClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();
    return session?.access_token ?? null;
  } catch {
    // Fallback silencieux — l'appel API suivra sans header Authorization
    return null;
  }
}

// Fonction de fetch générique avec auth, retry et gestion d'erreurs
// BUG 6 FIX : timeout 15s sur tous les appels API (génération IA peut être lente)
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = await getAuthToken();

  // Timeout 15s — suffisant pour la génération du plan IA (Railway cold start inclus)
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15_000);

  const response = await fetch(url, {
    ...options,
    signal: options.signal ?? controller.signal,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      // BUG 6 FIX : token JWT Supabase envoyé dans Authorization: Bearer
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  }).finally(() => clearTimeout(timeoutId));

  // Gestion du rate limiting (429) — message FR user-friendly
  if (response.status === 429) {
    const retryAfter = response.headers.get("Retry-After");
    const waitSeconds = retryAfter ? parseInt(retryAfter, 10) : 60;
    toast.warning(
      "Trop de requêtes",
      `Veuillez patienter ${waitSeconds} secondes avant de réessayer.`,
    );
    throw new ApiRequestError(429, "Rate limit atteint", undefined);
  }

  // Gestion des erreurs HTTP
  if (!response.ok) {
    let errorData: ApiError | null = null;

    try {
      const json = await response.json();
      const parsed = apiErrorSchema.safeParse(json);
      if (parsed.success) {
        errorData = parsed.data as ApiError;
      }
    } catch {
      // Réponse non-JSON
    }

    // Pas de toast ici — les composants gèrent leurs propres erreurs
    // Évite les toasts en boucle sur les appels passifs (chargement page)

    throw new ApiRequestError(
      response.status,
      errorData?.detail ?? response.statusText,
      errorData?.correlation_id,
    );
  }

  // Réponse 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

// Client HTTP exposé — méthodes typées
export const apiClient = {
  get: <T>(endpoint: string, options?: RequestInit) =>
    apiRequest<T>(endpoint, { ...options, method: "GET" }),

  post: <T>(endpoint: string, body: unknown, options?: RequestInit) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: "POST",
      body: JSON.stringify(body),
    }),

  put: <T>(endpoint: string, body: unknown, options?: RequestInit) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: "PUT",
      body: JSON.stringify(body),
    }),

  patch: <T>(endpoint: string, body: unknown, options?: RequestInit) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  delete: <T>(endpoint: string, options?: RequestInit) =>
    apiRequest<T>(endpoint, { ...options, method: "DELETE" }),
};
