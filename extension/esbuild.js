const esbuild = require("esbuild");

const isWatch = process.argv.includes("--watch");

async function main() {
  const ctx = await esbuild.context({
    entryPoints: ["src/extension.ts"],
    bundle: true,
    outdir: "dist",
    external: ["vscode"],
    format: "cjs",
    platform: "node",
    sourcemap: true,
    minify: !isWatch,
  });

  if (isWatch) {
    await ctx.watch();
    console.log("Watching...");
  } else {
    await ctx.rebuild();
    await ctx.dispose();
    console.log("Build complete.");
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
