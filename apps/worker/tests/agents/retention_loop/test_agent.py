"""
Tests unitaires pour RetentionLoopAgent.

Couvre :
1. run() — foyer at_risk détecté (dernière activité > 5 jours)
2. run() — foyer inactive détecté (aucun plan cette semaine)
3. run() — foyer disengaged (aucun feedback depuis 3 semaines)
4. run() — foyer sain (aucun flag)
5. run() — foyer sans activité du tout (first_time_user)
6. _compute_flags — calcul correct des flags
7. run() — stats agrégées correctes (total_checked, counts)

Isolation complète : DB mockée via AsyncMock.
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.agents.retention_loop.agent import (
    AT_RISK_DAYS,
    DISENGAGED_WEEKS,
    RetentionLoopAgent,
)


# ---- Helpers ----

def _make_scalar_result(value):
    """Simule un scalaire retourné par session.execute().scalar()."""
    mock = MagicMock()
    mock.scalar.return_value = value
    return mock


def _make_fetchone_result(value):
    """Simule un fetchone() retourné par session.execute()."""
    mock = MagicMock()
    mock.fetchone.return_value = (value,)
    return mock


def _make_fetchall_result(rows):
    """Simule un fetchall() retourné par session.execute()."""
    mock = MagicMock()
    mock.fetchall.return_value = rows
    return mock


# ---- Tests ----


class TestRetentionLoopAgentFlags:
    """Tests des calculs de flags d'engagement."""

    @pytest.mark.asyncio
    async def test_at_risk_si_derniere_activite_ancienne(self):
        """
        Un foyer dont la dernière activité date de > AT_RISK_DAYS jours
        doit avoir le flag at_risk=True.
        """
        agent = RetentionLoopAgent()
        today = date.today()
        at_risk_cutoff = today - timedelta(days=AT_RISK_DAYS)

        # Dernière activité = il y a 10 jours (> seuil)
        last_activity = today - timedelta(days=10)

        session = AsyncMock()
        # Appels successifs : last_activity, plan_count_this_week, last_feedback
        session.execute = AsyncMock(side_effect=[
            _make_fetchone_result(last_activity),   # MAX(activity_date)
            _make_scalar_result(2),                  # COUNT plan_this_week
            _make_fetchone_result(today),            # MAX(last_feedback) — récent
        ])

        flags = await agent._compute_flags(
            db_session=session,
            household_id=str(uuid4()),
            week_start=today - timedelta(days=today.weekday()),
            at_risk_cutoff=at_risk_cutoff,
            disengaged_cutoff=today - timedelta(weeks=DISENGAGED_WEEKS),
        )

        assert flags["at_risk"] is True

    @pytest.mark.asyncio
    async def test_inactive_si_aucun_plan_cette_semaine(self):
        """
        Un foyer sans plan la semaine courante doit avoir inactive=True.
        """
        agent = RetentionLoopAgent()
        today = date.today()

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            _make_fetchone_result(today),            # last_activity récente
            _make_scalar_result(0),                  # 0 plan cette semaine
            _make_fetchone_result(today),            # last_feedback récent
        ])

        flags = await agent._compute_flags(
            db_session=session,
            household_id=str(uuid4()),
            week_start=today - timedelta(days=today.weekday()),
            at_risk_cutoff=today - timedelta(days=AT_RISK_DAYS),
            disengaged_cutoff=today - timedelta(weeks=DISENGAGED_WEEKS),
        )

        assert flags["inactive"] is True
        assert flags["plan_count_this_week"] == 0

    @pytest.mark.asyncio
    async def test_disengaged_si_aucun_feedback_recent(self):
        """
        Un foyer sans feedback depuis > 3 semaines doit avoir disengaged=True.
        """
        agent = RetentionLoopAgent()
        today = date.today()
        disengaged_cutoff = today - timedelta(weeks=DISENGAGED_WEEKS)

        # Dernier feedback = 4 semaines (> seuil)
        old_feedback = today - timedelta(weeks=4)

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            _make_fetchone_result(today),            # last_activity récente
            _make_scalar_result(1),                  # plan cette semaine
            _make_fetchone_result(old_feedback),     # feedback ancien
        ])

        flags = await agent._compute_flags(
            db_session=session,
            household_id=str(uuid4()),
            week_start=today - timedelta(days=today.weekday()),
            at_risk_cutoff=today - timedelta(days=AT_RISK_DAYS),
            disengaged_cutoff=disengaged_cutoff,
        )

        assert flags["disengaged"] is True

    @pytest.mark.asyncio
    async def test_foyer_sain_aucun_flag(self):
        """
        Un foyer actif récemment, avec plan et feedback récents → aucun flag.
        """
        agent = RetentionLoopAgent()
        today = date.today()

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            _make_fetchone_result(today),    # last_activity aujourd'hui
            _make_scalar_result(3),          # 3 plans cette semaine
            _make_fetchone_result(today),    # feedback aujourd'hui
        ])

        flags = await agent._compute_flags(
            db_session=session,
            household_id=str(uuid4()),
            week_start=today - timedelta(days=today.weekday()),
            at_risk_cutoff=today - timedelta(days=AT_RISK_DAYS),
            disengaged_cutoff=today - timedelta(weeks=DISENGAGED_WEEKS),
        )

        assert flags["at_risk"] is False
        assert flags["inactive"] is False
        assert flags["disengaged"] is False

    @pytest.mark.asyncio
    async def test_foyer_sans_aucune_activite(self):
        """
        Un foyer totalement nouveau (NULL last_activity, NULL feedback) → at_risk + disengaged.
        """
        agent = RetentionLoopAgent()
        today = date.today()

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[
            _make_fetchone_result(None),     # NULL last_activity
            _make_scalar_result(0),          # 0 plans cette semaine
            _make_fetchone_result(None),     # NULL last_feedback
        ])

        flags = await agent._compute_flags(
            db_session=session,
            household_id=str(uuid4()),
            week_start=today - timedelta(days=today.weekday()),
            at_risk_cutoff=today - timedelta(days=AT_RISK_DAYS),
            disengaged_cutoff=today - timedelta(weeks=DISENGAGED_WEEKS),
        )

        assert flags["at_risk"] is True
        assert flags["inactive"] is True
        assert flags["disengaged"] is True


