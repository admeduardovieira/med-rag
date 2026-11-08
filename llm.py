import warnings
import os
from types import SimpleNamespace as sn


from litellm import acompletion, aembedding
import litellm
import random
from logging_setup import setup_logging, get_logger
import asyncio
import re
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")


load_dotenv()

litellm.enable_cache(
    type="disk",
    supported_call_types=["aembedding"],
    disk_cache_dir="llm_cache",
)

RETRY_LIMIT = 3
MAX_TOKENS = 200
TIMEOUT = 30

logger = get_logger(__name__)


def extract_sql_from_response(result):
    """Extract SQL query from model response, handling reasoning output."""
    if not result:
        return None

    # Method 1: Look for SQL code blocks (```sql)
    if "```sql" in result:
        pattern = r"```sql\s*(.*?)(?:```|$)"
        matches = re.findall(pattern, result, re.DOTALL | re.IGNORECASE)
        if matches:
            # Take the last SQL block (most likely the final answer)
            sql = matches[-1].strip()
            if sql:
                return sql

    # Method 2: Look for generic code blocks (```)
    if "```" in result:
        pattern = r"```\s*(.*?)(?:```|$)"
        matches = re.findall(pattern, result, re.DOTALL)
        if matches:
            # Take the last code block that looks like SQL
            for match in reversed(matches):
                sql = match.strip()
                if sql and (
                    sql.upper().startswith(
                        ("SELECT", "WITH", "INSERT", "UPDATE", "DELETE")
                    )
                ):
                    return sql

    # Method 3: Look for SQL patterns in reasoning text
    # Find SELECT statements that end with semicolon or are at end of text
    sql_pattern = r"(SELECT\s+(?:(?!SELECT\s+).)*?)(?:;|$)"
    matches = re.findall(sql_pattern, result, re.DOTALL | re.IGNORECASE)
    if matches:
        # Take the last/longest SQL statement
        sql = matches[-1].strip()
        if sql and len(sql) > 20:  # Basic sanity check
            return sql

    # Method 4: Extract anything that looks like a complete SQL query
    # Look for patterns like "So we need" followed by SQL or just bare SQL
    reasoning_sql_pattern = r"(?:so|therefore|thus|answer:|output:|query:)\s*(?:we need)?\s*(SELECT\s+(?:(?!SELECT\s+).)*?)(?:;|\.|$|We need|So we|The answer)"
    matches = re.findall(reasoning_sql_pattern, result, re.DOTALL | re.IGNORECASE)
    if matches:
        sql = matches[-1].strip()
        if sql and len(sql) > 15:
            return sql

    return None


# litellm._turn_on_debug()

models = {
    # Deepseek models
    "deepseek-v3": sn(
        model="fireworks_ai/accounts/fireworks/models/deepseek-v3",
        meta=sn(
            price_in=0.90,
            price_out=0.90,
        ),
    ),
    "deepseek-v3.1": sn(
        model="fireworks_ai/accounts/fireworks/models/deepseek-v3p1",
        meta=sn(
            price_in=0.56,
            price_out=1.68,
        ),
    ),
    # Llama 3.3
    "llama3.3-70b": sn(
        model="fireworks_ai/accounts/fireworks/models/llama-v3p3-70b-instruct",
        meta=sn(
            price_in=0.90,
            price_out=0.90,
        ),
    ),
    # Open AI models
    "gpt-4o": sn(
        model="gpt-4o",
        meta=sn(
            price_in=2.50,
            price_out=10.00,
        ),
    ),
    "gpt-5": sn(
        model="gpt-5-chat-latest",
        meta=sn(
            price_in=1.25,
            price_out=10.00,
        ),
    ),
    "gpt-oss-20b": sn(
        model="groq/openai/gpt-oss-20b",
        meta=sn(
            price_in=0.10,
            price_out=0.50,
        ),
    ),
    "qwen2p5-vl-32b-instruct": sn(
        model="fireworks_ai/accounts/fireworks/models/qwen2p5-vl-32b-instruct",
        meta=sn(
            price_in=0.90,
            price_out=0.90,
        ),
    ),
    "mixtral-8x22b-instruct": sn(
        model="fireworks_ai/accounts/fireworks/models/mixtral-8x22b-instruct",
        meta=sn(
            price_in=1.2,
            price_out=1.2,
        ),
    ),
    "bio-mistral-7b": sn(
        model="fireworks_ai/accounts/lukablaskovic2000-738cce/deployedModels/bio-mistral-7b-yvistc6t",
        meta=sn(
            price_in=0.5,
            price_out=0.5,
            has_system=False,
        ),
    ),
}


