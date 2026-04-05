const esbuild = require("esbuild");

const isWatch = process.argv.includes("--watch");

async function main() {
  const ctx = await esbuild.context({
    entryPoints: ["src/extension.ts"],
    bundle: true,
    outdir: "dist",
    external: ["vscode"], // vscode module is provided by VS Code at runtime
    format: "cjs",        // VS Code extensions use CommonJS
    platform: "node",     // runs in Node.js, not browser
    sourcemap: true,
    minify: !isWatch,
  });

  if (isWatch) {
    await ctx.watch();
    console.log("Watching for changes...");
  } else {
    await ctx.rebuild();
    await ctx.dispose();
    console.log("Build complete.");
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
