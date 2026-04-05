import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

/**
 * ModelComparison — Shows model training results and evaluation metrics.
 *
 * Displays:
 *   1. Bar chart comparing CV scores across 4 models
 *   2. Best model highlighted
 *   3. Test set evaluation metrics (accuracy/F1 or MAE/RMSE/R²)
 *   4. Confusion matrix (for classification)
 */

interface Props {
  cvResults: Record<string, any>;
  bestModel: string;
  evaluation: any;
  taskType: string;
}

export function ModelComparison({ cvResults, bestModel, evaluation, taskType }: Props) {
  // Prepare chart data
  const chartData = Object.entries(cvResults)
    .filter(([, v]) => !v.error)
    .map(([name, result]) => ({
      name: name.length > 12 ? name.slice(0, 12) + "…" : name,
      fullName: name,
      score: taskType === "classification"
        ? result.mean_cv_accuracy
        : result.mean_cv_rmse,
      isBest: name === bestModel,
    }));

  const metricLabel = taskType === "classification" ? "CV Accuracy" : "CV RMSE";

  return (
    <div className="space-y-4">
      {/* Model comparison chart */}
      <div>
        <h4 className="text-xs font-semibold mb-2 opacity-60">Model Comparison ({metricLabel})</h4>
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <XAxis dataKey="name" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip
                contentStyle={{ backgroundColor: "var(--vscode-editor-background)", border: "1px solid var(--vscode-panel-border)", fontSize: 11 }}
                formatter={(value: number) => value.toFixed(4)}
              />
              <Bar
                dataKey="score"
                radius={[4, 4, 0, 0]}
                fill="var(--vscode-progressBar-background, #0078d4)"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Best model callout */}
      <div className="bg-green-500/10 border border-green-500/30 rounded p-3">
        <div className="text-xs font-semibold text-green-400">Best Model</div>
        <div className="text-sm font-bold mt-1">{bestModel}</div>
        {cvResults[bestModel] && (
          <div className="text-xs opacity-70 mt-1">
            {taskType === "classification"
              ? `CV Accuracy: ${cvResults[bestModel].mean_cv_accuracy} (±${cvResults[bestModel].std})`
              : `CV RMSE: ${cvResults[bestModel].mean_cv_rmse} (±${cvResults[bestModel].std})`}
          </div>
        )}
      </div>

      {/* Test set metrics */}
      {evaluation && (
        <div>
          <h4 className="text-xs font-semibold mb-2 opacity-60">Test Set Evaluation</h4>
          <div className="grid grid-cols-3 gap-2">
            {taskType === "classification" ? (
              <>
                <MetricCard label="Accuracy" value={evaluation.accuracy} />
                <MetricCard label="F1 Score" value={evaluation.f1_score} />
                <MetricCard label="Precision" value={evaluation.precision} />
                <MetricCard label="Recall" value={evaluation.recall} />
                {evaluation.roc_auc && <MetricCard label="ROC-AUC" value={evaluation.roc_auc} />}
              </>
            ) : (
              <>
                <MetricCard label="MAE" value={evaluation.mae} />
                <MetricCard label="RMSE" value={evaluation.rmse} />
                <MetricCard label="R²" value={evaluation.r2} />
              </>
            )}
          </div>
        </div>
      )}

      {/* Confusion matrix */}
      {evaluation?.confusion_matrix && (
        <div>
          <h4 className="text-xs font-semibold mb-1 opacity-60">Confusion Matrix</h4>
          <div className="inline-block border border-vscode-border rounded overflow-hidden">
            <table className="text-xs">
              <thead>
                <tr className="bg-vscode-input-bg">
                  <th className="px-3 py-1"></th>
                  {evaluation.class_labels?.map((label: string) => (
                    <th key={label} className="px-3 py-1 text-center">Pred: {label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {evaluation.confusion_matrix.map((row: number[], i: number) => (
                  <tr key={i} className="border-t border-vscode-border">
                    <td className="px-3 py-1 font-medium bg-vscode-input-bg">
                      True: {evaluation.class_labels?.[i] || i}
                    </td>
                    {row.map((val: number, j: number) => (
                      <td
                        key={j}
                        className="px-3 py-1 text-center font-mono"
                        style={{
                          backgroundColor: i === j ? "rgba(76, 175, 80, 0.2)" : "rgba(244, 67, 54, 0.1)",
                        }}
                      >
                        {val}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-vscode-input-bg rounded p-2 text-center">
      <div className="text-base font-bold">{typeof value === "number" ? value.toFixed(4) : value}</div>
      <div className="text-[10px] opacity-60 uppercase">{label}</div>
    </div>
  );
}