def parse_file(filename):
    parsed_data = {}
    current_section = None

    with open(filename, "r") as file:
        for line in file:
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1]
                parsed_data[current_section] = line + "\n"
            elif current_section:
                parsed_data[current_section] += line + "\n"
            else:
                raise ValueError(
                    "File format is invalid. Ensure sections are properly defined."
                )

    parsed_data = {k: v.strip() for k, v in parsed_data.items()}
    return parsed_data


try:
    prompts = parse_file("prompts/system.md")
except FileNotFoundError:
    logger.warning("prompts/system.md not found; using empty system prompts")
    prompts = {}
except Exception as e:
    logger.warning("Failed to load prompts/system.md: %s", type(e).__name__)
    prompts = {}


def get_models(include_large=False, models_filter=None):
    return [
        key
        for key, value in models.items()
        if (not hasattr(value, "large") or not value.large)
        and (models_filter is None or key in models_filter)
    ]


def normalize(x):
    if x:
        return re.sub(r"\s+", " ", x).strip()
    return x


async def ai_embeddings(inputs=[]):
    if len(inputs) == 0:
        return {"data": []}
    response = await aembedding(
        model="text-embedding-3-small",
        input=inputs,
        dimensions=512,
        caching=True,
    )
    return response


async def ai_query(
    message=None,
    system=None,
    model="llama3.2",
    max_tokens=MAX_TOKENS,
    prefix=None,
    exclude_system_sections={},
    sql=True,
):
    if system is None:
        system = "".join(
            content
            for section, content in prompts.items()
            if section not in exclude_system_sections
        )

        # Add instruction to avoid chain-of-thought / thinking outputs
        if model in ["gpt-5", "gpt-oss-20b", "deepseek-v3.1"]:
            system += "\n\n**IMPORTANT**: Do not include chain-of-thought or any hidden 'thinking'. Output only the final SQL query."

    model_spec = models.get(model)

    if hasattr(model_spec, "meta") and hasattr(model_spec.meta, "extra_tokens"):
        max_tokens += model_spec.meta.extra_tokens

    messages = []

    if system is not None:
        if (
            hasattr(model_spec, "meta")
            and hasattr(model_spec.meta, "has_system")
            and not model_spec.meta.has_system
        ):
            message = f"Context: {system} \n\n" + message
        else:
            messages.append({"content": system, "role": "system"})

    if message is not None:
        messages.append({"content": message, "role": "user"})

    if prefix:
        messages.append({"content": prefix, "role": "system"})

    params = {
        **{k: v for k, v in model_spec.__dict__.items() if k not in {"meta"}},
        "messages": messages,
        "max_tokens": max_tokens,
        "timeout": TIMEOUT,
    }

    # GPT-5 models: Remove any special parameter handling for now
    # The reasoning parameter is not supported by GPT-5 API
    if model == "gpt-5":
        pass  # Use standard parameters

    # Help LiteLLM map provider/endpoints for Fireworks-hosted models
    if isinstance(model_spec, sn) and hasattr(model_spec, "model"):
        model_id = getattr(model_spec, "model", "")
        if isinstance(model_id, str) and model_id.startswith("fireworks_ai/"):
            params["custom_llm_provider"] = "fireworks_ai"
            params["api_base"] = os.getenv(
                "FIREWORKS_API_BASE", "https://api.fireworks.ai/inference/v1"
            )

    # Set temperature and reasoning parameters
    if model == "gpt-5":
        params["temperature"] = 1
        # GPT-5 uses a lot of reasoning tokens, increase max_tokens significantly
        params["max_tokens"] = max_tokens * 4  # Quadruple for GPT-5
        # Note: GPT-5 doesn't support reasoning effort control yet
    elif model == "gpt-oss-20b":
        params["temperature"] = 0
        # Hide reasoning per Groq docs for GPT-OSS models
        # https://console.groq.com/docs/reasoning
        params["include_reasoning"] = False
        # Keep reasoning effort minimal if used internally
        params["reasoning_effort"] = "low"
        # Do not boost max_tokens for reasoning
        params["max_tokens"] = max_tokens
    elif model == "deepseek-v3.1":
        params["temperature"] = 0
        # Keep token budget tight and rely on prompt to avoid CoT
        params["max_tokens"] = max_tokens
        params["response_format"] = {"type": "text"}
    else:
        params["temperature"] = 0

    # Optional per-model API key override
    # - Set models[<name>].meta.api_key_env to the env var name holding the key
    # - Or set models[<name>].meta.api_key directly (not recommended)
    api_key_override = None
    if hasattr(model_spec, "meta"):
        if hasattr(model_spec.meta, "api_key_env"):
            api_key_override = os.getenv(model_spec.meta.api_key_env)
        if not api_key_override and hasattr(model_spec.meta, "api_key"):
            api_key_override = model_spec.meta.api_key

    if api_key_override:
        params["api_key"] = api_key_override

    response = None
    for retry_idx in range(RETRY_LIMIT):
        try:
            response = await acompletion(**params)
            break
        except Exception as e:
            logger.error("Model %s request failed: %s", model, type(e).__name__)
            await asyncio.sleep((1.5 + retry_idx) ** 2 + random.uniform(0.5, 3))

    if response and len(response.choices):
        message = response.choices[0].message
        result = message.content

        # Handle models that put responses in reasoning field (e.g., GPT-OSS-20B)
        if not result and hasattr(message, "reasoning") and message.reasoning:
            result = message.reasoning

        if sql:
            # Enhanced SQL extraction to handle reasoning output
            sql_query = extract_sql_from_response(result)
            if sql_query:
                result = sql_query

        if prefix:
            result = prefix + result

        response.model = model

        if sql:
            return sn(
                sql=normalize(result),
                meta=response,
            )
        else:
            return sn(
                text=normalize(result),
                meta=response,
            )

    if sql:
        return sn(
            sql="--timeout--",
            meta=sn(
                model=model,
                usage=sn(
                    prompt_tokens=0,
                    completion_tokens=0,
                ),
            ),
        )
    else:
        return sn(
            text="--timeout--",
            meta=sn(
                model="none",
                usage=sn(
                    prompt_tokens=0,
                    completion_tokens=0,
                ),
            ),
        )


