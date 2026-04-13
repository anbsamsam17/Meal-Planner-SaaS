// apps/web/src/__tests__/button.test.tsx
// Tests du composant Button — smoke tests et variants
// AAA pattern : Arrange → Act → Assert
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { Button } from "@/components/ui/button";

describe("Button", () => {
  // -----------------------------------------------------------------------
  // Rendu de base
  // -----------------------------------------------------------------------
  describe("rendu", () => {
    it("rend le texte passé en enfant", () => {
      // Arrange & Act
      render(<Button>Générer mon planning</Button>);

      // Assert
      expect(screen.getByRole("button", { name: "Générer mon planning" })).toBeInTheDocument();
    });

    it("rend le variant primary par défaut", () => {
      render(<Button>Cliquez</Button>);

      const button = screen.getByRole("button");
      expect(button).toHaveClass("bg-primary-500");
    });
  });

  // -----------------------------------------------------------------------
  // Variants visuels
  // -----------------------------------------------------------------------
  describe("variants", () => {
    it("applique les classes du variant secondary", () => {
      render(<Button variant="secondary">Secondaire</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveClass("bg-secondary-100");
    });

    it("applique les classes du variant ghost", () => {
      render(<Button variant="ghost">Ghost</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveClass("bg-transparent");
    });

    it("applique les classes du variant destructive", () => {
      render(<Button variant="destructive">Supprimer</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveClass("bg-error-500");
    });
  });

  // -----------------------------------------------------------------------
  // Tailles
  // -----------------------------------------------------------------------
  describe("sizes", () => {
    it("applique la taille sm", () => {
      render(<Button size="sm">Petit</Button>);
      expect(screen.getByRole("button")).toHaveClass("h-8");
    });

    it("applique la taille xl pour les CTA landing", () => {
      render(<Button size="xl">Commencer</Button>);
      expect(screen.getByRole("button")).toHaveClass("h-14");
    });
  });

  // -----------------------------------------------------------------------
  // Accessibilité
  // -----------------------------------------------------------------------
  describe("accessibilité", () => {
    it("est désactivé quand disabled=true", () => {
      render(<Button disabled>Désactivé</Button>);
      expect(screen.getByRole("button")).toBeDisabled();
    });

    it("affiche aria-busy=true en état isLoading", () => {
      render(<Button isLoading>Chargement</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("aria-busy", "true");
      expect(button).toBeDisabled();
    });

    it("affiche le texte 'Chargement...' en état isLoading", () => {
      render(<Button isLoading>Texte original</Button>);
      // En isLoading, le texte est remplacé par "Chargement..."
      expect(screen.getByText("Chargement...")).toBeInTheDocument();
      expect(screen.queryByText("Texte original")).not.toBeInTheDocument();
    });

    it("respecte le touch target minimum (min-h-[44px])", () => {
      render(<Button>CTA</Button>);
      // La classe min-h-[44px] garantit le touch target WCAG 2.5.5
      expect(screen.getByRole("button")).toHaveClass("min-h-[44px]");
    });
  });

  // -----------------------------------------------------------------------
  // Interactions
  // -----------------------------------------------------------------------
  describe("interactions", () => {
    it("appelle onClick au clic", async () => {
      const user = userEvent.setup();
      const onClick = vi.fn();

      render(<Button onClick={onClick}>Cliquer</Button>);
      await user.click(screen.getByRole("button"));

      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it("n'appelle pas onClick si disabled", async () => {
      const user = userEvent.setup();
      const onClick = vi.fn();

      render(
        <Button disabled onClick={onClick}>
          Désactivé
        </Button>,
      );
      await user.click(screen.getByRole("button"));

      expect(onClick).not.toHaveBeenCalled();
    });

    it("n'appelle pas onClick si isLoading", async () => {
      const user = userEvent.setup();
      const onClick = vi.fn();

      render(
        <Button isLoading onClick={onClick}>
          Chargement
        </Button>,
      );
      await user.click(screen.getByRole("button"));

      expect(onClick).not.toHaveBeenCalled();
    });
  });

  // -----------------------------------------------------------------------
  // Slot (asChild pattern)
  // -----------------------------------------------------------------------
  describe("asChild", () => {
    it("rend un <a> quand asChild est combiné avec un lien", () => {
      render(
        <Button asChild>
          <a href="/dashboard">Mon dashboard</a>
        </Button>,
      );

      // L'élément rendu est un lien, pas un bouton
      expect(screen.getByRole("link", { name: "Mon dashboard" })).toBeInTheDocument();
    });
  });
});
