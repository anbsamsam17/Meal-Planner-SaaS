// apps/web/src/lib/utils.ts
// Utilitaires partagés
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

// Fusion intelligente de classes Tailwind — évite les conflits entre variantes
// Usage : cn("px-4 py-2", isActive && "bg-primary-500", className)
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

// Formater une durée en minutes pour l'affichage
// Exemple : 75 → "1h 15min"
export function formatDuration(minutes: number): string {
  if (minutes < 60) {
    return `${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  if (remainingMinutes === 0) {
    return `${hours}h`;
  }
  return `${hours}h ${remainingMinutes}min`;
}

// Formater un prix en euros (format FR)
// Exemple : 999 → "9,99 €"
export function formatPrice(cents: number): string {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
  }).format(cents / 100);
}

// Obtenir les initiales d'un nom pour les avatars
// Exemple : "Sophie Durand" → "SD"
export function getInitials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

// Vérifier si une date correspond à la semaine courante
export function isCurrentWeek(date: Date): boolean {
  const today = new Date();
  const startOfWeek = new Date(today);
  startOfWeek.setDate(today.getDate() - today.getDay() + 1); // Lundi
  startOfWeek.setHours(0, 0, 0, 0);

  const endOfWeek = new Date(startOfWeek);
  endOfWeek.setDate(startOfWeek.getDate() + 6); // Dimanche
  endOfWeek.setHours(23, 59, 59, 999);

  return date >= startOfWeek && date <= endOfWeek;
}
