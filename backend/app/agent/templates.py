"""
Templates — turn an Intent into (code, explanation) deterministically.

No LLM here. Every template returns ready-to-run Python plus a one-line
explanation that the UI shows above the code block.

Visualization templates use plotly (interactive in notebooks) with a
plain template — the user can switch theme later without breaking the code.
"""

from __future__ import annotations

from app.agent.intents import Intent, IntentKind, IntentResult


# Default DataFrame variable name. The session sets this when uploading.
DEFAULT_DF = "df"


def render(intent: Intent, df_name: str = DEFAULT_DF) -> IntentResult | None:
    """
    Render an Intent into code + explanation. Returns None for QA / CUSTOM
    intents (those go through LLM paths).
    """
    handler = _HANDLERS.get(intent.kind)
    if handler is None:
        return None
    return handler(intent, df_name)


# --- Inspection ---

def _show_head(intent: Intent, df: str) -> IntentResult:
    n = intent.params.get("n", 5)
    return IntentResult(
        explanation=f"Show the first {n} rows of `{df}`.",
        code=f"{df}.head({n})",
    )


def _show_shape(intent: Intent, df: str) -> IntentResult:
    return IntentResult(
        explanation=f"Print the shape (rows, columns) of `{df}`.",
        code=f"print(f'Shape: {{{df}.shape[0]:,}} rows, {{{df}.shape[1]}} columns')",
    )


def _show_columns(intent: Intent, df: str) -> IntentResult:
    return IntentResult(
        explanation=f"List the column names of `{df}`.",
        code=f"list({df}.columns)",
    )


def _show_dtypes(intent: Intent, df: str) -> IntentResult:
    return IntentResult(
        explanation=f"Show the data type of every column in `{df}`.",
        code=f"{df}.dtypes",
    )


def _show_describe(intent: Intent, df: str) -> IntentResult:
    return IntentResult(
        explanation=f"Compute summary statistics (count, mean, std, min, max, quartiles) for the numeric columns of `{df}`.",
        code=f"{df}.describe(include='all')",
    )


def _show_missing(intent: Intent, df: str) -> IntentResult:
    return IntentResult(
        explanation=f"Count missing values per column in `{df}`, sorted from worst to best.",
        code=(
            f"_missing = {df}.isnull().sum().sort_values(ascending=False)\n"
            f"_missing[_missing > 0]"
        ),
    )


def _show_info(intent: Intent, df: str) -> IntentResult:
    return IntentResult(
        explanation=f"Print non-null counts, dtypes, and memory usage for `{df}`.",
        code=f"{df}.info()",
    )


def _show_unique(intent: Intent, df: str) -> IntentResult:
    col = intent.params["column"]
    return IntentResult(
        explanation=f"Show how many distinct values are in `{col}` and the most common ones.",
        code=(
            f"print(f\"unique: {{{df}['{col}'].nunique()}}\")\n"
            f"{df}['{col}'].value_counts().head(20)"
        ),
    )


# --- Cleaning ---

def _clean_missing(intent: Intent, df: str) -> IntentResult:
    strategy = intent.params.get("strategy", "median")
    if strategy == "drop":
        return IntentResult(
            explanation=f"Drop every row in `{df}` that contains a missing value.",
            code=(
                f"_before = len({df})\n"
                f"{df} = {df}.dropna().reset_index(drop=True)\n"
                f"print(f'dropped {{_before - len({df})}} rows')"
            ),
        )
    fill_expr = {
        "mean": f"{df}.mean(numeric_only=True)",
        "median": f"{df}.median(numeric_only=True)",
        "mode": f"{df}.mode().iloc[0]",
        "zero": "0",
    }[strategy]
    return IntentResult(
        explanation=f"Fill missing values in `{df}` using the {strategy} of each column.",
        code=(
            f"{df} = {df}.fillna({fill_expr})\n"
            f"print(f'remaining missing: {{int({df}.isnull().sum().sum())}}')"
        ),
    )


def _drop_duplicates(intent: Intent, df: str) -> IntentResult:
    return IntentResult(
        explanation=f"Drop duplicate rows from `{df}`.",
        code=(
            f"_before = len({df})\n"
            f"{df} = {df}.drop_duplicates().reset_index(drop=True)\n"
            f"print(f'dropped {{_before - len({df})}} duplicate rows')"
        ),
    )


