"""Examples of REAL LLM and REAL API implementations.

These show what YOUR production code looks like — they don't run without
your actual credentials/database. The scaffold ships with MOCKS
(MockLLM, MockColorsAPI, etc.) in llm.py and pipeline.py. When you're
ready to test against real services, write implementations following
the patterns below and swap them in via conftest.py.

See SWAP_GUIDE.md for the full swap instructions.
"""

from __future__ import annotations

from typing import Any


# =====================================================================
# REAL LLM EXAMPLE: AWS Bedrock
# =====================================================================
# This shows what a real LLM client looks like. NOT a working implementation
# (you need aioboto3 + AWS creds). The point is the interface: same two
# async methods as MockLLM, same return shapes.

class BedrockLLM:
    """Real LLM via AWS Bedrock. Drop-in replacement for MockLLM."""

    def __init__(
        self,
        model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0",
        region: str = "us-east-1",
    ) -> None:
        self.model_id = model_id
        self.region = region

    async def first_call(self, prompt: str, scenario: str) -> dict[str, Any]:
        # Stage 1: ask the LLM what API to call
        # Real code:
        #   import aioboto3, json
        #   async with aioboto3.Session().client("bedrock-runtime", ...) as client:
        #       resp = await client.converse(
        #           modelId=self.model_id,
        #           messages=[{"role": "user", "content": [{"text": prompt}]}],
        #           toolConfig={"tools": [_decision_tool_spec]},
        #           inferenceConfig={"temperature": 0},
        #       )
        #   return _extract_tool_input(resp)
        # For demo, return a placeholder. Replace with the real call.
        raise NotImplementedError(
            "Install aioboto3 and replace this with a Bedrock converse call. "
            "See SWAP_GUIDE.md section 1 for the full pattern."
        )

    async def second_call(
        self,
        scenario: str,
        behavior: str,
        api_response: dict | None,
        api_error: str | None,
    ) -> str:
        # Stage 2: ask the LLM to write the user-facing message
        # Same Bedrock call pattern, different system prompt + tools.
        raise NotImplementedError(
            "Replace with a Bedrock converse call returning text. "
            "See SWAP_GUIDE.md section 1."
        )


# =====================================================================
# REAL API EXAMPLE: PostgreSQL via asyncpg
# =====================================================================
# What a real DB-backed API client looks like. NOT a working implementation
# (you need asyncpg + a DB connection). Drop-in replacement for the mocks.

class PostgresColorsAPI:
    """Real colors API via PostgreSQL. Drop-in replacement for MockColorsAPI."""

    name = "colors"

    def __init__(self, pool) -> None:
        # pool = asyncpg.create_pool(dsn="postgresql://...")
        self.pool = pool

    async def call(self, params: dict, behavior: str) -> dict | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT name, hex, rgb FROM colors WHERE name = $1",
                params.get("name"),
            )
            return dict(row) if row else None
        # Real errors (DB down, query timeout, etc.) propagate naturally
        # and are caught by ExecutionLambda as api_error.


class PostgresNumbersAPI:
    """Real numbers API via PostgreSQL. Drop-in replacement for MockNumbersAPI."""

    name = "numbers"

    def __init__(self, pool) -> None:
        self.pool = pool

    async def call(self, params: dict, behavior: str) -> dict | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT n, is_prime, parity FROM numbers WHERE n = $1",
                params.get("n"),
            )
            return dict(row) if row else None


# =====================================================================
# REAL API EXAMPLE: HTTP via httpx
# =====================================================================

class HttpColorsAPI:
    """Real colors API via HTTP. Drop-in replacement for MockColorsAPI."""

    name = "colors"

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def call(self, params: dict, behavior: str) -> dict | None:
        # Real code:
        #   import httpx
        #   async with httpx.AsyncClient(base_url=self.base_url) as http:
        #       r = await http.get(f"/{params['name']}")
        #       if r.status_code == 404:
        #           return None
        #       r.raise_for_status()  # 400/500/etc. propagate as exceptions
        #       return r.json()
        raise NotImplementedError(
            "Install httpx and replace this. See SWAP_GUIDE.md section 2."
        )


# =====================================================================
# FACTORIES: wire into conftest.py
# =====================================================================

def real_llm_factory():
    """Factory returning a real LLM. Swap into conftest.py."""
    return BedrockLLM()


def real_postgres_apis_factory(pool):
    """Factory returning real DB-backed APIs. Swap into conftest.py."""
    return {
        "colors": PostgresColorsAPI(pool),
        "numbers": PostgresNumbersAPI(pool),
        # "shapes": PostgresShapesAPI(pool),
    }


def real_http_apis_factory(base_url: str):
    """Factory returning real HTTP-backed APIs. Swap into conftest.py."""
    return {
        "colors": HttpColorsAPI(base_url),
        # "numbers": HttpNumbersAPI(base_url),
        # "shapes": HttpShapesAPI(base_url),
    }