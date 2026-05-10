"""
IntentRouter — pattern matches user text into a structured Intent.

This is the deterministic part of the agent. Matching uses regex with
named captures. Column names captured from text are validated against
the loaded DataFrame's columns (case-insensitive); on miss, the rule
is skipped so something else (or the LLM fallback) can match.

Order matters: more specific patterns come first. Question patterns are
checked first so "what does df.head() do" never resolves to SHOW_HEAD.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.agent.intents import Intent, IntentKind


@dataclass
class RouterContext:
    """What the router needs to know about the live session."""
    columns: list[str]  # the actual columns of the loaded df
    has_data: bool


# A rule: regex + a function that builds the Intent given the match + context.
# Returning None means "this rule didn't apply after all" (e.g., column not found).
Rule = tuple[re.Pattern[str], "callable"]


def _norm(text: str) -> str:
    return text.strip().lower()


def _find_column(name: str | None, ctx: RouterContext) -> str | None:
    """Case-insensitive lookup against ctx.columns. Returns the canonical name."""
    if not name:
        return None
    name = name.strip().strip("'\"`")
    for col in ctx.columns:
        if col.lower() == name.lower():
            return col
    return None


def _qa_rule(text: str, ctx: RouterContext) -> Intent | None:
    """Question-shaped utterances → QA intent."""
    t = _norm(text)
    if t.endswith("?"):
        return Intent(IntentKind.QA, raw_text=text)
    if re.match(r"^(why|what|how|explain|tell me|describe what|can you explain)\b", t):
        return Intent(IntentKind.QA, raw_text=text)
    return None


# --- Inspection rules ---

def _show_head(m: re.Match, ctx: RouterContext) -> Intent | None:
    n = int(m.group("n")) if m.group("n") else 5
    return Intent(IntentKind.SHOW_HEAD, params={"n": n})


def _show_unique(m: re.Match, ctx: RouterContext) -> Intent | None:
    col = _find_column(m.group("col"), ctx)
    if not col:
        return None
    return Intent(IntentKind.SHOW_UNIQUE, params={"column": col})


# --- Cleaning ---

def _clean_missing(m: re.Match, ctx: RouterContext) -> Intent | None:
    raw = (m.group("strategy") or "").lower()
    strategy = {
        "drop": "drop", "remove": "drop",
        "mean": "mean", "average": "mean",
        "median": "median",
        "mode": "mode",
        "zero": "zero", "0": "zero",
    }.get(raw, "median")
    return Intent(IntentKind.CLEAN_MISSING, params={"strategy": strategy})


def _encode_cats(m: re.Match, ctx: RouterContext) -> Intent | None:
    raw = (m.group("method") or "label").lower()
    method = "onehot" if "one" in raw or "hot" in raw or "dummy" in raw else "label"
    return Intent(IntentKind.ENCODE_CATEGORICALS, params={"method": method})


# --- Visualization ---

def _plot_relationship(m: re.Match, ctx: RouterContext) -> Intent | None:
    x = _find_column(m.group("x"), ctx)
    y = _find_column(m.group("y"), ctx)
    if not (x and y):
        return None
    return Intent(IntentKind.PLOT_RELATIONSHIP, params={"x": x, "y": y})


def _plot_distribution(m: re.Match, ctx: RouterContext) -> Intent | None:
    col = _find_column(m.group("col"), ctx)
    if not col:
        return None
    return Intent(IntentKind.PLOT_DISTRIBUTION, params={"column": col})


def _plot_categorical(m: re.Match, ctx: RouterContext) -> Intent | None:
    col = _find_column(m.group("col"), ctx)
    if not col:
        return None
    return Intent(IntentKind.PLOT_CATEGORICAL, params={"column": col})


# --- Modeling ---

_MODEL_ALIASES = {
    "random forest": "random_forest",
    "rf": "random_forest",
    "logistic": "logistic_regression",
    "logreg": "logistic_regression",
    "xgboost": "xgboost", "xgb": "xgboost",
    "lightgbm": "lightgbm", "lgbm": "lightgbm",
    "linear": "linear_regression",
}


def _train_classifier(m: re.Match, ctx: RouterContext) -> Intent | None:
    target = _find_column(m.group("target"), ctx)
    if not target:
        return None
    raw_model = (m.group("model") or "").lower().strip()
    model = _MODEL_ALIASES.get(raw_model, "random_forest")
    return Intent(
        IntentKind.TRAIN_CLASSIFIER,
        params={"target": target, "model": model},
    )


def _train_regressor(m: re.Match, ctx: RouterContext) -> Intent | None:
    target = _find_column(m.group("target"), ctx)
    if not target:
        return None
    raw_model = (m.group("model") or "").lower().strip()
    model = _MODEL_ALIASES.get(raw_model, "random_forest")
    return Intent(
        IntentKind.TRAIN_REGRESSOR,
        params={"target": target, "model": model},
    )


# Rules are evaluated in order; the first match wins.
# Each entry: (compiled regex, builder)
RULES: list[tuple[re.Pattern[str], callable]] = [
    # Inspection (no params)
    (re.compile(r"^\s*(show\s+)?(the\s+)?shape\b", re.I),
     lambda m, c: Intent(IntentKind.SHOW_SHAPE)),
    (re.compile(r"^\s*(show\s+)?(the\s+)?(column|col)s?\b\s*$", re.I),
     lambda m, c: Intent(IntentKind.SHOW_COLUMNS)),
    (re.compile(r"^\s*(show\s+)?(the\s+)?(dtypes?|types|schema)\b", re.I),
     lambda m, c: Intent(IntentKind.SHOW_DTYPES)),
    (re.compile(r"^\s*(show\s+)?(the\s+)?(describe|stats|statistics|summary)\b", re.I),
     lambda m, c: Intent(IntentKind.SHOW_DESCRIBE)),
    (re.compile(r"^\s*(show\s+)?(the\s+)?(missing|nulls?|nans?|nas?)(\s+values?)?\b", re.I),
     lambda m, c: Intent(IntentKind.SHOW_MISSING)),
    (re.compile(r"^\s*(show\s+)?info\b\s*$", re.I),
     lambda m, c: Intent(IntentKind.SHOW_INFO)),

    # Inspection (with params)
    (re.compile(r"^\s*(show\s+)?(me\s+)?(the\s+)?(first\s+)?(?P<n>\d+)?\s*(rows?|head|samples?)\b", re.I),
     _show_head),
    (re.compile(r"^\s*(show\s+)?(unique|distinct)\s+(values?\s+)?(in|of|for)\s+(?P<col>[\w\-\.]+)", re.I),
     _show_unique),

    # Cleaning
    (re.compile(r"^\s*(handle|fix|fill|impute|clean)\s+(the\s+)?(missing|nulls?|nans?|nas?)(\s+(values?|with|using)\s+(?P<strategy>\w+))?", re.I),
     _clean_missing),
    (re.compile(r"^\s*(drop|remove)\s+(the\s+)?duplicates?\b", re.I),
     lambda m, c: Intent(IntentKind.DROP_DUPLICATES)),
    (re.compile(r"^\s*(encode|convert)\s+(the\s+)?(categoricals?|cats?|categories)(\s+(using|with|via|as)\s+(?P<method>[\w\-\s]+))?", re.I),
     _encode_cats),

    # Visualization (specific shapes first)
    (re.compile(r"^\s*(plot|show|chart|graph)\s+(?P<x>[\w\-\.]+)\s+(vs|versus|against|by)\s+(?P<y>[\w\-\.]+)", re.I),
     _plot_relationship),
    (re.compile(r"^\s*(scatter|relationship)\s+(plot\s+)?(of\s+)?(?P<x>[\w\-\.]+)\s+(and|vs|versus|with)\s+(?P<y>[\w\-\.]+)", re.I),
     _plot_relationship),
    (re.compile(r"^\s*(plot|show)\s+(the\s+)?(correlation|corr)(\s+(matrix|heatmap))?", re.I),
     lambda m, c: Intent(IntentKind.PLOT_CORRELATION)),
    (re.compile(r"^\s*(heatmap)\b", re.I),
     lambda m, c: Intent(IntentKind.PLOT_CORRELATION)),
    (re.compile(r"^\s*(bar\s+chart|bar\s+plot|count\s+plot|countplot)\s+(of\s+)?(?P<col>[\w\-\.]+)", re.I),
     _plot_categorical),
    (re.compile(r"^\s*(plot|show|chart|histogram|distribution\s+of|hist\s+of|dist\s+of)\s+(the\s+)?(?P<col>[\w\-\.]+)(\s+(distribution|histogram))?", re.I),
     _plot_distribution),

    # Modeling
    (re.compile(r"^\s*(train|build|fit)\s+(a\s+)?(?P<model>[\w\s]+?)?\s*classifier\s+(to\s+predict|for|on)\s+(?P<target>[\w\-\.]+)", re.I),
     _train_classifier),
    (re.compile(r"^\s*(train|build|fit)\s+(a\s+)?(?P<model>[\w\s]+?)?\s*(regressor|regression)\s+(to\s+predict|for|on)\s+(?P<target>[\w\-\.]+)", re.I),
     _train_regressor),
    (re.compile(r"^\s*(predict|classify)\s+(?P<target>[\w\-\.]+)(\s+(using|with)\s+(?P<model>[\w\s]+))?", re.I),
     _train_classifier),
]


def route(text: str, ctx: RouterContext) -> Intent:
    """
    Route user text to an Intent.

    Order:
      1. Question shape → QA (so "what is df.head()" never matches show_head).
      2. Pattern rules in declaration order.
      3. Fallback → CUSTOM (LLM codegen).
    """
    text = text.strip()
    if not text:
        return Intent(IntentKind.CUSTOM, raw_text=text)

    qa = _qa_rule(text, ctx)
    if qa:
        return qa

    for pattern, builder in RULES:
        m = pattern.match(text)
        if not m:
            continue
        intent = builder(m, ctx)
        if intent is not None:
            intent.raw_text = text
            return intent

    return Intent(IntentKind.CUSTOM, raw_text=text)