def _encode_categoricals(intent: Intent, df: str) -> IntentResult:
    method = intent.params.get("method", "label")
    if method == "onehot":
        return IntentResult(
            explanation=f"One-hot encode every categorical column in `{df}`.",
            code=(
                f"_cat_cols = {df}.select_dtypes(include='object').columns.tolist()\n"
                f"{df} = pd.get_dummies({df}, columns=_cat_cols, drop_first=True)\n"
                f"print(f'encoded {{len(_cat_cols)}} columns -> {{{df}.shape[1]}} total columns')"
            ),
        )
    return IntentResult(
        explanation=f"Label-encode every categorical column in `{df}` (each unique value gets an integer).",
        code=(
            "from sklearn.preprocessing import LabelEncoder\n"
            f"_cat_cols = {df}.select_dtypes(include='object').columns.tolist()\n"
            "for _c in _cat_cols:\n"
            f"    {df}[_c] = LabelEncoder().fit_transform({df}[_c].astype(str))\n"
            "print(f'encoded {len(_cat_cols)} columns')"
        ),
    )


# --- Visualization ---

def _plot_distribution(intent: Intent, df: str) -> IntentResult:
    col = intent.params["column"]
    return IntentResult(
        explanation=f"Histogram of `{col}` — shows how values are distributed.",
        code=(
            "import plotly.express as px\n"
            f"fig = px.histogram({df}, x='{col}', nbins=30, title='Distribution of {col}')\n"
            "fig.show()"
        ),
    )


def _plot_relationship(intent: Intent, df: str) -> IntentResult:
    x, y = intent.params["x"], intent.params["y"]
    return IntentResult(
        explanation=f"Scatter plot of `{x}` against `{y}` — shows the relationship between the two.",
        code=(
            "import plotly.express as px\n"
            f"fig = px.scatter({df}, x='{x}', y='{y}', opacity=0.6, title='{x} vs {y}')\n"
            "fig.show()"
        ),
    )


def _plot_correlation(intent: Intent, df: str) -> IntentResult:
    return IntentResult(
        explanation="Correlation heatmap of numeric columns. Values close to +1 or -1 indicate strong linear relationships.",
        code=(
            "import plotly.express as px\n"
            f"_corr = {df}.select_dtypes(include='number').corr()\n"
            "fig = px.imshow(_corr, text_auto='.2f', color_continuous_scale='RdBu_r', "
            "aspect='auto', title='Correlation Matrix')\n"
            "fig.show()"
        ),
    )


def _plot_categorical(intent: Intent, df: str) -> IntentResult:
    col = intent.params["column"]
    return IntentResult(
        explanation=f"Bar chart of value counts in `{col}` (top 20 categories).",
        code=(
            "import plotly.express as px\n"
            f"_counts = {df}['{col}'].value_counts().head(20).reset_index()\n"
            f"_counts.columns = ['{col}', 'count']\n"
            f"fig = px.bar(_counts, x='{col}', y='count', title='Counts by {col}')\n"
            "fig.show()"
        ),
    )


# --- Modeling ---

_CLASSIFIER_IMPORTS: dict[str, tuple[str, str]] = {
    "random_forest": (
        "from sklearn.ensemble import RandomForestClassifier",
        "RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)",
    ),
    "logistic_regression": (
        "from sklearn.linear_model import LogisticRegression",
        "LogisticRegression(max_iter=1000, random_state=42)",
    ),
    "xgboost": (
        "from xgboost import XGBClassifier",
        "XGBClassifier(n_estimators=200, random_state=42, verbosity=0, use_label_encoder=False, eval_metric='logloss')",
    ),
    "lightgbm": (
        "from lightgbm import LGBMClassifier",
        "LGBMClassifier(n_estimators=200, random_state=42, verbosity=-1)",
    ),
}

_REGRESSOR_IMPORTS: dict[str, tuple[str, str]] = {
    "random_forest": (
        "from sklearn.ensemble import RandomForestRegressor",
        "RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)",
    ),
    "linear_regression": (
        "from sklearn.linear_model import LinearRegression",
        "LinearRegression()",
    ),
    "xgboost": (
        "from xgboost import XGBRegressor",
        "XGBRegressor(n_estimators=200, random_state=42, verbosity=0)",
    ),
    "lightgbm": (
        "from lightgbm import LGBMRegressor",
        "LGBMRegressor(n_estimators=200, random_state=42, verbosity=-1)",
    ),
}


