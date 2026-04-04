/**
 * DataProfileView — Displays dataset profiling results.
 *
 * Shows:
 *   - Dataset shape (rows × columns)
 *   - Missing values per column
 *   - Numeric column statistics (mean, median, std, min, max)
 *   - Warnings (high missing, constant columns, etc.)
 */

interface Props {
  profile: {
    shape: [number, number];
    numeric_columns: string[];
    categorical_columns: string[];
    missing_values: Record<string, { count: number; percent: number }>;
    n_duplicates: number;
    numeric_stats: Record<string, { mean: number; median: number; std: number; min: number; max: number }>;
    warnings: string[];
  };
}

export function DataProfileView({ profile }: Props) {
  const missingEntries = Object.entries(profile.missing_values);

  return (
    <div className="space-y-3">
      {/* Overview cards */}
      <div className="grid grid-cols-3 gap-2">
        <StatCard label="Rows" value={profile.shape[0].toLocaleString()} />
        <StatCard label="Columns" value={profile.shape[1].toString()} />
        <StatCard label="Duplicates" value={profile.n_duplicates.toString()} />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <StatCard label="Numeric" value={profile.numeric_columns.length.toString()} />
        <StatCard label="Categorical" value={profile.categorical_columns.length.toString()} />
      </div>

      {/* Warnings */}
      {profile.warnings.length > 0 && (
        <div className="border border-yellow-500/30 bg-yellow-500/10 rounded p-2">
          <h4 className="text-xs font-semibold text-yellow-400 mb-1">Warnings</h4>
          {profile.warnings.map((w, i) => (
            <p key={i} className="text-xs opacity-80">{w}</p>
          ))}
        </div>
      )}

      {/* Missing values */}
      {missingEntries.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold mb-1 opacity-60">Missing Values</h4>
          <div className="space-y-1">
            {missingEntries.map(([col, info]) => (
              <div key={col} className="flex items-center gap-2 text-xs">
                <span className="w-24 truncate">{col}</span>
                <div className="flex-1 bg-vscode-input-bg rounded-full h-2">
                  <div
                    className="h-2 rounded-full"
                    style={{
                      width: `${Math.min(info.percent, 100)}%`,
                      backgroundColor: info.percent > 50 ? "#f44336" : info.percent > 20 ? "#ff9800" : "#4caf50",
                    }}
                  />
                </div>
                <span className="w-12 text-right opacity-60">{info.percent}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Numeric stats table */}
      {Object.keys(profile.numeric_stats).length > 0 && (
        <div>
          <h4 className="text-xs font-semibold mb-1 opacity-60">Numeric Statistics</h4>
          <div className="overflow-x-auto border border-vscode-border rounded">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-vscode-input-bg">
                  <th className="px-2 py-1 text-left">Column</th>
                  <th className="px-2 py-1 text-right">Mean</th>
                  <th className="px-2 py-1 text-right">Median</th>
                  <th className="px-2 py-1 text-right">Std</th>
                  <th className="px-2 py-1 text-right">Min</th>
                  <th className="px-2 py-1 text-right">Max</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(profile.numeric_stats).map(([col, stats]) => (
                  <tr key={col} className="border-t border-vscode-border">
                    <td className="px-2 py-1 font-medium">{col}</td>
                    <td className="px-2 py-1 text-right opacity-80">{stats.mean}</td>
                    <td className="px-2 py-1 text-right opacity-80">{stats.median}</td>
                    <td className="px-2 py-1 text-right opacity-80">{stats.std}</td>
                    <td className="px-2 py-1 text-right opacity-80">{stats.min}</td>
                    <td className="px-2 py-1 text-right opacity-80">{stats.max}</td>
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

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-vscode-input-bg rounded p-2 text-center">
      <div className="text-lg font-bold">{value}</div>
      <div className="text-[10px] opacity-60 uppercase">{label}</div>
    </div>
  );
}
