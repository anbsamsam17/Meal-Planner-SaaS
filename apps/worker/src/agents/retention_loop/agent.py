"""
RetentionLoopAgent — analyse d'engagement des foyers.

Logique v0 (Phase 2) :
1. Récupère tous les foyers actifs (au moins un membre, plan dans les 30 derniers jours)
2. Pour chaque foyer, calcule les flags d'engagement
3. Log les events (Phase 3 : envoi email/push)
4. Retourne un résumé {total_checked, at_risk, inactive, disengaged}

Flags :
- at_risk    : dernière activité (feedback/validation) > 5 jours
- inactive   : aucun plan créé ou validé la semaine courante
- disengaged : aucun feedback dans les 3 dernières semaines

Phase 3 : les flags déclencheront l'envoi d'emails via Resend
et de push notifications via Web Push API.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from loguru import logger


# Seuils d'engagement
AT_RISK_DAYS = 5          # Jours sans activité → at_risk
INACTIVE_WEEKS = 1        # Semaines sans plan → inactive
DISENGAGED_WEEKS = 3      # Semaines sans feedback → disengaged


class RetentionLoopAgent:
    """
    Analyseur d'engagement des foyers.

    Conçu pour être exécuté toutes les 4 heures via Celery beat.
    En v0 : lecture seule + logging. Aucun email/push envoyé.
    """

    async def run(self, db_session: Any) -> dict[str, int]:
        """
        Point d'entrée principal. Analyse tous les foyers actifs.

        Args:
            db_session: Session SQLAlchemy async.

        Returns:
            dict : {total_checked, at_risk, inactive, disengaged}
        """
        from sqlalchemy import text

        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        at_risk_cutoff = today - timedelta(days=AT_RISK_DAYS)
        disengaged_cutoff = today - timedelta(weeks=DISENGAGED_WEEKS)

        logger.info(
            "retention_loop_start",
            date=str(today),
            at_risk_cutoff=str(at_risk_cutoff),
            disengaged_cutoff=str(disengaged_cutoff),
        )

        # Récupère tous les foyers actifs (avec au moins un plan dans les 30 derniers jours)
        households_result = await db_session.execute(
            text(
                """
                SELECT DISTINCT h.id::text, h.name
                FROM households h
                JOIN weekly_plans wp ON wp.household_id = h.id
                WHERE wp.created_at >= NOW() - INTERVAL '30 days'
                ORDER BY h.id
                """
            )
        )
        households = households_result.fetchall()

        stats = {
            "total_checked": len(households),
            "at_risk": 0,
            "inactive": 0,
            "disengaged": 0,
        }

        for household_row in households:
            household_id = household_row[0]
            household_name = household_row[1]

            flags = await self._compute_flags(
                db_session=db_session,
                household_id=household_id,
                week_start=week_start,
                at_risk_cutoff=at_risk_cutoff,
                disengaged_cutoff=disengaged_cutoff,
            )

            if flags["at_risk"]:
                stats["at_risk"] += 1
                self._log_at_risk(household_id, household_name, flags)

            if flags["inactive"]:
                stats["inactive"] += 1
                self._log_inactive(household_id, household_name, flags)

            if flags["disengaged"]:
                stats["disengaged"] += 1
                self._log_disengaged(household_id, household_name, flags)

        logger.info(
            "retention_loop_done",
            **stats,
        )

        return stats

    async def _compute_flags(
        self,
        db_session: Any,
        household_id: str,
        week_start: date,
        at_risk_cutoff: date,
        disengaged_cutoff: date,
    ) -> dict[str, Any]:
        """
        Calcule les flags d'engagement pour un foyer.

        Flags calculés :
        - at_risk    : dernière activité < at_risk_cutoff
        - inactive   : aucun plan cette semaine (week_start)
        - disengaged : aucun feedback depuis disengaged_cutoff

        Args:
            db_session: Session SQLAlchemy async.
            household_id: UUID str du foyer.
            week_start: Lundi de la semaine courante.
            at_risk_cutoff: Date seuil pour at_risk.
            disengaged_cutoff: Date seuil pour disengaged.

        Returns:
            dict avec les flags booléens et les métadonnées.
        """
        from sqlalchemy import text

        # Dernière activité : validation de plan OU feedback
        last_activity_result = await db_session.execute(
            text(
                """
                SELECT MAX(activity_date)::date AS last_activity
                FROM (
                    SELECT validated_at AS activity_date
                    FROM weekly_plans
                    WHERE household_id = :hid AND validated_at IS NOT NULL
                    UNION ALL
                    SELECT created_at AS activity_date
                    FROM recipe_feedbacks rf
                    JOIN household_members hm ON hm.id = rf.member_id
                    WHERE hm.household_id = :hid
                ) sub
                """
            ),
            {"hid": household_id},
        )
        last_activity_row = last_activity_result.fetchone()
        last_activity: date | None = last_activity_row[0] if last_activity_row else None

        # Flag at_risk : pas d'activité depuis AT_RISK_DAYS jours
        at_risk = (last_activity is None) or (last_activity < at_risk_cutoff)

        # Aucun plan cette semaine
        plan_this_week_result = await db_session.execute(
            text(
                """
                SELECT COUNT(*) FROM weekly_plans
                WHERE household_id = :hid
                  AND week_start = :week_start
                """
            ),
            {"hid": household_id, "week_start": week_start.isoformat()},
        )
        plan_count = plan_this_week_result.scalar() or 0
        inactive = plan_count == 0

        # Aucun feedback depuis 3 semaines
        last_feedback_result = await db_session.execute(
            text(
                """
                SELECT MAX(rf.created_at)::date AS last_feedback
                FROM recipe_feedbacks rf
                JOIN household_members hm ON hm.id = rf.member_id
                WHERE hm.household_id = :hid
                """
            ),
            {"hid": household_id},
        )
        last_feedback_row = last_feedback_result.fetchone()
        last_feedback: date | None = last_feedback_row[0] if last_feedback_row else None

        disengaged = (last_feedback is None) or (last_feedback < disengaged_cutoff)

        return {
            "at_risk": at_risk,
            "inactive": inactive,
            "disengaged": disengaged,
            "last_activity": str(last_activity) if last_activity else None,
            "last_feedback": str(last_feedback) if last_feedback else None,
            "plan_count_this_week": plan_count,
        }

    def _log_at_risk(
        self, household_id: str, household_name: str, flags: dict
    ) -> None:
        """
        Log un foyer at_risk.

        Phase 3 : déclenchera un email "On vous manque" via Resend.
        """
        logger.warning(
            "retention_at_risk",
            household_id=household_id,
            household_name=household_name,
            last_activity=flags.get("last_activity"),
            # Phase 3 : action="send_email_at_risk"
            action="log_only",
        )

    def _log_inactive(
        self, household_id: str, household_name: str, flags: dict
    ) -> None:
        """
        Log un foyer inactive.

        Phase 3 : déclenchera une push notification "Votre semaine vous attend".
        """
        logger.info(
            "retention_inactive",
            household_id=household_id,
            household_name=household_name,
            message="Votre semaine vous attend — générez votre plan maintenant !",
            # Phase 3 : action="send_push_inactive"
            action="log_only",
        )

    def _log_disengaged(
        self, household_id: str, household_name: str, flags: dict
    ) -> None:
        """
        Log un foyer disengaged.

        Phase 3 : déclenchera un email de réengagement avec suggestion de recettes.
        """
        logger.warning(
            "retention_disengaged",
            household_id=household_id,
            household_name=household_name,
            last_feedback=flags.get("last_feedback"),
            # Phase 3 : action="send_email_reengagement"
            action="log_only",
        )
