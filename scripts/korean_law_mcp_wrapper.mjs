#!/usr/bin/env node
/**
 * korean_law_mcp_wrapper.mjs — Intelligent cross-repo launcher for Korean Law MCP
 * Resolves full API server from lazyforensic / lazyforensic- if available,
 * or gracefully falls back to lazyantigravity offline grounding server.
 */
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const pluginRoot = resolve(dirname(__filename), "..");
const parentDir = resolve(pluginRoot, "..");

const apiKey = process.env.LAW_OC || process.env.KOREAN_LAW_API_KEY;

// Candidate 1: Full API server from lazyforensic or lazyforensic-
const forensicBuildCandidates = [
	join(parentDir, "lazyforensic-", "korean-law-mcp", "build", "index.js"),
	join(parentDir, "lazyforensic", "korean-law-mcp", "build", "index.js"),
];

// Candidate 2: Offline landmark statute/precedent MCP server from lazyantigravity
const antigravityCandidates = [
	join(parentDir, "lazyantigravity", "korean-law-mcp", "dist", "cli.js"),
	join(parentDir, "lazyantigravity", "korean-law-mcp", "src", "cli.mjs"),
];

let targetScript = null;
let targetCwd = pluginRoot;

if (apiKey) {
	for (const candidate of forensicBuildCandidates) {
		if (existsSync(candidate)) {
			targetScript = candidate;
			targetCwd = dirname(dirname(candidate));
			break;
		}
	}
}

if (!targetScript) {
	for (const candidate of antigravityCandidates) {
		if (existsSync(candidate)) {
			targetScript = candidate;
			targetCwd = dirname(dirname(candidate));
			break;
		}
	}
}

if (!targetScript) {
	for (const candidate of forensicBuildCandidates) {
		if (existsSync(candidate)) {
			targetScript = candidate;
			targetCwd = dirname(dirname(candidate));
			break;
		}
	}
}

if (!targetScript) {
	process.stderr.write(
		"[lazyothers] korean_law disabled: neither lazyforensic build/index.js nor lazyantigravity korean-law-mcp found.\n"
	);
	process.exit(78);
}

const child = spawn(process.execPath, [targetScript, "mcp"], {
	cwd: targetCwd,
	env: process.env,
	stdio: "inherit",
	windowsHide: true,
});

child.on("error", (err) => {
	process.stderr.write(`[lazyothers] korean_law failed to spawn: ${err.message}\n`);
	process.exit(1);
});

child.on("exit", (code, signal) => {
	if (signal) {
		process.kill(process.pid, signal);
		return;
	}
	process.exit(code ?? 0);
});
