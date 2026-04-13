// apps/web/src/app/(auth)/signup/page.tsx
// Page inscription — email + password (primaire) + magic link (secondaire)
// BUG 1 FIX (2026-04-12) : ajout champ mot de passe + supabase.auth.signUp()
"use client";

import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Loader2, Mail, Eye, EyeOff } from "lucide-react";
import { createBrowserClient } from "@/lib/supabase/client";

function validateEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}

function validatePassword(password: string): string | null {
  if (password.length < 8) return "Le mot de passe doit contenir au moins 8 caractères.";
  if (!/[A-Z]/.test(password)) return "Ajoutez au moins une majuscule.";
  if (!/[0-9]/.test(password)) return "Ajoutez au moins un chiffre.";
  return null;
}

type Mode = "password" | "magic-link";

export default function SignupPage() {
  const [mode, setMode] = useState<Mode>("password");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSent, setIsSent] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  async function handlePasswordSignup(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setEmailError(null);
    setPasswordError(null);

    if (!validateEmail(email)) {
      setEmailError("Veuillez saisir une adresse email valide.");
      return;
    }
    const pwdError = validatePassword(password);
    if (pwdError) {
      setPasswordError(pwdError);
      return;
    }

    setIsLoading(true);

    try {
      const supabase = createBrowserClient();

      const { error } = await supabase.auth.signUp({
        email: email.trim().toLowerCase(),
        password,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback?next=/onboarding/step-1`,
        },
      });

      if (error) {
        if (error.status === 429 || error.message.includes("rate")) {
          toast.error("Trop de tentatives", {
            description: "Veuillez patienter quelques minutes avant de réessayer.",
          });
          return;
        }
        if (error.message.toLowerCase().includes("already registered") || error.message.toLowerCase().includes("user already")) {
          toast.info("Compte existant", {
            description: "Cet email est déjà inscrit. Connectez-vous.",
            action: { label: "Se connecter", onClick: () => window.location.assign("/login") },
          });
          return;
        }
        toast.error("Erreur lors de l'inscription", {
          description: error.message,
        });
        return;
      }

      setIsSent(true);
      toast.success("Compte créé ! Vérifiez votre boîte mail", {
        description: `Un email de confirmation a été envoyé à ${email.trim()}.`,
        duration: 8000,
      });
    } catch {
      toast.error("Erreur inattendue", {
        description: "Une erreur est survenue. Veuillez réessayer.",
      });
    } finally {
      setIsLoading(false);
    }
  }

  async function handleMagicLink(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setEmailError(null);

    if (!validateEmail(email)) {
      setEmailError("Veuillez saisir une adresse email valide.");
      return;
    }

    setIsLoading(true);

    try {
      const supabase = createBrowserClient();

      const { error } = await supabase.auth.signInWithOtp({
        email: email.trim().toLowerCase(),
        options: {
          shouldCreateUser: true,
          emailRedirectTo: `${window.location.origin}/auth/callback?next=/onboarding/step-1`,
        },
      });

      if (error) {
        if (error.status === 429 || error.message.includes("rate")) {
          toast.error("Trop de tentatives", {
            description: "Veuillez patienter quelques minutes avant de réessayer.",
          });
          return;
        }
        toast.error("Erreur lors de l'envoi", {
          description: "Impossible d'envoyer le lien. Réessayez dans quelques instants.",
        });
        return;
      }

      setIsSent(true);
      toast.success("Lien envoyé ! Vérifiez votre boîte mail", {
        description: `Un lien de connexion a été envoyé à ${email.trim()}.`,
        duration: 8000,
      });
    } catch {
      toast.error("Erreur inattendue", {
        description: "Une erreur est survenue. Veuillez réessayer.",
      });
    } finally {
      setIsLoading(false);
    }
  }

  if (isSent) {
    return (
      <div className="text-center">
        <div
          className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary-50"
          aria-hidden="true"
        >
          <Mail className="h-8 w-8 text-primary-500" />
        </div>
        <h1 className="font-serif mb-2 text-2xl font-bold text-neutral-900">
          {mode === "password" ? "Confirmez votre email" : "Vérifiez votre boîte mail"}
        </h1>
        <p className="mb-6 text-sm text-neutral-500">
          {mode === "password"
            ? "Un email de confirmation a été envoyé à "
            : "Un lien de connexion a été envoyé à "}
          <strong className="font-medium text-neutral-800">{email.trim()}</strong>.{" "}
          {mode === "password"
            ? "Cliquez sur le lien pour activer votre compte."
            : "Cliquez dessus pour créer votre compte."}
        </p>
        <p className="text-xs text-neutral-400">
          Vous n&apos;avez pas reçu l&apos;email ?{" "}
          <button
            type="button"
            onClick={() => setIsSent(false)}
            className="text-primary-600 underline hover:text-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
          >
            Renvoyer
          </button>
        </p>
      </div>
    );
  }

  return (
    <>
      <h1 className="font-serif mb-2 text-2xl font-bold text-neutral-900">
        Créez votre compte en 30 secondes
      </h1>
      <p className="mb-6 text-sm text-neutral-500">
        {mode === "password"
          ? "Choisissez un mot de passe sécurisé pour votre compte."
          : "Nous vous enverrons un lien magique. Aucun mot de passe requis."}
      </p>

      {mode === "password" ? (
        <form onSubmit={handlePasswordSignup} noValidate>
          {/* Champ email */}
          <div className="mb-4">
            <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-neutral-700">
              Adresse email
            </label>
            <input
              id="email"
              type="email"
              name="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (emailError) setEmailError(null);
              }}
              placeholder="sophie@exemple.fr"
              autoComplete="email"
              required
              aria-invalid={emailError ? "true" : undefined}
              aria-describedby={emailError ? "email-error" : undefined}
              className={`block h-11 w-full rounded-xl border px-4 text-sm transition-colors duration-fast
                focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-0
                disabled:cursor-not-allowed disabled:opacity-50
                ${
                  emailError
                    ? "border-red-400 bg-red-50 text-neutral-900 placeholder:text-neutral-400"
                    : "border-neutral-300 bg-neutral-50 text-neutral-900 placeholder:text-neutral-400 focus:border-primary-500"
                }`}
            />
            {emailError && (
              <p
                id="email-error"
                role="alert"
                className="mt-1.5 flex items-center gap-1 text-xs text-red-600"
              >
                <span aria-hidden="true">⚠</span>
                {emailError}
              </p>
            )}
          </div>

          {/* Champ mot de passe */}
          <div className="mb-4">
            <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-neutral-700">
              Mot de passe
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                name="password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (passwordError) setPasswordError(null);
                }}
                placeholder="8 caractères min., 1 majuscule, 1 chiffre"
                autoComplete="new-password"
                required
                aria-invalid={passwordError ? "true" : undefined}
                aria-describedby={passwordError ? "password-error" : "password-hint"}
                className={`block h-11 w-full rounded-xl border px-4 pr-11 text-sm transition-colors duration-fast
                  focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-0
                  disabled:cursor-not-allowed disabled:opacity-50
                  ${
                    passwordError
                      ? "border-red-400 bg-red-50 text-neutral-900 placeholder:text-neutral-400"
                      : "border-neutral-300 bg-neutral-50 text-neutral-900 placeholder:text-neutral-400 focus:border-primary-500"
                  }`}
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
                aria-label={showPassword ? "Masquer le mot de passe" : "Afficher le mot de passe"}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <Eye className="h-4 w-4" aria-hidden="true" />
                )}
              </button>
            </div>
            {passwordError ? (
              <p
                id="password-error"
                role="alert"
                className="mt-1.5 flex items-center gap-1 text-xs text-red-600"
              >
                <span aria-hidden="true">⚠</span>
                {passwordError}
              </p>
            ) : (
              <p id="password-hint" className="mt-1.5 text-xs text-neutral-400">
                8 caractères minimum, 1 majuscule, 1 chiffre.
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={isLoading || !email.trim() || !password}
            aria-busy={isLoading}
            className="inline-flex min-h-[48px] w-full items-center justify-center gap-2 rounded-xl
              bg-primary-500 px-6 py-3 text-base font-semibold text-white
              transition-all duration-base
              hover:bg-primary-600 focus-visible:outline-none focus-visible:ring-2
              focus-visible:ring-primary-500 focus-visible:ring-offset-2
              active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                Création en cours…
              </>
            ) : (
              "Créer mon compte"
            )}
          </button>

          {/* Lien vers magic link */}
          <div className="mt-4 text-center">
            <button
              type="button"
              onClick={() => setMode("magic-link")}
              className="text-sm text-neutral-500 underline hover:text-neutral-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
            >
              Ou recevoir un lien par email
            </button>
          </div>
        </form>
      ) : (
        <form onSubmit={handleMagicLink} noValidate>
          <div className="mb-4">
            <label htmlFor="email-ml" className="mb-1.5 block text-sm font-medium text-neutral-700">
              Adresse email
            </label>
            <input
              id="email-ml"
              type="email"
              name="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (emailError) setEmailError(null);
              }}
              placeholder="sophie@exemple.fr"
              autoComplete="email"
              required
              aria-invalid={emailError ? "true" : undefined}
              aria-describedby={emailError ? "email-ml-error" : undefined}
              className={`block h-11 w-full rounded-xl border px-4 text-sm transition-colors duration-fast
                focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-0
                disabled:cursor-not-allowed disabled:opacity-50
                ${
                  emailError
                    ? "border-red-400 bg-red-50 text-neutral-900 placeholder:text-neutral-400"
                    : "border-neutral-300 bg-neutral-50 text-neutral-900 placeholder:text-neutral-400 focus:border-primary-500"
                }`}
            />
            {emailError && (
              <p
                id="email-ml-error"
                role="alert"
                className="mt-1.5 flex items-center gap-1 text-xs text-red-600"
              >
                <span aria-hidden="true">⚠</span>
                {emailError}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={isLoading || !email.trim()}
            aria-busy={isLoading}
            className="inline-flex min-h-[48px] w-full items-center justify-center gap-2 rounded-xl
              bg-primary-500 px-6 py-3 text-base font-semibold text-white
              transition-all duration-base
              hover:bg-primary-600 focus-visible:outline-none focus-visible:ring-2
              focus-visible:ring-primary-500 focus-visible:ring-offset-2
              active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                Envoi en cours…
              </>
            ) : (
              "Recevoir le lien de connexion"
            )}
          </button>

          <div className="mt-4 text-center">
            <button
              type="button"
              onClick={() => setMode("password")}
              className="text-sm text-neutral-500 underline hover:text-neutral-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
            >
              Créer un compte avec un mot de passe
            </button>
          </div>
        </form>
      )}

      <div className="mt-6 text-center text-sm text-neutral-500">
        Déjà un compte ?{" "}
        <Link
          href="/login"
          className="font-medium text-primary-600 hover:text-primary-700
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
        >
          Se connecter
        </Link>
      </div>
    </>
  );
}
