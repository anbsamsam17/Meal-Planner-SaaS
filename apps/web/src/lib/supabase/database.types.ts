// apps/web/src/lib/supabase/database.types.ts
// Types de la base de données Supabase — générés à partir du schéma PostgreSQL
// À remplacer par la génération automatique via : pnpm supabase gen types typescript
// Pour l'instant : types minimaux pour le scaffold Phase 1

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

// Placeholder — sera complété par le database-administrator
// Commande de génération : supabase gen types typescript --local > src/lib/supabase/database.types.ts
export interface Database {
  public: {
    Tables: {
      profiles: {
        Row: {
          id: string;
          created_at: string;
          updated_at: string;
          email: string;
          full_name: string | null;
          avatar_url: string | null;
          subscription_tier: "starter" | "family" | "coach";
          subscription_status: "active" | "trialing" | "canceled" | "past_due";
          stripe_customer_id: string | null;
        };
        Insert: {
          id: string;
          email: string;
          full_name?: string | null;
          avatar_url?: string | null;
          subscription_tier?: "starter" | "family" | "coach";
          subscription_status?: "active" | "trialing" | "canceled" | "past_due";
          stripe_customer_id?: string | null;
        };
        Update: {
          full_name?: string | null;
          avatar_url?: string | null;
          subscription_tier?: "starter" | "family" | "coach";
          subscription_status?: "active" | "trialing" | "canceled" | "past_due";
          stripe_customer_id?: string | null;
        };
      };
      households: {
        Row: {
          id: string;
          created_at: string;
          owner_id: string;
          name: string;
          drive_provider: string | null;
          cooking_time_preference: "under-20" | "20-40" | "over-40";
        };
        Insert: {
          owner_id: string;
          name: string;
          drive_provider?: string | null;
          cooking_time_preference?: "under-20" | "20-40" | "over-40";
        };
        Update: {
          name?: string;
          drive_provider?: string | null;
          cooking_time_preference?: "under-20" | "20-40" | "over-40";
        };
      };
      household_members: {
        Row: {
          id: string;
          household_id: string;
          name: string;
          age_range: "adult" | "under-3" | "3-6" | "7-12" | "13-plus";
          dietary_restrictions: string[];
        };
        Insert: {
          household_id: string;
          name: string;
          age_range: "adult" | "under-3" | "3-6" | "7-12" | "13-plus";
          dietary_restrictions?: string[];
        };
        Update: {
          name?: string;
          age_range?: "adult" | "under-3" | "3-6" | "7-12" | "13-plus";
          dietary_restrictions?: string[];
        };
      };
      weekly_plans: {
        Row: {
          id: string;
          created_at: string;
          household_id: string;
          week_start_date: string; // ISO date string
          recipes: Json; // {monday: recipe_id | null, ...}
          status: "draft" | "confirmed" | "completed";
        };
        Insert: {
          household_id: string;
          week_start_date: string;
          recipes?: Json;
          status?: "draft" | "confirmed" | "completed";
        };
        Update: {
          recipes?: Json;
          status?: "draft" | "confirmed" | "completed";
        };
      };
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
    Enums: {
      subscription_tier: "starter" | "family" | "coach";
      subscription_status: "active" | "trialing" | "canceled" | "past_due";
      cooking_time: "under-20" | "20-40" | "over-40";
    };
  };
}
