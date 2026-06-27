"""
Typed configuration loader.

All thresholds live in config/claims_policy.yml.
Secrets and paths come from environment via pydantic-settings.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

POC_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POLICY_PATH = POC_ROOT / "config" / "claims_policy.yml"


class EnvSettings(BaseSettings):
    """Environment-backed settings (secrets + paths)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    langchain_tracing_v2: bool = Field(default=False, alias="LANGCHAIN_TRACING_V2")
    langchain_api_key: str = Field(default="", alias="LANGCHAIN_API_KEY")
    langchain_project: str = Field(
        default="claims-multiagent-rag-poc", alias="LANGCHAIN_PROJECT"
    )
    claims_policy_config: Path = Field(
        default=DEFAULT_POLICY_PATH, alias="CLAIMS_POLICY_CONFIG"
    )
    chroma_persist_dir: Path = Field(
        default=POC_ROOT / ".cache" / "chroma", alias="CHROMA_PERSIST_DIR"
    )
    audit_db_path: Path = Field(
        default=POC_ROOT / ".cache" / "audit_trail.sqlite", alias="AUDIT_DB_PATH"
    )


class IntakeConfig:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.min_extraction_confidence: float = float(raw["min_extraction_confidence"])
        self.required_fields: tuple[str, ...] = tuple(raw["required_fields"])


class RetrievalConfig:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.top_k_per_collection: int = int(raw["top_k_per_collection"])
        self.min_similarity_score: float = float(raw["min_similarity_score"])


class FraudConfig:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.escalate_risk_score: float = float(raw["escalate_risk_score"])
        self.max_claims_30_days: int = int(raw["max_claims_30_days"])
        self.min_days_since_policy_start: int = int(raw["min_days_since_policy_start"])
        self.amount_vs_limit_flag_ratio: float = float(raw["amount_vs_limit_flag_ratio"])


class AdjudicationConfig:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.human_review_threshold_usd: float = float(raw["human_review_threshold_usd"])
        self.min_decision_confidence: float = float(raw["min_decision_confidence"])
        self.require_policy_citation: bool = bool(raw["require_policy_citation"])


class VectorStoreConfig:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.chunk_size: int = int(raw["chunk_size"])
        self.chunk_overlap: int = int(raw["chunk_overlap"])
        self.collections: dict[str, str] = dict(raw["collections"])


class AuditConfig:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.db_filename: str = str(raw["db_filename"])
        self.pii_redact_patterns: tuple[str, ...] = tuple(raw["pii_redact_patterns"])


class LlmConfig:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.provider: str = str(raw["provider"])
        self.model: str = str(raw["model"])
        self.temperature: float = float(raw["temperature"])
        self.max_tokens: int = int(raw["max_tokens"])


class EmbeddingsConfig:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.provider: str = str(raw["provider"])
        self.model: str = str(raw["model"])
        self.fallback: str = str(raw["fallback"])


class ClaimsPolicyConfig:
    """Full typed view of claims_policy.yml."""

    def __init__(self, raw: dict[str, Any]) -> None:
        self.intake = IntakeConfig(raw["intake"])
        self.retrieval = RetrievalConfig(raw["retrieval"])
        self.fraud = FraudConfig(raw["fraud"])
        self.adjudication = AdjudicationConfig(raw["adjudication"])
        self.vector_store = VectorStoreConfig(raw["vector_store"])
        self.audit = AuditConfig(raw["audit"])
        self.llm = LlmConfig(raw["llm"])
        self.embeddings = EmbeddingsConfig(raw["embeddings"])


def load_policy_yaml(path: Path | None = None) -> ClaimsPolicyConfig:
    cfg_path = path or DEFAULT_POLICY_PATH
    with cfg_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return ClaimsPolicyConfig(raw)


@lru_cache
def get_env_settings() -> EnvSettings:
    return EnvSettings()


@lru_cache
def get_policy_config() -> ClaimsPolicyConfig:
    env = get_env_settings()
    return load_policy_yaml(env.claims_policy_config)
