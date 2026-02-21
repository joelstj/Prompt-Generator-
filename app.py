import os
import json
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024  # 64 KB request limit

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_FILE = os.path.join(BASE_DIR, "prompt_templates.json")

MAX_FIELD_LENGTH = 4000  # characters per field

OPENCLAW_INTEGRATION = (
    "Integrate OpenClaw AI into this project:\n\n"
    "SETUP & INSTALL:\n"
    "1. Install: `npm install -g @openclaw/cli` (Node) or `pip install openclaw` (Python)\n"
    "2. Authenticate: `openclaw auth --key $OPENCLAW_API_KEY`\n"
    "3. Initialise: `openclaw init` in the project root — creates `.openclaw.json`\n\n"
    "CONFIGURATION (.openclaw.json):\n"
    "- Set target language, model, and output style preferences\n"
    "- Define allowed libraries and framework constraints\n"
    "- Configure auto-review hooks and CI integration flags\n\n"
    "PROGRAMMING LANGUAGE INSTRUCTIONS:\n"
    "- Specify exact language version (e.g. Python 3.11, Node 20, Solidity ^0.8.20)\n"
    "- Follow language-idiomatic patterns; use type annotations where supported\n"
    "- Adhere to the project linting rules (ESLint, Ruff, solhint, etc.)\n\n"
    "TOOLS TO USE:\n"
    "- IDE: VS Code + OpenClaw extension, or JetBrains with OpenClaw plugin\n"
    "- Version control: Git with `openclaw hooks install` pre-commit review\n"
    "- CI/CD: add `openclaw validate` step before merge gates\n\n"
    "LIBRARIES TO INCLUDE:\n"
    "- `openclaw-sdk` for programmatic API access\n"
    "- Language SDK: `npm install openclaw-js` / `pip install openclaw-python`\n"
    "- Optional: `openclaw-test-assist` for AI-driven test generation\n\n"
    "ENVIRONMENT BUILD, INSTALL & DEPLOY:\n"
    "- Development: `openclaw dev --watch` for continuous inline feedback\n"
    "- Testing: `openclaw test-assist --coverage` to improve test coverage\n"
    "- Pre-deploy audit: `openclaw audit --strict` (fails on any critical issue)\n"
    "- Set `OPENCLAW_API_KEY` environment variable in all environments\n\n"
    "OUTPUT REQUIREMENTS WITH OPENCLAW:\n"
    "- All generated code must pass `openclaw lint` without errors\n"
    "- Include `.openclaw.json` config in the project root\n"
    "- Mark AI-generated sections with `# @openclaw-generated` comments for traceability"
)

BLOCKCHAIN_KEYWORDS = {
    "solidity", "smart contract", "defi", "dex", "nft", "mev", "arbitrage",
    "flash loan", "liquidity", "erc20", "erc721", "web3", "ethereum", "blockchain",
    "uniswap", "aave", "compound", "yield", "staking", "bridge", "cross-chain",
    "on-chain", "gas", "wallet", "token", "swap", "pool", "vault",
}

BLOCKCHAIN_CONTEXT = (
    "You are an expert blockchain and Web3 developer with deep knowledge of Solidity, "
    "DeFi protocols, smart contract security, and on-chain automation. "
    "Prioritize gas efficiency, security best practices, and protocol compatibility. "
)


def _has_blockchain_context(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in BLOCKCHAIN_KEYWORDS)


def _assemble_prompt(data: dict) -> str:
    main_goal = data.get("main_goal", "").strip()
    output_format = data.get("output_format", "").strip()
    rules = data.get("rules", "").strip()
    output_goal = data.get("output_goal", "").strip()
    correctness = data.get("correctness", "").strip()
    how_to_act = data.get("how_to_act", "").strip()
    code_output_guidelines = data.get("code_output_guidelines", "").strip()
    openclaw_integration = bool(data.get("openclaw_integration", False))

    combined = " ".join([main_goal, output_format, rules, output_goal, correctness, how_to_act, code_output_guidelines])
    use_blockchain_ctx = _has_blockchain_context(combined)

    sections = []

    if use_blockchain_ctx:
        sections.append(f"[SYSTEM CONTEXT]\n{BLOCKCHAIN_CONTEXT.strip()}")

    if main_goal:
        sections.append(f"## MAIN GOAL\n{main_goal}")

    if how_to_act:
        sections.append(f"## ROLE & BEHAVIOR\n{how_to_act}")

    if rules:
        sections.append(f"## RULES TO FOLLOW\n{rules}")

    if output_format:
        sections.append(f"## OUTPUT FORMAT\n{output_format}")

    if code_output_guidelines:
        sections.append(f"## CODE OUTPUT GUIDELINES\n{code_output_guidelines}")

    if openclaw_integration:
        sections.append(f"## OPENCLAW AI INTEGRATION\n{OPENCLAW_INTEGRATION}")

    if output_goal:
        sections.append(f"## OUTPUT GOAL\n{output_goal}")

    if correctness:
        sections.append(f"## CORRECTNESS & VERIFICATION\n{correctness}")

    sections.append(
        "## FINAL INSTRUCTION\n"
        "Follow the rules and format above precisely. "
        "Be thorough, accurate, and structured in your response. "
        "If any requirement is ambiguous, state your assumptions clearly before proceeding."
    )

    return "\n\n".join(sections)


def _load_templates() -> list:
    try:
        with open(TEMPLATES_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


# Cache templates once at startup to avoid repeated disk reads.
_TEMPLATES_CACHE: list = _load_templates()


@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "template_count": len(_TEMPLATES_CACHE)})


@app.route("/api/generate", methods=["POST"])
def generate():
    body = request.get_json(silent=True) or {}
    field_names = ["main_goal", "output_format", "rules", "output_goal", "correctness", "how_to_act", "code_output_guidelines"]

    for field in field_names:
        value = body.get(field, "")
        if not isinstance(value, str):
            return jsonify({"error": f"Field '{field}' must be a string."}), 400
        if len(value) > MAX_FIELD_LENGTH:
            return jsonify({"error": f"Field '{field}' exceeds the maximum length of {MAX_FIELD_LENGTH} characters."}), 400

    openclaw = body.get("openclaw_integration", False)
    if not isinstance(openclaw, bool):
        return jsonify({"error": "Field 'openclaw_integration' must be a boolean."}), 400

    if not any(body.get(f, "").strip() for f in field_names) and not openclaw:
        return jsonify({"error": "At least one field must be filled in."}), 400

    prompt = _assemble_prompt(body)
    return jsonify({"prompt": prompt, "char_count": len(prompt)})


@app.route("/api/templates", methods=["GET"])
def get_templates():
    return jsonify(_TEMPLATES_CACHE)


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(413)
def request_too_large(e):
    return jsonify({"error": "Request body too large"}), 413


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=debug)
