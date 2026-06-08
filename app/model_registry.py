from __future__ import annotations

from sqlalchemy.orm import Session
from app.models import ModelVersion

VALID_STAGES = {"none", "staging", "production", "archived"}


class ModelRegistry:
    def __init__(self, db: Session):
        self.db = db

    def register(
        self,
        name: str,
        version: str,
        artifact_uri: str,
        metrics: dict | None = None,
        params: dict | None = None,
    ) -> ModelVersion:
        existing = (
            self.db.query(ModelVersion)
            .filter_by(name=name, version=version)
            .first()
        )
        if existing:
            return existing
        mv = ModelVersion(
            name=name,
            version=version,
            artifact_uri=artifact_uri,
            metrics=metrics or {},
            params=params or {},
        )
        self.db.add(mv)
        self.db.commit()
        self.db.refresh(mv)
        return mv

    def list_names(self) -> list[str]:
        from sqlalchemy import distinct
        rows = self.db.query(distinct(ModelVersion.name)).order_by(ModelVersion.name).all()
        return [r[0] for r in rows]

    def list_versions(self, name: str) -> list[dict]:
        rows = (
            self.db.query(ModelVersion)
            .filter_by(name=name)
            .order_by(ModelVersion.created_at.desc())
            .all()
        )
        return [_serialize(r) for r in rows]

    def promote(self, name: str, version: str, stage: str) -> ModelVersion:
        if stage not in VALID_STAGES:
            raise ValueError(f"Invalid stage '{stage}'. Must be one of {sorted(VALID_STAGES)}")

        mv = self.db.query(ModelVersion).filter_by(name=name, version=version).first()
        if not mv:
            raise KeyError(f"Model '{name}' version '{version}' not found")

        # demote any existing version holding this stage
        if stage in ("staging", "production"):
            (
                self.db.query(ModelVersion)
                .filter(
                    ModelVersion.name == name,
                    ModelVersion.stage == stage,
                    ModelVersion.id != mv.id,
                )
                .update({"stage": "archived"})
            )

        mv.stage = stage
        self.db.commit()
        self.db.refresh(mv)
        return mv

    def get_by_stage(self, name: str, stage: str) -> ModelVersion | None:
        return (
            self.db.query(ModelVersion)
            .filter_by(name=name, stage=stage)
            .order_by(ModelVersion.created_at.desc())
            .first()
        )


def _serialize(mv: ModelVersion) -> dict:
    return {
        "name": mv.name,
        "version": mv.version,
        "stage": mv.stage,
        "artifact_uri": mv.artifact_uri,
        "metrics": mv.metrics,
        "params": mv.params,
        "created_at": str(mv.created_at),
    }
