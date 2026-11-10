"""Configuration tests: environments, grants, env-file precedence, token path."""

from __future__ import annotations

from pathlib import Path

import pytest

from pingen_mcp_server.config import (
    ConfigError,
    default_token_file,
    load_config,
    parse_env_file,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_production_is_the_default():
    cfg = load_config({})
    assert cfg.environment == "production"
    assert cfg.api_base_url == "https://api.pingen.com"
    assert cfg.identity_base_url == "https://identity.pingen.com"
    assert cfg.grant_type == "client_credentials"


def test_staging_selects_documented_hosts():
    cfg = load_config({"PINGEN_ENVIRONMENT": "staging"})
    assert cfg.api_base_url == "https://api-staging.pingen.com"
    assert cfg.identity_base_url == "https://identity-staging.pingen.com"


def test_base_url_overrides_win():
    cfg = load_config(
        {
            "PINGEN_ENVIRONMENT": "staging",
            "PINGEN_API_BASE_URL": "http://127.0.0.1:9/",
            "PINGEN_IDENTITY_BASE_URL": "http://127.0.0.1:9/",
        }
    )
    assert cfg.api_base_url == "http://127.0.0.1:9"
    assert cfg.identity_base_url == "http://127.0.0.1:9"


def test_invalid_environment_fails_fast_naming_the_variable():
    with pytest.raises(ConfigError) as exc:
        load_config({"PINGEN_ENVIRONMENT": "api.pingen-staging.com"})
    assert "PINGEN_ENVIRONMENT" in str(exc.value)
    assert "staging" in str(exc.value)


def test_invalid_grant_fails_fast_naming_the_variable():
    with pytest.raises(ConfigError) as exc:
        load_config({"PINGEN_GRANT_TYPE": "password"})
    assert "PINGEN_GRANT_TYPE" in str(exc.value)
    assert "client_credentials" in str(exc.value)


def test_env_file_values_used_when_env_unset(tmp_path: Path):
    env_file = tmp_path / "credentials.env"
    env_file.write_text(
        "# comment\nPINGEN_CLIENT_ID=from-file\nPINGEN_CLIENT_SECRET='quoted'\n",
        encoding="utf-8",
    )
    cfg = load_config({"PINGEN_ENV_FILE": str(env_file)})
    assert cfg.client_id == "from-file"
    assert cfg.client_secret == "quoted"
    assert cfg.env_file == env_file


def test_process_env_beats_env_file(tmp_path: Path):
    env_file = tmp_path / "credentials.env"
    env_file.write_text(
        "PINGEN_CLIENT_ID=from-file\nPINGEN_CLIENT_SECRET=from-file\n",
        encoding="utf-8",
    )
    cfg = load_config(
        {"PINGEN_ENV_FILE": str(env_file), "PINGEN_CLIENT_ID": "from-env"}
    )
    assert cfg.client_id == "from-env"
    assert cfg.client_secret == "from-file"


def test_missing_env_file_fails_fast(tmp_path: Path):
    with pytest.raises(ConfigError) as exc:
        load_config({"PINGEN_ENV_FILE": str(tmp_path / "absent.env")})
    assert "PINGEN_ENV_FILE" in str(exc.value)


def test_parse_env_file_handles_quotes_and_comments(tmp_path: Path):
    path = tmp_path / "x.env"
    path.write_text(
        'A=1\n# B=2\nC="has spaces"\nD-no-equals-ignored\n', encoding="utf-8"
    )
    assert parse_env_file(path) == {"A": "1", "C": "has spaces"}


def test_default_token_file_is_outside_the_repo():
    token_file = default_token_file()
    assert token_file.name == "tokens.json"
    resolved = token_file.resolve()
    assert REPO_ROOT.resolve() not in resolved.parents


def test_scopes_split_on_whitespace():
    cfg = load_config({"PINGEN_SCOPES": "letter batch webhook"})
    assert cfg.scopes == ("letter", "batch", "webhook")
