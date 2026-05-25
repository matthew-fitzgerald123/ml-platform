from __future__ import annotations

import json
import redis as redis_lib
from sqlalchemy.orm import Session
from app.models import FeatureSet, FeatureValue

class FeatureStore:
    def __init__(self, db: Session, redis_client: redis_lib.Redis):
        self.db    = db
        self.redis = redis_client
        self.ttl   = 3600

    def register(self, name: str, schema: dict) -> FeatureSet:
        existing = self.db.query(FeatureSet).filter_by(name=name).first()
        if existing:
            return existing
        fs = FeatureSet(name=name, schema=schema)
        self.db.add(fs)
        self.db.commit()
        self.db.refresh(fs)
        return fs

    def list_feature_sets(self) -> list[dict]:
        rows = self.db.query(FeatureSet).all()
        return [{"name": r.name, "schema": r.schema, "created_at": str(r.created_at)} for r in rows]

    def write(self, entity_id: str, feature_set: str, features: dict) -> FeatureValue:
        fv = FeatureValue(entity_id=entity_id, feature_set=feature_set, features=features)
        self.db.add(fv)
        self.db.commit()
        self.db.refresh(fv)
        self.redis.setex(
            f"fs:{feature_set}:{entity_id}",
            self.ttl,
            json.dumps(features)
        )
        return fv

    def get(self, entity_id: str, feature_set: str) -> dict | None:
        cached = self.redis.get(f"fs:{feature_set}:{entity_id}")
        if cached:
            return json.loads(cached)
        fv = (
            self.db.query(FeatureValue)
            .filter_by(entity_id=entity_id, feature_set=feature_set)
            .order_by(FeatureValue.created_at.desc())
            .first()
        )
        if fv:
            self.redis.setex(f"fs:{feature_set}:{entity_id}", self.ttl, json.dumps(fv.features))
            return fv.features
        return None

    def get_historical(self, entity_ids: list[str], feature_set: str, limit: int = 0) -> list[dict]:
        q = self.db.query(FeatureValue).filter(FeatureValue.feature_set == feature_set)
        if entity_ids:
            q = q.filter(FeatureValue.entity_id.in_(entity_ids))
        q = q.order_by(FeatureValue.created_at.desc())
        if limit:
            q = q.limit(limit)
        rows = q.all()
        seen, result = set(), []
        for row in rows:
            if row.entity_id not in seen:
                seen.add(row.entity_id)
                result.append({"entity_id": row.entity_id, **row.features})
        return result
