"""
Agent RETENTION_LOOP — Phase 2 Presto.

Vérifie l'engagement des foyers actifs et identifie les utilisateurs at_risk.
Phase 2 : logging uniquement. Phase 3 : envoi email Resend + push notification.

Flags d'engagement :
- at_risk      : dernière activité > 5 jours
- inactive     : aucun plan cette semaine
- disengaged   : 3 semaines sans feedback
"""
