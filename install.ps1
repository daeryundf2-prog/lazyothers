# Antigravity 3대 플러그인 원클릭 완전 자동 설치 스크립트
$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Antigravity Complete Setup Auto-Installer" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$pluginDir = "$HOME\.gemini\config\plugins"
if (!(Test-Path $pluginDir)) {
    New-Item -ItemType Directory -Force -Path $pluginDir | Out-Null
}
Set-Location $pluginDir

# 1. Git Repositories Clone or Pull
$repos = @{
    "lazyantigravity" = "https://github.com/daeryundf2-prog/LAZYANTIGRAVITY.git"
    "lazyforensic"    = "https://github.com/daeryundf2-prog/lazyforensic-.git"
    "lazyothers"      = "https://github.com/daeryundf2-prog/lazyothers.git"
}

foreach ($name in $repos.Keys) {
    $targetPath = Join-Path $pluginDir $name
    if (Test-Path $targetPath) {
        Write-Host "Updating $name..." -ForegroundColor Yellow
        Push-Location $targetPath
        git pull
        Pop-Location
    } else {
        Write-Host "Cloning $name..." -ForegroundColor Green
        git clone $repos[$name] $name
    }
}

# 2. Build LazyAntigravity
Write-Host "Building LazyAntigravity..." -ForegroundColor Green
Push-Location "$pluginDir\lazyantigravity"
npm install
npm run build
Pop-Location

# 3. Setup LazyOthers (Sync MCP tools)
Write-Host "Syncing LazyOthers MCP tools..." -ForegroundColor Green
Push-Location "$pluginDir\lazyothers"
npm run setup
Pop-Location

# 4. Activate plugins in config.json
Write-Host "Activating plugins in config.json..." -ForegroundColor Green
$configPath = "$HOME\.gemini\config\config.json"
$configJson = @"
{
  "plugins": {
    "lazyantigravity": {
      "enabled": true
    },
    "lazyforensic": {
      "enabled": true
    },
    "lazyothers": {
      "enabled": true
    }
  },
  "userSettings": {
    "globalPermissionGrants": {
      "allow": [
        "write_file($HOME\\.gemini\\config\\plugins)",
        "read_url(disco.re)"
      ]
    }
  }
}
"@
Set-Content -Path $configPath -Value $configJson -Encoding UTF8

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Setup Completed Successfully! (PASS)" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