def _train_classifier(intent: Intent, df: str) -> IntentResult:
    target = intent.params["target"]
    model_key = intent.params.get("model", "random_forest")
    import_line, ctor = _CLASSIFIER_IMPORTS.get(model_key, _CLASSIFIER_IMPORTS["random_forest"])
    return IntentResult(
        explanation=f"Train a {model_key.replace('_', ' ')} to predict `{target}`. Splits 80/20, encodes categoricals, prints accuracy + classification report.",
        code=(
            "from sklearn.model_selection import train_test_split\n"
            "from sklearn.metrics import accuracy_score, classification_report\n"
            "from sklearn.preprocessing import LabelEncoder\n"
            f"{import_line}\n"
            "\n"
            f"_X = {df}.drop(columns=['{target}']).copy()\n"
            f"_y = {df}['{target}'].copy()\n"
            "for _c in _X.select_dtypes(include='object').columns:\n"
            "    _X[_c] = LabelEncoder().fit_transform(_X[_c].astype(str))\n"
            "_X = _X.fillna(_X.median(numeric_only=True))\n"
            "if _y.dtype == 'object':\n"
            "    _y = LabelEncoder().fit_transform(_y.astype(str))\n"
            "\n"
            "X_train, X_test, y_train, y_test = train_test_split(_X, _y, test_size=0.2, random_state=42, stratify=_y)\n"
            f"model = {ctor}\n"
            "model.fit(X_train, y_train)\n"
            "\n"
            "y_pred = model.predict(X_test)\n"
            "print(f'accuracy: {accuracy_score(y_test, y_pred):.4f}')\n"
            "print(classification_report(y_test, y_pred))"
        ),
    )


def _train_regressor(intent: Intent, df: str) -> IntentResult:
    target = intent.params["target"]
    model_key = intent.params.get("model", "random_forest")
    import_line, ctor = _REGRESSOR_IMPORTS.get(model_key, _REGRESSOR_IMPORTS["random_forest"])
    return IntentResult(
        explanation=f"Train a {model_key.replace('_', ' ')} regressor to predict `{target}`. Splits 80/20, encodes categoricals, prints R² + RMSE.",
        code=(
            "from sklearn.model_selection import train_test_split\n"
            "from sklearn.metrics import r2_score, mean_squared_error\n"
            "from sklearn.preprocessing import LabelEncoder\n"
            "import numpy as np\n"
            f"{import_line}\n"
            "\n"
            f"_X = {df}.drop(columns=['{target}']).copy()\n"
            f"_y = {df}['{target}'].copy()\n"
            "for _c in _X.select_dtypes(include='object').columns:\n"
            "    _X[_c] = LabelEncoder().fit_transform(_X[_c].astype(str))\n"
            "_X = _X.fillna(_X.median(numeric_only=True))\n"
            "\n"
            "X_train, X_test, y_train, y_test = train_test_split(_X, _y, test_size=0.2, random_state=42)\n"
            f"model = {ctor}\n"
            "model.fit(X_train, y_train)\n"
            "\n"
            "y_pred = model.predict(X_test)\n"
            "print(f'R²: {r2_score(y_test, y_pred):.4f}')\n"
            "print(f'RMSE: {np.sqrt(mean_squared_error(y_test, y_pred)):.4f}')"
        ),
    )


_HANDLERS = {
    IntentKind.SHOW_HEAD: _show_head,
    IntentKind.SHOW_SHAPE: _show_shape,
    IntentKind.SHOW_COLUMNS: _show_columns,
    IntentKind.SHOW_DTYPES: _show_dtypes,
    IntentKind.SHOW_DESCRIBE: _show_describe,
    IntentKind.SHOW_MISSING: _show_missing,
    IntentKind.SHOW_INFO: _show_info,
    IntentKind.SHOW_UNIQUE: _show_unique,
    IntentKind.CLEAN_MISSING: _clean_missing,
    IntentKind.DROP_DUPLICATES: _drop_duplicates,
    IntentKind.ENCODE_CATEGORICALS: _encode_categoricals,
    IntentKind.PLOT_DISTRIBUTION: _plot_distribution,
    IntentKind.PLOT_RELATIONSHIP: _plot_relationship,
    IntentKind.PLOT_CORRELATION: _plot_correlation,
    IntentKind.PLOT_CATEGORICAL: _plot_categorical,
    IntentKind.TRAIN_CLASSIFIER: _train_classifier,
    IntentKind.TRAIN_REGRESSOR: _train_regressor,
}