class TestRetentionLoopAgentRun:
    """Tests de la méthode run() avec agrégation des stats."""

    @pytest.mark.asyncio
    async def test_run_retourne_stats_correctes(self):
        """
        run() doit retourner un dict avec les bonnes clés et les bons comptes.
        """
        agent = RetentionLoopAgent()

        # Mock : 2 foyers actifs
        households = [
            (str(uuid4()), "Foyer 1"),
            (str(uuid4()), "Foyer 2"),
        ]

        today = date.today()

        # Foyer 1 : at_risk
        # Foyer 2 : sain
        flags_sequence = [
            # Foyer 1 : at_risk
            _make_fetchone_result(today - timedelta(days=10)),  # last_activity
            _make_scalar_result(1),                              # plan count
            _make_fetchone_result(today),                        # last_feedback
            # Foyer 2 : sain
            _make_fetchone_result(today),                        # last_activity
            _make_scalar_result(2),                              # plan count
            _make_fetchone_result(today),                        # last_feedback
        ]

        session = AsyncMock()
        # Premier appel : liste des foyers
        households_mock = _make_fetchall_result(households)
        session.execute = AsyncMock(side_effect=[households_mock] + flags_sequence)

        result = await agent.run(session)

        assert result["total_checked"] == 2
        assert result["at_risk"] == 1
        assert result["inactive"] == 0
        assert isinstance(result["disengaged"], int)

    @pytest.mark.asyncio
    async def test_run_aucun_foyer_actif(self):
        """
        Si aucun foyer actif, run() retourne des stats à zéro.
        """
        agent = RetentionLoopAgent()

        session = AsyncMock()
        session.execute = AsyncMock(return_value=_make_fetchall_result([]))

        result = await agent.run(session)

        assert result["total_checked"] == 0
        assert result["at_risk"] == 0
        assert result["inactive"] == 0
        assert result["disengaged"] == 0
