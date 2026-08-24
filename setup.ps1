# ---------------------------------------------------------------------------
# LYRA - finaliza a instalacao do repositorio
#
# Coloca no lugar os arquivos que a ponte remota nao pode escrever
# (.github/ e .pre-commit-config.yaml), inicializa o git e faz o primeiro
# commit. Rode uma vez so.
#
# Como rodar (PowerShell, na pasta lyra):
#     powershell -ExecutionPolicy Bypass -File .\setup.ps1
# ---------------------------------------------------------------------------

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$raiz = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }

function Passo($texto) { Write-Host "  [ok] $texto" -ForegroundColor Green }
function Aviso($texto) { Write-Host "  [--] $texto" -ForegroundColor Yellow }
function Erro($texto)  { Write-Host "  [!!] $texto" -ForegroundColor Red }

Write-Host ""
Write-Host "LYRA - finalizando a estrutura do repositorio" -ForegroundColor Cyan
Write-Host "Pasta: $raiz"
Write-Host ""

# --- 1. Arquivos que precisavam de rename local ----------------------------

$setup = Join-Path $raiz "_setup"

if (Test-Path $setup) {
    $origemGithub = Join-Path $setup "github"
    $destGithub   = Join-Path $raiz ".github"

    if (Test-Path $origemGithub) {
        if (Test-Path $destGithub) { Remove-Item $destGithub -Recurse -Force }
        Move-Item $origemGithub $destGithub
        Passo ".github/ criado - CI, template de PR e 3 templates de issue"
    }

    $origemPre = Join-Path $setup "pre-commit-config.yaml"
    if (Test-Path $origemPre) {
        Move-Item $origemPre (Join-Path $raiz ".pre-commit-config.yaml") -Force
        Passo ".pre-commit-config.yaml criado"
    }

    Remove-Item $setup -Recurse -Force -ErrorAction SilentlyContinue
} else {
    Aviso "_setup/ nao encontrado - provavelmente este script ja rodou antes"
}

$total = (Get-ChildItem $raiz -Recurse -File -Force |
          Where-Object { $_.FullName -notmatch '\\\.git\\' }).Count
Passo "$total arquivos na arvore do projeto"

# --- 2. Git ----------------------------------------------------------------

Write-Host ""

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Erro "git nao encontrado no PATH."
    Write-Host "       Instale em https://git-scm.com/download/win, abra um PowerShell"
    Write-Host "       novo e rode este script de novo."
    exit 1
}

Set-Location $raiz

if (Test-Path (Join-Path $raiz ".git")) {
    Aviso "ja existe um repositorio git aqui - pulando init e commit"
} else {
    $nomeGit  = (git config user.name)  2>$null
    $emailGit = (git config user.email) 2>$null

    if ([string]::IsNullOrWhiteSpace($nomeGit) -or [string]::IsNullOrWhiteSpace($emailGit)) {
        Erro "o git ainda nao sabe quem e voce."
        Write-Host ""
        Write-Host '       git config --global user.name "Gustavo Neves da Paz Rafael"'
        Write-Host '       git config --global user.email "seu-email@exemplo.com"'
        Write-Host ""
        Write-Host "       Rode os dois comandos acima e depois este script de novo."
        exit 1
    }

    git init -b main | Out-Null
    git add -A
    git commit -m "feat: estrutura base do projeto LYRA" | Out-Null

    if ($LASTEXITCODE -eq 0) {
        Passo "repositorio git criado e primeiro commit feito (branch main)"
    } else {
        Erro "o commit falhou - rode 'git status' para ver o que aconteceu"
        exit 1
    }
}

# --- 3. Proximos passos ----------------------------------------------------

Write-Host ""
Write-Host "Pronto. O que falta, e so voce pode fazer:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Crie o repositorio PRIVADO no GitHub (sem README, sem .gitignore)."
Write-Host "     https://github.com/new"
Write-Host ""
Write-Host "  2. Conecte e suba:"
Write-Host ""
Write-Host "     git remote add origin https://github.com/SEU-USUARIO/lyra.git" -ForegroundColor White
Write-Host "     git push -u origin main" -ForegroundColor White
Write-Host ""
Write-Host "  3. Convide o Athayde:"
Write-Host "     Settings > Collaborators > Add people"
Write-Host ""
Write-Host "  4. Proteja a main:"
Write-Host "     Settings > Branches > Add rule > exigir Pull Request"
Write-Host ""
Write-Host "  Para conferir que esta tudo de pe (precisa do uv instalado):"
Write-Host "     uv sync --all-extras" -ForegroundColor White
Write-Host "     uv run pytest" -ForegroundColor White
Write-Host "     -> devem passar 41 testes, 1 pulado"
Write-Host ""
