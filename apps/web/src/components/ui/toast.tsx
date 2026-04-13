// apps/web/src/components/ui/toast.tsx
// Wrapper Sonner pour les notifications toast
// Référence : phase-0/design-system/04-components-catalog.md #10 Toast
// Sonner est configuré dans root-providers.tsx
// Ce fichier expose des helpers typed pour déclencher des toasts depuis n'importe où
import { toast as sonnerToast } from "sonner";

// Helpers typés — évite d'appeler sonner directement dans les composants
export const toast = {
  // Succès — ex: "Recette ajoutée au planning"
  success: (message: string, description?: string) =>
    sonnerToast.success(message, { description }),

  // Erreur — ex: "Erreur lors de la génération du planning"
  error: (message: string, description?: string) =>
    sonnerToast.error(message, { description }),

  // Avertissement — ex: "Recette modifiée : liste de courses mise à jour"
  warning: (message: string, description?: string) =>
    sonnerToast.warning(message, { description }),

  // Info — ex: "Votre PDF est prêt"
  info: (message: string, description?: string) =>
    sonnerToast.info(message, { description }),

  // Toast avec action — ex: "Ajouté au planning (annuler)"
  withAction: (
    message: string,
    actionLabel: string,
    onAction: () => void,
    description?: string,
  ) =>
    sonnerToast(message, {
      description,
      action: {
        label: actionLabel,
        onClick: onAction,
      },
      duration: 6000, // Plus long pour les toasts avec action
    }),

  // Toast de chargement — retourne l'ID pour le résoudre ensuite
  loading: (message: string) => sonnerToast.loading(message),

  // Résoudre un toast de chargement
  dismiss: (id: string | number) => sonnerToast.dismiss(id),

  // PDF hebdomadaire reçu — durée plus longue (6s)
  pdfReady: () =>
    sonnerToast.success("Votre livre de la semaine est prêt !", {
      description: "Ouvrez-le pour voir vos recettes de la semaine.",
      duration: 6000,
      action: {
        label: "Voir mon livre",
        onClick: () => {
          // TODO Phase 1 : rediriger vers la page du PDF
        },
      },
    }),
};
