"""
Configuration Stripe — plans d'abonnement Presto.

Initialise le client Stripe avec la clé API (mode test : sk_test_...).
Définit les 3 plans tarifaires et leurs features associées.

Plans disponibles :
- starter : gratuit, 3 recettes/semaine, liste basique
- famille : payant, 7 dîners par Presto, PDF hebdo, profils famille, Drive
- coach   : payant, tout famille + coach nutrition + tracking macros

Utilisation dans les endpoints :
    from src.core.stripe_config import PLANS, get_stripe_price_id
"""

# Import conditionnel : stripe peut ne pas être installé en test ou en dev minimal
try:
    import stripe
except ImportError:
    stripe = None  # type: ignore[assignment]

# FIX PROD (2026-04-12) : chargement lazy de get_settings() pour éviter que l'import
# du module fasse crasher le serveur si une variable d'environnement est manquante.
# get_settings() est appelé uniquement au moment de l'accès à PLANS ou lors de
# l'initialisation Stripe, pas à l'import du module.
_stripe_initialized = False


def _init_stripe_if_needed() -> None:
    """Initialise stripe.api_key de façon lazy (appelé à la première utilisation).

    FIX PROD (2026-04-12) : évite le crash au démarrage si STRIPE_SECRET_KEY=""
    ou si get_settings() lève une exception (variable manquante). Le serveur
    démarre quoi qu'il arrive — les endpoints billing retournent 503 proprement
    via _check_stripe_configured() dans billing.py.
    """
    global _stripe_initialized
    if _stripe_initialized:
        return
    _stripe_initialized = True

    try:
        from src.core.config import get_settings
        _settings = get_settings()
        if stripe is not None and _settings.STRIPE_SECRET_KEY:
            stripe.api_key = _settings.STRIPE_SECRET_KEY  # type: ignore[union-attr]
    except Exception:
        # Si get_settings() échoue (variable manquante), on ignore silencieusement.
        # Les endpoints billing détecteront l'absence de clé via _check_stripe_configured().
        pass


def _get_plans() -> dict[str, dict]:
    """Construit le dictionnaire des plans de façon lazy.

    Séparé du module-level pour éviter que get_settings() soit appelé à l'import.
    """
    try:
        from src.core.config import get_settings
        _settings = get_settings()
        stripe_price_famille = _settings.STRIPE_PRICE_FAMILLE
        stripe_price_coach = _settings.STRIPE_PRICE_COACH
    except Exception:
        stripe_price_famille = ""
        stripe_price_coach = ""

    return {
        "starter": {
            "price_id": None,  # Gratuit — pas de Stripe Price
            "display_name": "Starter",
            "price_monthly_eur": 0,
            "features": [
                "3 recettes/semaine",
                "Liste de courses basique",
                "Profil famille unique",
            ],
            "pdf_access": False,
            "coach_access": False,
        },
        "famille": {
            "price_id": stripe_price_famille,
            "display_name": "Famille",
            "price_monthly_eur": 9,
            "features": [
                "7 dîners par Presto par semaine",
                "Livre de recettes PDF hebdomadaire",
                "Profils famille (jusqu'à 6 membres)",
                "Liste de courses Drive",
                "Mode frigo (utiliser les restes)",
                "Filtres avancés (budget, temps, régime)",
            ],
            "pdf_access": True,
            "coach_access": False,
        },
        "coach": {
            "price_id": stripe_price_coach,
            "display_name": "Coach Nutrition",
            "price_monthly_eur": 19,
            "features": [
                "Tout le plan Famille",
                "Coach nutrition Presto personnalisé",
                "Tracking macronutriments",
                "Objectifs caloriques personnalisés",
                "Rapport nutritionnel mensuel",
            ],
            "pdf_access": True,
            "coach_access": True,
        },
    }


# ---- Plans tarifaires ----
# Chargé à l'import pour la rétrocompatibilité avec les imports existants.
# FIX PROD (2026-04-12) : _get_plans() encapsule get_settings() dans un try/except
# pour que l'import du module ne crashe pas si une variable est absente.
PLANS: dict[str, dict] = _get_plans()

# Initialisation Stripe lazy — appelée maintenant pour pré-configurer la clé API
# si disponible, sans bloquer le démarrage du serveur si elle est absente.
_init_stripe_if_needed()

# Ordre des plans pour les upgrades/downgrades (index = niveau)
PLAN_ORDER: list[str] = ["starter", "famille", "coach"]


def get_stripe_price_id(plan_name: str) -> str | None:
    """
    Retourne le Stripe Price ID d'un plan.

    Args:
        plan_name: Nom du plan ('starter', 'famille', 'coach').

    Returns:
        Price ID Stripe, ou None si plan gratuit ou inconnu.

    Raises:
        KeyError: si le plan_name est invalide.
    """
    plan = PLANS[plan_name]  # KeyError si plan inconnu — comportement voulu
    return plan.get("price_id")


def get_plan_level(plan_name: str) -> int:
    """
    Retourne le niveau numérique d'un plan (0=starter, 1=famille, 2=coach).

    Utilisé pour les vérifications require_plan().

    Args:
        plan_name: Nom du plan.

    Returns:
        Entier 0-2, ou -1 si plan inconnu.
    """
    try:
        return PLAN_ORDER.index(plan_name)
    except ValueError:
        return -1
