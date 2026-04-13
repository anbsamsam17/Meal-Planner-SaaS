"""
Agent WEEKLY_PLANNER — planificateur hebdomadaire intelligent.

Ce package génère les plans de repas hebdomadaires personnalisés
pour chaque foyer en combinant :
- Les contraintes (allergies, régimes, temps, budget)
- Les préférences de goût (vecteurs member_taste_vectors)
- L'historique (anti-répétition 3 semaines)
- Les ingrédients du frigo (mode anti-gaspi)
"""

from src.agents.weekly_planner.agent import WeeklyPlannerAgent, WeeklyPlanResult

__all__ = ["WeeklyPlanResult", "WeeklyPlannerAgent"]
