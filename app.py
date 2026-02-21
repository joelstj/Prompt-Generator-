import os
import json
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024  # 64 KB request limit

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_FILE = os.path.join(BASE_DIR, "prompt_templates.json")

MAX_FIELD_LENGTH = 4000  # characters per field

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

    combined = " ".join([main_goal, output_format, rules, output_goal, correctness, how_to_act])
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
    field_names = ["main_goal", "output_format", "rules", "output_goal", "correctness", "how_to_act"]

    for field in field_names:
        value = body.get(field, "")
        if not isinstance(value, str):
            return jsonify({"error": f"Field '{field}' must be a string."}), 400
        if len(value) > MAX_FIELD_LENGTH:
            return jsonify({"error": f"Field '{field}' exceeds the maximum length of {MAX_FIELD_LENGTH} characters."}), 400

    if not any(body.get(f, "").strip() for f in field_names):
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
