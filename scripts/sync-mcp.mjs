import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const pluginRoot = path.resolve(__dirname, "..");
const sourceMcpDir = path.join(pluginRoot, "mcp");

// Antigravity spec: plugin's own mcp/ + mcp_config.json is authoritative.
// This sync is OPTIONAL legacy helper — mirrors definitions to the
// global Antigravity MCP directory for older runtimes that expect
// ~/.gemini/antigravity/mcp. It does NOT replace mcp_config.json.
const legacyTarget = path.join(pluginRoot, "..", "..", "antigravity", "mcp");

console.log(`[lazyothers:sync] Source: ${sourceMcpDir}`);
console.log(`[lazyothers:sync] plugin.json mcpServers -> ./mcp_config.json (primary)`);
console.log(`[lazyothers:sync] Legacy mirror target (optional): ${legacyTarget}`);

if (!fs.existsSync(sourceMcpDir)) {
  console.error(`[lazyothers:sync] Error: Source directory does not exist: ${sourceMcpDir}`);
  process.exit(1);
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

// Validate mcp_config.json covers all bundled tools
try {
  const mcpConfigPath = path.join(pluginRoot, "mcp_config.json");
  const mcpConfig = JSON.parse(fs.readFileSync(mcpConfigPath, "utf-8"));
  const bundledTools = fs.readdirSync(sourceMcpDir).filter((d) => fs.statSync(path.join(sourceMcpDir, d)).isDirectory());
  const registeredServers = Object.keys(mcpConfig.mcpServers || {});
  console.log(`[lazyothers:sync] Bundled tools: ${bundledTools.join(", ")}`);
  console.log(`[lazyothers:sync] Registered servers: ${registeredServers.join(", ")}`);
  for (const tool of bundledTools) {
    if (!registeredServers.includes(tool) && tool !== "korean_law") {
      // korean_law is an external optional bridge (lazyforensic)
      if (!registeredServers.includes(tool)) {
        console.warn(`[lazyothers:sync] WARN: bundled tool '${tool}' not in mcp_config.json`);
      }
    }
  }
} catch (e) {
  console.warn(`[lazyothers:sync] Could not validate mcp_config.json: ${e.message}`);
}

// Optional legacy mirror — skip if target parent does not exist
try {
  if (fs.existsSync(path.dirname(legacyTarget))) {
    if (!fs.existsSync(legacyTarget)) {
      fs.mkdirSync(legacyTarget, { recursive: true });
    }
    const toolDirs = fs.readdirSync(sourceMcpDir);
    for (const tool of toolDirs) {
      const srcTool = path.join(sourceMcpDir, tool);
      const destTool = path.join(legacyTarget, tool);
      copyRecursive(srcTool, destTool);
      console.log(`  ✓ Mirrored (legacy): ${tool}`);
    }
  } else {
    console.log("[lazyothers:sync] Legacy target parent not found — skipping mirror (primary is mcp_config.json)");
  }
  console.log("[lazyothers:sync] Done. Primary MCP registration is via plugin.json -> mcp_config.json");
} catch (err) {
  console.error("[lazyothers:sync] Failed:", err);
  process.exit(1);
}
