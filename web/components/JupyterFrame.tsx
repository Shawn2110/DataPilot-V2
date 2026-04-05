"use client";

/**
 * JupyterFrame — Embeds JupyterLab in an iframe.
 *
 * JupyterLab runs on a separate server (port 8888).
 * We load it in an iframe pointing to the notebook path.
 * The backend manages the notebook file — when the agent generates code,
 * the backend inserts cells via Jupyter Server REST API, and JupyterLab
 * reflects the changes.
 */
export function JupyterFrame({
  baseUrl,
  token,
  notebookPath,
}: {
  baseUrl: string;
  token: string;
  notebookPath: string;
}) {
  const src = `${baseUrl}/lab/tree/${notebookPath}?token=${token}`;

  return (
    <iframe
      src={src}
      className="w-full h-full border-0"
      sandbox="allow-scripts allow-same-origin allow-popups allow-forms allow-modals"
      title="JupyterLab"
    />
  );
}
