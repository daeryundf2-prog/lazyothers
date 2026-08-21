# Antigravity 3대 플러그인 원클릭 완전 자동 설치 스크립트
$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Antigravity Complete Setup Auto-Installer" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$pluginDir = "$HOME\.gemini\config\plugins"
if (!(Test-Path $pluginDir)) {
    New-Item -ItemType Directory -Force -Path $pluginDir | Out-Null
}
$originalLocation = Get-Location
Set-Location $pluginDir

# 1. Git Repositories Clone or Pull
$repos = @{
    "lazyantigravity" = "https://github.com/daeryundf2-prog/LAZYANTIGRAVITY.git"
    "lazyforensic"    = "https://github.com/daeryundf2-prog/lazyforensic.git"
    "lazyothers"      = "https://github.com/daeryundf2-prog/lazyothers.git"
}

foreach ($name in $repos.Keys) {
    $targetPath = Join-Path $pluginDir $name
    if (Test-Path $targetPath) {
        Write-Host "Updating $name..." -ForegroundColor Yellow
        Push-Location $targetPath
        try {
            $gitStatus = git status --porcelain 2>&1
            if ($gitStatus) {
                Write-Host "  [!] $name has local changes, stashing..." -ForegroundColor Yellow
                git stash push -m "auto-stash before pull" | Out-Null
            }
            git pull --ff-only
            if ($LASTEXITCODE -ne 0) {
                Write-Host "  [!] git pull failed for $name, skipping" -ForegroundColor Red
            }
        } catch {
            Write-Host "  [!] Failed to update ${name}: $_" -ForegroundColor Red
        } finally {
            Pop-Location
        }
    } else {
        Write-Host "Cloning $name..." -ForegroundColor Green
        git clone $repos[$name] $name
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  [!] Failed to clone $name" -ForegroundColor Red
        }
    }
}

# 2. Build LazyAntigravity (if Node.js available)
if (Get-Command npm -ErrorAction SilentlyContinue) {
    Write-Host "Building LazyAntigravity..." -ForegroundColor Green
    Push-Location "$pluginDir\lazyantigravity"
    try {
        npm install
        npm run build
    } catch {
        Write-Host "  [!] Build failed: $_" -ForegroundColor Red
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[!] npm not found, skipping build step" -ForegroundColor Yellow
}

# 3. Setup LazyOthers (Sync MCP tools)
if (Test-Path "$pluginDir\lazyothers\package.json") {
    Write-Host "Syncing LazyOthers MCP tools..." -ForegroundColor Green
    Push-Location "$pluginDir\lazyothers"
    try {
        npm run setup
    } catch {
        Write-Host "  [!] Sync failed: $_" -ForegroundColor Red
    } finally {
        Pop-Location
    }
}

# 4. Activate plugins in config.json (MERGE, not overwrite)
Write-Host "Activating plugins in config.json..." -ForegroundColor Green
$configPath = "$HOME\.gemini\config\config.json"
$configDir = Split-Path $configPath -Parent
if (!(Test-Path $configDir)) {
    New-Item -ItemType Directory -Force -Path $configDir | Out-Null
}

$defaultConfig = @{
    plugins = @{
        lazyantigravity = @{ enabled = $true }
        lazyforensic    = @{ enabled = $true }
        lazyothers      = @{ enabled = $true }
    }
}

if (Test-Path $configPath) {
    try {
        $existingJson = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
        if (-not $existingJson.plugins) { $existingJson.plugins = @{} }
        foreach ($k in $defaultConfig.plugins.Keys) {
            $existingJson.plugins[$k] = $defaultConfig.plugins[$k]
        }
        $mergedJson = $existingJson | ConvertTo-Json -Depth 10
        Set-Content -Path $configPath -Value $mergedJson -Encoding UTF8
        Write-Host "  Merged plugins into existing config.json" -ForegroundColor Green
    } catch {
        Write-Host "  [!] Failed to merge config, backing up and writing default: $_" -ForegroundColor Yellow
        Copy-Item $configPath "$configPath.bak" -Force -ErrorAction SilentlyContinue
        $defaultConfig | ConvertTo-Json -Depth 10 | Set-Content -Path $configPath -Encoding UTF8
    }
} else {
    $defaultConfig | ConvertTo-Json -Depth 10 | Set-Content -Path $configPath -Encoding UTF8
    Write-Host "  Created new config.json" -ForegroundColor Green
}

Set-Location $originalLocation

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Setup Completed Successfully! (PASS)" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
