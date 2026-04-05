import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

/**
 * ShapExplainer — Shows SHAP feature importance.
 *
 * Displays a horizontal bar chart of the top features ranked by
 * their mean absolute SHAP value (how much they influence predictions).
 *
 * Taller bars = more influential features.
 */

interface Props {
  importance: Record<string, number>;
}

export function ShapExplainer({ importance }: Props) {
  const data = Object.entries(importance)
    .slice(0, 15)
    .map(([feature, value]) => ({
      feature: feature.length > 20 ? feature.slice(0, 20) + "…" : feature,
      importance: value,
    }))
    .reverse(); // Reverse so most important is at top

  if (data.length === 0) {
    return (
      <div className="text-xs opacity-60 text-center py-8">
        No explainability data available.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div>
        <h4 className="text-xs font-semibold mb-1 opacity-60">Feature Importance (SHAP)</h4>
        <p className="text-[10px] opacity-40">
          Higher values = more influence on predictions. Based on mean |SHAP value|.
        </p>
      </div>

      <div style={{ height: Math.max(200, data.length * 28) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 100 }}>
            <XAxis type="number" tick={{ fontSize: 10 }} />
            <YAxis
              type="category"
              dataKey="feature"
              tick={{ fontSize: 10 }}
              width={100}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--vscode-editor-background)",
                border: "1px solid var(--vscode-panel-border)",
                fontSize: 11,
              }}
              formatter={(value: number) => value.toFixed(6)}
            />
            <Bar
              dataKey="importance"
              fill="var(--vscode-progressBar-background, #0078d4)"
              radius={[0, 4, 4, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Feature list */}
      <div>
        <h4 className="text-xs font-semibold mb-1 opacity-60">Top Features</h4>
        <div className="space-y-1">
          {Object.entries(importance).slice(0, 10).map(([feature, value], i) => (
            <div key={feature} className="flex items-center gap-2 text-xs">
              <span className="w-5 text-right opacity-40 font-mono">{i + 1}</span>
              <span className="flex-1 truncate">{feature}</span>
              <span className="opacity-60 font-mono">{value.toFixed(4)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
