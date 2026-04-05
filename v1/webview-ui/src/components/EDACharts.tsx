import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

/**
 * EDACharts — Visualizes exploratory data analysis results.
 *
 * Shows:
 *   - Top feature correlations with target (bar chart)
 *   - Outlier summary per column
 *   - Categorical value distributions
 *
 * Uses Recharts for interactive charts that work inside VS Code webview.
 */

interface Props {
  eda: {
    distributions: Record<string, any>;
    outliers: Record<string, { n_outliers: number; percent: number }>;
    target_correlations: Record<string, number>;
    categorical_summaries: Record<string, Record<string, number>>;
  };
}

export function EDACharts({ eda }: Props) {
  // Prepare correlation data for bar chart
  const correlationData = Object.entries(eda.target_correlations || {})
    .slice(0, 10)
    .map(([feature, value]) => ({
      feature: feature.length > 15 ? feature.slice(0, 15) + "…" : feature,
      correlation: value,
      fill: value > 0 ? "#4caf50" : "#f44336",
    }));

  // Outlier summary
  const outlierData = Object.entries(eda.outliers || {})
    .filter(([, info]) => info.n_outliers > 0)
    .sort((a, b) => b[1].percent - a[1].percent)
    .slice(0, 10);

  return (
    <div className="space-y-4">
      {/* Target correlations */}
      {correlationData.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold mb-2 opacity-60">Feature Correlations with Target</h4>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={correlationData} layout="vertical" margin={{ left: 80 }}>
                <XAxis type="number" domain={[-1, 1]} tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="feature" tick={{ fontSize: 10 }} width={80} />
                <Tooltip
                  contentStyle={{ backgroundColor: "var(--vscode-editor-background)", border: "1px solid var(--vscode-panel-border)", fontSize: 11 }}
                />
                <Bar dataKey="correlation" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-[10px] opacity-40 mt-1">
            Positive = feature increases with target. Negative = feature decreases with target.
          </p>
        </div>
      )}

      {/* Outliers */}
      {outlierData.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold mb-1 opacity-60">Outliers Detected</h4>
          <div className="space-y-1">
            {outlierData.map(([col, info]) => (
              <div key={col} className="flex items-center gap-2 text-xs">
                <span className="w-28 truncate">{col}</span>
                <div className="flex-1 bg-vscode-input-bg rounded-full h-2">
                  <div
                    className="h-2 rounded-full bg-orange-500"
                    style={{ width: `${Math.min(info.percent, 100)}%` }}
                  />
                </div>
                <span className="w-16 text-right opacity-60">
                  {info.n_outliers} ({info.percent}%)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Categorical distributions */}
      {Object.keys(eda.categorical_summaries || {}).length > 0 && (
        <div>
          <h4 className="text-xs font-semibold mb-1 opacity-60">Categorical Distributions</h4>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(eda.categorical_summaries).slice(0, 4).map(([col, counts]) => (
              <div key={col} className="border border-vscode-border rounded p-2">
                <div className="text-xs font-medium mb-1">{col}</div>
                {Object.entries(counts).slice(0, 5).map(([val, count]) => (
                  <div key={val} className="flex justify-between text-[10px] opacity-70">
                    <span className="truncate mr-2">{val}</span>
                    <span>{count}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
