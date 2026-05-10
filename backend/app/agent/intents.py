"""
Intent shapes — the structured output of the IntentRouter.

The agent works in two layers:
  1. Router — turns user text into an Intent (deterministic, no LLM).
  2. Renderer — turns an Intent into code + explanation
     (templates for known kinds, LLM only for `custom` and `qa`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class IntentKind(str, Enum):
    # Inspection (live read of df) — no LLM
    SHOW_HEAD = "show_head"
    SHOW_SHAPE = "show_shape"
    SHOW_DESCRIBE = "show_describe"
    SHOW_MISSING = "show_missing"
    SHOW_COLUMNS = "show_columns"
    SHOW_DTYPES = "show_dtypes"
    SHOW_UNIQUE = "show_unique"
    SHOW_INFO = "show_info"

    # Cleaning — no LLM
    CLEAN_MISSING = "clean_missing"
    DROP_DUPLICATES = "drop_duplicates"
    ENCODE_CATEGORICALS = "encode_categoricals"

    # Visualization — no LLM
    PLOT_DISTRIBUTION = "plot_distribution"
    PLOT_RELATIONSHIP = "plot_relationship"
    PLOT_CORRELATION = "plot_correlation"
    PLOT_CATEGORICAL = "plot_categorical"

    # Modeling — no LLM
    TRAIN_CLASSIFIER = "train_classifier"
    TRAIN_REGRESSOR = "train_regressor"

    # LLM tiers
    QA = "qa"            # text-only reply, no code
    CUSTOM = "custom"    # LLM writes code for an unmatched request


@dataclass
class Intent:
    kind: IntentKind
    params: dict = field(default_factory=dict)
    # The original user text — needed by codegen/qa intents.
    raw_text: str = ""


@dataclass
class IntentResult:
    explanation: str
    code: str | None = None
    source: str = "template"  # "template" | "codegen" | "qa"
