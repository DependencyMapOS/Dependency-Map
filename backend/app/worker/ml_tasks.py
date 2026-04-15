"""Celery tasks for ML training / refresh."""

from __future__ import annotations

import logging

from app.services.gnn_engine import train_link_prediction_stub

log = logging.getLogger(__name__)


def train_org_model(org_id: str) -> None:
    """Nightly stub: aggregate AST graphs and train when torch-geometric is available."""
    train_link_prediction_stub(org_id, [])
    log.info("train_org_model finished for %s", org_id)
