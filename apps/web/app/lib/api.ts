const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: string,
  ) {
    super(`HTTP ${status}`);
    this.name = "ApiError";
  }
}

// ---- Types (mirror apps/api/app/schemas/recommendation.py) ----------------

export interface RecipeRecommendation {
  id?: number | null;
  name: string;
  description?: string | null;
  cuisine?: string | null;
  prep_time?: number | null;
  cook_time?: number | null;
  total_time?: number | null;
  servings?: number | null;
  difficulty?: string | null;
  ingredients?: string[] | null;
  instructions?: string[] | null;
  nutrition?: Record<string, unknown> | null;
  tags?: string[] | null;
}

export interface MenuDay {
  day: number;
  date?: string | null;
  meals: Record<string, RecipeRecommendation>;
  notes?: string | null;
}

export interface MenuPlan {
  days: MenuDay[];
  total_days: number;
  servings: number;
}

export interface GroceryItem {
  ingredient: string;
  quantity?: number | null;
  unit?: string | null;
  category?: string | null;
  estimated_cost?: number | null;
  already_available: boolean;
}

export interface GroceryList {
  items: GroceryItem[];
  categories: Record<string, GroceryItem[]>;
  total_items: number;
  estimated_total_cost?: number | null;
}

export interface RecommendationResponse {
  recommendations: RecipeRecommendation[];
  menu_plan?: MenuPlan | null;
  grocery_list?: GroceryList | null;
  nutrition_notes?: string | null;
  warnings: string[];
  trace_id?: string | null;
}

export interface RecommendationRequest {
  message: string;
  available_ingredients?: string[] | null;
  dietary_restrictions?: string[] | null;
  cuisine_preferences?: string[] | null;
  servings?: number | null;
  days?: number | null;
}

export interface CreateApiKeyRequest {
  owner_id: string;
  name: string;
  tracing_consent?: boolean;
  expires_in_days?: number | null;
}

export interface CreateApiKeyResponse {
  key: string;
  owner_id: string;
  name: string;
  tracing_consent: boolean;
  expires_at: string | null;
}

// ---- Helpers ---------------------------------------------------------------

function authHeaders(apiKey: string | null): Record<string, string> {
  return apiKey ? { "X-API-Key": apiKey } : {};
}

// ---- API calls -------------------------------------------------------------

export async function fetchRecommendations(
  req: RecommendationRequest,
  apiKey: string | null = null,
): Promise<RecommendationResponse> {
  const res = await fetch(`${API_BASE}/api/v1/recommendations`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(apiKey) },
    body: JSON.stringify(req),
  });

  const text = await res.text();
  if (!res.ok) throw new ApiError(res.status, text);
  return JSON.parse(text) as RecommendationResponse;
}

export async function createApiKey(
  req: CreateApiKeyRequest,
): Promise<CreateApiKeyResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/api-keys`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  const text = await res.text();
  if (!res.ok) throw new ApiError(res.status, text);
  return JSON.parse(text) as CreateApiKeyResponse;
}
