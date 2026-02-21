#!/usr/bin/env bash
# =============================================================================
#  AI Prompt Generator — Install Script
#  Blockchain & DeFi Dev Edition
# =============================================================================

set -e

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

# ── Banner ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════════╗${RESET}"
echo -e "${CYAN}${BOLD}║       ⚡  AI Prompt Generator  ⚡                        ║${RESET}"
echo -e "${CYAN}${BOLD}║          Blockchain & DeFi Dev Edition                   ║${RESET}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════╝${RESET}"
echo ""

# ── Helper functions ─────────────────────────────────────────────────────────
info()    { echo -e "${BLUE}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; exit 1; }
step()    { echo -e "\n${BOLD}▶  $*${RESET}"; }

# ── Project root (directory of this script) ──────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Step 1: Check Python 3 ────────────────────────────────────────────────────
step "Checking for Python 3"
if ! command -v python3 &>/dev/null; then
  error "Python 3 is not installed or not in PATH. Please install Python 3.9+ and re-run this script."
fi
PY_VERSION=$(python3 --version 2>&1)
success "Found $PY_VERSION"

# Require Python 3.9+
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
if [[ "$PY_MAJOR" -lt 3 || ( "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 9 ) ]]; then
  error "Python 3.9 or higher is required. Found $PY_VERSION"
fi

# ── Step 2: Create virtual environment ───────────────────────────────────────
step "Creating virtual environment (.venv)"
if [[ -d ".venv" ]]; then
  warn ".venv already exists — skipping creation"
else
  python3 -m venv .venv
  success "Virtual environment created at .venv/"
fi

# ── Step 3: Install dependencies ─────────────────────────────────────────────
step "Installing Python dependencies"
source .venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
success "Dependencies installed (Flask)"

# ── Step 4: Create run.sh ────────────────────────────────────────────────────
step "Creating run.sh launcher script"
cat > run.sh <<'RUN_EOF'
#!/usr/bin/env bash
# AI Prompt Generator — Launch Script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -d ".venv" ]]; then
  echo "ERROR: .venv not found. Run ./install.sh first." >&2
  exit 1
fi

source .venv/bin/activate
export FLASK_DEBUG="${FLASK_DEBUG:-false}"
echo ""
echo "  ⚡  Starting AI Prompt Generator..."
echo "  🌐  Open http://localhost:5000 in your browser"
echo "  🛑  Press Ctrl+C to stop"
echo ""
exec python app.py
RUN_EOF

chmod +x run.sh
success "run.sh created and made executable"

# ── Step 5: Deactivate venv (user will use run.sh) ────────────────────────────
deactivate 2>/dev/null || true

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════╗${RESET}"
echo -e "${GREEN}${BOLD}║  ✅  Installation complete!                              ║${RESET}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  ${BOLD}Quick Start:${RESET}"
echo -e "    ${CYAN}./run.sh${RESET}          — start the app"
echo -e "    Then open  ${CYAN}http://localhost:5000${RESET}  in your browser"
echo ""
echo -e "  ${BOLD}Manual start:${RESET}"
echo -e "    ${CYAN}source .venv/bin/activate${RESET}"
echo -e "    ${CYAN}python app.py${RESET}"
echo ""
echo -e "  ${BOLD}Enable debug mode:${RESET}"
echo -e "    ${CYAN}FLASK_DEBUG=true ./run.sh${RESET}"
echo ""
