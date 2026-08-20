import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const pluginRoot = path.resolve(__dirname, "..");
const sourceMcpDir = path.join(pluginRoot, "mcp");

const homeDir = os.homedir();
const targetMcpDir = path.join(homeDir, ".gemini", "antigravity", "mcp");

console.log(`[lazyothers:sync] Syncing MCP definitions from ${sourceMcpDir} -> ${targetMcpDir}`);

if (!fs.existsSync(sourceMcpDir)) {
  console.error(`[lazyothers:sync] Error: Source directory does not exist: ${sourceMcpDir}`);
  process.exit(1);
}

if (!fs.existsSync(targetMcpDir)) {
  fs.mkdirSync(targetMcpDir, { recursive: true });
}

function copyRecursive(src, dest) {
  const stats = fs.statSync(src);
  if (stats.isDirectory()) {
    if (!fs.existsSync(dest)) {
      fs.mkdirSync(dest, { recursive: true });
    }
    const entries = fs.readdirSync(src);
    for (const entry of entries) {
      copyRecursive(path.join(src, entry), path.join(dest, entry));
    }
  } else {
    fs.copyFileSync(src, dest);
  }
}

try {
  const toolDirs = fs.readdirSync(sourceMcpDir);
  for (const tool of toolDirs) {
    const srcTool = path.join(sourceMcpDir, tool);
    const destTool = path.join(targetMcpDir, tool);
    copyRecursive(srcTool, destTool);
    console.log(`  ✓ Synced tool: ${tool}`);
  }
  console.log("[lazyothers:sync] Successfully synced all MCP tools to Antigravity!");
} catch (err) {
  console.error("[lazyothers:sync] Failed to sync MCP tools:", err);
  process.exit(1);
}