if __name__ == "__main__":

    # Initialize logging with default INFO level and colored output
    setup_logging()

    async def test_models():
        logger.info("Testing API keys for all models...")

        test_query = "Say OK"
        test_system = "You are a helpful assistant."

        tested_models = list(models.keys())
        successful_models = []
        failed_models = []

        try:
            for model_name in tested_models:
                logger.warning("%s", "*" * 30)
                logger.info("Testing %s...", model_name)
                try:
                    result = await ai_query(
                        message=test_query,
                        system=test_system,
                        model=model_name,
                        max_tokens=100,
                        sql=False,
                    )

                    if (
                        result.text
                        and result.text != "--timeout--"
                        and result.text.strip()
                    ):
                        logger.info(
                            "Testing %s: SUCCESS - Response: %s",
                            model_name,
                            result.text[:50] + ("..." if len(result.text) > 50 else ""),
                        )
                        successful_models.append(model_name)
                    else:
                        logger.error(
                            "Testing %s: FAILED - Timeout or empty response (got: '%s')",
                            model_name,
                            result.text if result.text else "None",
                        )
                        failed_models.append(model_name)

                except Exception as e:
                    logger.error("Testing %s: FAILED - Error: %s", model_name, str(e))
                    failed_models.append(model_name)
        finally:
            total_count = len(tested_models)
            success_count = len(successful_models)

            logger.info("API key testing complete.")
            logger.warning("Tested models: %s", ", ".join(tested_models))
            logger.warning("Worked: %d/%d", success_count, total_count)
            logger.warning(
                "Successful models (%d): %s",
                len(successful_models),
                ", ".join(successful_models) if successful_models else "None",
            )
            logger.warning(
                "Failed models (%d): %s",
                len(failed_models),
                ", ".join(failed_models) if failed_models else "None",
            )

    # Run the async test
    asyncio.run(test_models())

    logger.debug("Prompts: %s", prompts)
