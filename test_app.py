"""Tests for the AI Prompt Generator Flask application."""
import json
import pytest
from app import app, _assemble_prompt, _has_blockchain_context, _TEMPLATES_CACHE, MAX_FIELD_LENGTH


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── Index route ────────────────────────────────────────────────────────────────

class TestIndex:
    def test_returns_200(self, client):
        res = client.get("/")
        assert res.status_code == 200

    def test_returns_html(self, client):
        res = client.get("/")
        assert b"<!DOCTYPE html>" in res.data or b"<html" in res.data

    def test_contains_generate_button(self, client):
        res = client.get("/")
        assert b"generate-btn" in res.data


# ── Health endpoint ────────────────────────────────────────────────────────────

class TestHealth:
    def test_returns_200(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200

    def test_returns_ok_status(self, client):
        data = json.loads(client.get("/api/health").data)
        assert data["status"] == "ok"

    def test_returns_template_count(self, client):
        data = json.loads(client.get("/api/health").data)
        assert "template_count" in data
        assert isinstance(data["template_count"], int)
        assert data["template_count"] >= 0


# ── Templates endpoint ─────────────────────────────────────────────────────────

class TestTemplates:
    def test_returns_200(self, client):
        res = client.get("/api/templates")
        assert res.status_code == 200

    def test_returns_json_list(self, client):
        res = client.get("/api/templates")
        data = json.loads(res.data)
        assert isinstance(data, list)

    def test_templates_have_required_fields(self, client):
        required = {"id", "name", "category", "description",
                    "main_goal", "output_format", "rules",
                    "output_goal", "correctness", "how_to_act"}
        data = json.loads(client.get("/api/templates").data)
        for t in data:
            for field in required:
                assert field in t, f"Template '{t.get('id')}' missing field '{field}'"

    def test_template_count_matches_cache(self, client):
        data = json.loads(client.get("/api/templates").data)
        assert len(data) == len(_TEMPLATES_CACHE)

    def test_post_not_allowed(self, client):
        res = client.post("/api/templates")
        assert res.status_code == 405


# ── Generate endpoint ──────────────────────────────────────────────────────────

class TestGenerate:
    def _post(self, client, payload):
        return client.post(
            "/api/generate",
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_empty_body_returns_400(self, client):
        res = self._post(client, {})
        assert res.status_code == 400
        assert b"error" in res.data

    def test_all_blank_fields_returns_400(self, client):
        res = self._post(client, {"main_goal": "   ", "rules": ""})
        assert res.status_code == 400

    def test_single_field_returns_200(self, client):
        res = self._post(client, {"main_goal": "Write a hello world contract"})
        assert res.status_code == 200

    def test_response_has_prompt_and_char_count(self, client):
        res = self._post(client, {"main_goal": "test goal"})
        data = json.loads(res.data)
        assert "prompt" in data
        assert "char_count" in data

    def test_char_count_matches_prompt_length(self, client):
        res = self._post(client, {"main_goal": "test goal"})
        data = json.loads(res.data)
        assert data["char_count"] == len(data["prompt"])

    def test_non_string_field_returns_400(self, client):
        res = self._post(client, {"main_goal": 12345})
        assert res.status_code == 400
        assert b"must be a string" in res.data

    def test_field_over_max_length_returns_400(self, client):
        res = self._post(client, {"main_goal": "x" * (MAX_FIELD_LENGTH + 1)})
        assert res.status_code == 400
        assert b"exceeds the maximum length" in res.data

    def test_field_at_max_length_returns_200(self, client):
        res = self._post(client, {"main_goal": "x" * MAX_FIELD_LENGTH})
        assert res.status_code == 200

    def test_missing_content_type_returns_400(self, client):
        # No JSON content-type → body parsed as None → treated as empty
        res = client.post("/api/generate", data="not json")
        assert res.status_code == 400

    def test_get_not_allowed(self, client):
        res = client.get("/api/generate")
        assert res.status_code == 405

    def test_all_fields_populated(self, client):
        payload = {
            "main_goal":     "Build a DeFi protocol",
            "output_format": "Markdown with code blocks",
            "rules":         "1. Use OpenZeppelin\n2. Gas optimized",
            "output_goal":   "A deployable contract",
            "correctness":   "Passes all unit tests",
            "how_to_act":    "Act as a senior Solidity engineer",
        }
        res = self._post(client, payload)
        assert res.status_code == 200
        data = json.loads(res.data)
        assert "MAIN GOAL" in data["prompt"]
        assert "OUTPUT FORMAT" in data["prompt"]
        assert "RULES TO FOLLOW" in data["prompt"]
        assert "OUTPUT GOAL" in data["prompt"]
        assert "CORRECTNESS" in data["prompt"]
        assert "ROLE & BEHAVIOR" in data["prompt"]


# ── Blockchain context injection ───────────────────────────────────────────────

class TestBlockchainContext:
    def _gen(self, client, **kwargs):
        res = client.post(
            "/api/generate",
            data=json.dumps(kwargs),
            content_type="application/json",
        )
        return json.loads(res.data)["prompt"]

    def test_blockchain_keyword_triggers_context(self, client):
        prompt = self._gen(client, main_goal="Write a Solidity ERC-20 token")
        assert "SYSTEM CONTEXT" in prompt

    def test_no_blockchain_keyword_omits_context(self, client):
        prompt = self._gen(client, main_goal="Write a Python script to sort a list")
        assert "SYSTEM CONTEXT" not in prompt

    def test_final_instruction_always_present(self, client):
        prompt = self._gen(client, main_goal="Any task")
        assert "FINAL INSTRUCTION" in prompt


# ── _has_blockchain_context helper ────────────────────────────────────────────

class TestHasBlockchainContext:
    def test_detects_solidity(self):
        assert _has_blockchain_context("write a solidity contract")

    def test_detects_nft(self):
        assert _has_blockchain_context("create an NFT")

    def test_detects_web3_mixed_case(self):
        assert _has_blockchain_context("Using Web3.js")

    def test_no_match_returns_false(self):
        assert not _has_blockchain_context("Hello world")

    def test_empty_string_returns_false(self):
        assert not _has_blockchain_context("")


# ── _assemble_prompt helper ────────────────────────────────────────────────────

class TestAssemblePrompt:
    def test_empty_data_returns_final_instruction_only(self):
        prompt = _assemble_prompt({})
        assert "FINAL INSTRUCTION" in prompt

    def test_sections_appear_in_order(self):
        data = {
            "main_goal":     "goal",
            "how_to_act":    "role",
            "rules":         "rules",
            "output_format": "format",
            "output_goal":   "output",
            "correctness":   "verify",
        }
        prompt = _assemble_prompt(data)
        positions = {
            "MAIN GOAL":            prompt.index("MAIN GOAL"),
            "ROLE & BEHAVIOR":      prompt.index("ROLE & BEHAVIOR"),
            "RULES TO FOLLOW":      prompt.index("RULES TO FOLLOW"),
            "OUTPUT FORMAT":        prompt.index("OUTPUT FORMAT"),
            "OUTPUT GOAL":          prompt.index("OUTPUT GOAL"),
            "CORRECTNESS":          prompt.index("CORRECTNESS"),
            "FINAL INSTRUCTION":    prompt.index("FINAL INSTRUCTION"),
        }
        ordered = sorted(positions, key=lambda k: positions[k])
        assert ordered == [
            "MAIN GOAL", "ROLE & BEHAVIOR", "RULES TO FOLLOW",
            "OUTPUT FORMAT", "OUTPUT GOAL", "CORRECTNESS", "FINAL INSTRUCTION",
        ]

    def test_whitespace_only_fields_are_omitted(self):
        prompt = _assemble_prompt({"main_goal": "   ", "rules": "\t\n"})
        assert "MAIN GOAL" not in prompt
        assert "RULES TO FOLLOW" not in prompt

    def test_blockchain_context_injected_before_main_goal(self):
        prompt = _assemble_prompt({"main_goal": "build an ethereum dapp"})
        ctx_pos = prompt.index("SYSTEM CONTEXT")
        goal_pos = prompt.index("MAIN GOAL")
        assert ctx_pos < goal_pos


# ── 404 handler ────────────────────────────────────────────────────────────────

class TestNotFound:
    def test_unknown_route_returns_404(self, client):
        res = client.get("/nonexistent-route")
        assert res.status_code == 404

    def test_404_returns_json(self, client):
        res = client.get("/nonexistent-route")
        data = json.loads(res.data)
        assert "error" in data
