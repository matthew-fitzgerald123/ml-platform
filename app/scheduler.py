"""
Scheduled feature pipeline using APScheduler.

Runs a cron job every 15 minutes to recompute derived features for
active entities, and exposes a backfill utility that replays feature
computation over a historical date range.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.feature_store import FeatureStore

log = logging.getLogger(__name__)

PIPELINE_FEATURE_SET = "derived_signals"
CRON_SCHEDULE = {"minute": "*/15"}  # every 15 minutes


def _compute_derived(raw: dict[str, Any]) -> dict[str, Any]:
    """Derive secondary features from raw financial signals."""
    dti = raw.get("debt_to_income", 0.0)
    score = raw.get("credit_score", 0)
    months = raw.get("months_employed", 0)
    return {
        "risk_score": round(dti * 0.4 + (1 - score / 850) * 0.4 + (1 - min(months, 60) / 60) * 0.2, 4),
        "dti_band": "low" if dti < 0.3 else "medium" if dti < 0.5 else "high",
        "credit_tier": "prime" if score >= 740 else "near_prime" if score >= 670 else "subprime",
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


class FeaturePipeline:
    def __init__(self, feature_store: FeatureStore):
        self.fs = feature_store
        self._scheduler = AsyncIOScheduler()
        self._last_run: Optional[datetime] = None
        self._run_count = 0

    def start(self):
        self._scheduler.add_job(
            self._run_pipeline,
            CronTrigger(**CRON_SCHEDULE),
            id="feature_pipeline",
            replace_existing=True,
            misfire_grace_time=60,
        )
        self._scheduler.start()
        log.info("Feature pipeline scheduler started (cron: %s)", CRON_SCHEDULE)

    def stop(self):
        self._scheduler.shutdown(wait=False)
        log.info("Feature pipeline scheduler stopped")

    def status(self) -> dict:
        job = self._scheduler.get_job("feature_pipeline")
        return {
            "running": self._scheduler.running,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "run_count": self._run_count,
            "next_run": job.next_run_time.isoformat() if job and job.next_run_time else None,
            "cron": CRON_SCHEDULE,
        }

    async def _run_pipeline(self):
        """Called by the scheduler: fetch all entities and recompute derived features."""
        log.info("Feature pipeline run starting")
        try:
            feature_sets = self.fs.list_feature_sets()
            source_sets = [f["name"] for f in feature_sets if f["name"] != PIPELINE_FEATURE_SET]

            entity_ids: set[str] = set()
            for fs_name in source_sets:
                rows = self.fs.get_historical([], fs_name, limit=500)
                entity_ids.update(r["entity_id"] for r in rows)

            updated = 0
            for entity_id in entity_ids:
                raw = {}
                for fs_name in source_sets:
                    vals = self.fs.get(entity_id, fs_name)
                    if vals:
                        raw.update(vals)
                if raw:
                    derived = _compute_derived(raw)
                    self.fs.write(entity_id, PIPELINE_FEATURE_SET, derived)
                    updated += 1

            self._last_run = datetime.now(timezone.utc)
            self._run_count += 1
            log.info("Feature pipeline complete: %d entities updated", updated)
        except Exception:
            log.exception("Feature pipeline run failed")

    def backfill(self, start: datetime, end: datetime, entity_ids: list[str]) -> dict:
        """
        Replay feature computation for a list of entities over [start, end].
        Snapshots one derived record per entity per day in the range.
        """
        days = (end - start).days + 1
        written = 0
        skipped = 0

        for entity_id in entity_ids:
            raw: dict[str, Any] = {}
            for fs_name in self.fs.list_feature_sets():
                name = fs_name["name"] if isinstance(fs_name, dict) else fs_name
                if name == PIPELINE_FEATURE_SET:
                    continue
                vals = self.fs.get(entity_id, name)
                if vals:
                    raw.update(vals)

            if not raw:
                skipped += 1
                continue

            for day_offset in range(days):
                as_of = start + timedelta(days=day_offset)
                derived = _compute_derived(raw)
                derived["computed_at"] = as_of.isoformat()
                self.fs.write(entity_id, PIPELINE_FEATURE_SET, derived)
                written += 1

        return {
            "entities_processed": len(entity_ids) - skipped,
            "entities_skipped": skipped,
            "records_written": written,
            "start": start.isoformat(),
            "end": end.isoformat(),
        }
