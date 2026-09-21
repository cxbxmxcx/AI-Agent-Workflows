"""Shared runtime configuration for every example in this repository.

Importing this module is enough to make an example talk to a third-party
OpenAI-compatible endpoint (a relay, or a token plan from another vendor)
instead of api.openai.com:

    import agents_config  # noqa: F401

There is no function to call - the settings are applied as a side effect of the
import, before the example creates its client. Every example imports it at the
top of the file.

Everything is driven by environment variables, so an unchanged .env keeps the
original behaviour of talking to api.openai.com.

    OPENAI_API_KEY
        Key issued by your provider. Required either way.

    OPENAI_BASE_URL
        OpenAI-compatible base URL of the provider, for example
        ``https://your-provider.example.com/v1``. Setting it switches on the
        third-party behaviour described below. The OpenAI SDK picks this up on
        its own, so no client has to be built here.

    OPENAI_AGENTS_CHAT_API
        ``1`` (the default once OPENAI_BASE_URL is set) moves the Agents SDK
        onto ``/v1/chat/completions``. The SDK uses ``/v1/responses`` by
        default, which most third-party providers do not implement. Set it to
        ``0`` if your provider does implement the Responses API.

    OPENAI_AGENTS_DISABLE_TRACING
        ``1`` (the default once OPENAI_BASE_URL is set) stops the SDK from
        uploading traces to api.openai.com, where a third-party key would be
        rejected. Set it to ``0`` to keep the OpenAI tracing dashboard.

    AGENT_MODEL
        Overrides the model every agent runs on. Providers rarely serve the
        model names the book uses, so set this to a model your provider does
        serve. When it is not set, each example keeps the model the book used.

        This works on both kinds of agent: ``Agent(model=...)`` sites go
        through ``agents_config.model()``, and the sites that name no model at
        all are covered by exporting AGENT_MODEL as OPENAI_DEFAULT_MODEL, which
        the SDK reads for its own default.

        One caveat from the SDK: on that second path the name is lowercased
        (``get_default_model()`` ends in ``.lower()``), so a mixed-case model
        id such as ``GLM-4-Plus`` reaches the provider as ``glm-4-plus``. Ids
        that are case-sensitive are only passed through untouched on the
        ``model=`` path.

    IMAGE_MODEL / IMAGE_SIZE
        Only used by the image examples (chapter_07/07, chapter_07/08,
        chapter_08/02_app.py and bonus_projects/). IMAGE_MODEL is the image
        model your provider serves, defaulting to ``dall-e-3``; IMAGE_SIZE
        overrides the size the example asks for, because the sizes the book
        uses are gpt-image-1 sizes that other models may reject.

    VISION_MODEL
        Model for the vision call in chapter_07/08, which talks to the provider
        directly rather than through an agent. Falls back to AGENT_MODEL, then
        to the model the book used.

    EMBEDDING_MODEL
        Model for chapter_06/document_query_chromadb.py and
        chapter_06/document_visualizing_embeddings.py. It does not fall back to
        AGENT_MODEL - a chat model is not an embedding model. Changing it means
        rebuilding any ChromaDB collection built with the old one.

    AGENT_TEMPERATURE
        Overrides the temperature in the examples that set one
        (chapter_02/02). Reasoning-style models reject a temperature other
        than their default, so set this to ``1`` if yours is one of them.
"""

import base64
import os
import tempfile
import urllib.request

from dotenv import load_dotenv

load_dotenv()

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or None

AGENT_MODEL = os.getenv("AGENT_MODEL") or None

IMAGE_MODEL = os.getenv("IMAGE_MODEL") or None

IMAGE_SIZE = os.getenv("IMAGE_SIZE") or None

VISION_MODEL = os.getenv("VISION_MODEL") or None

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL") or None

USING_THIRD_PARTY_ENDPOINT = OPENAI_BASE_URL is not None

# The local image tool reports where it put the file by returning a string the
# model can read but cannot misinterpret; save_image() looks for this prefix.
_IMAGE_PATH_PREFIX = "Image saved to "

if AGENT_MODEL:
    # Agent(...) calls that name no model fall back to OPENAI_DEFAULT_MODEL
    # (see agents/models/default_models.py), so this covers those too.
    os.environ["OPENAI_DEFAULT_MODEL"] = AGENT_MODEL


def model(default: str) -> str:
    """Return the model an agent should run on.

    ``AGENT_MODEL`` wins when it is set, so every example can be pointed at a
    provider that serves different model names without editing any of them.
    Otherwise the model the book chose for that example is kept.
    """
    return AGENT_MODEL or default


def vision_model(default: str) -> str:
    """Return the model for a direct vision call.

    VISION_MODEL wins, then AGENT_MODEL, then the model the book used. The
    extra step past :func:`model` is because AGENT_MODEL is chosen for chat
    agents and is not always one that can read images.
    """
    return VISION_MODEL or AGENT_MODEL or default


def embedding_model(default: str) -> str:
    """Return the embedding model to use.

    Deliberately does not fall back to AGENT_MODEL: a chat model cannot
    produce embeddings. Note that changing this invalidates any ChromaDB
    collection built with the previous model, because the vector widths differ.
    """
    return EMBEDDING_MODEL or default


def temperature(default: float) -> float:
    """Return the temperature an example should set.

    AGENT_TEMPERATURE wins when it is set. Reasoning-style models reject a
    temperature other than their own default, so being able to override this
    is what lets chapter_02/02 run on one of them.
    """
    value = os.getenv("AGENT_TEMPERATURE")
    return float(value) if value else default


def _flag(name: str, default: bool) -> bool:
    """Read a boolean environment variable, falling back to ``default``."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _ensure_parent(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _write_file(path: str, data: bytes) -> None:
    _ensure_parent(path)
    with open(path, "wb") as handle:
        handle.write(data)


def _generate_and_store(prompt: str, size: str, model: str) -> str:
    """Ask the provider for one image, write it to a temp file, return its path."""
    from openai import OpenAI

    client = OpenAI()
    # response_format is deliberately not sent: some providers reject it, and
    # the response tells us which of b64_json/url we got anyway.
    response = client.images.generate(
        model=model,
        prompt=prompt,
        size=size,
        n=1,
    )
    image = response.data[0]
    if image.b64_json:
        raw = base64.b64decode(image.b64_json)
    else:
        with urllib.request.urlopen(image.url) as download:  # type: ignore[arg-type]
            raw = download.read()

    handle, path = tempfile.mkstemp(suffix=".png", prefix="agents_image_")
    with os.fdopen(handle, "wb") as file:
        file.write(raw)
    return path


def image_tool(
    *,
    size: str = "1536x1024",
    quality: str = "high",
    model: str = "gpt-image-1",
):
    """Return the image generation tool an example should hand to its agent.

    Against api.openai.com this is the book's server-side ``ImageGenerationTool``
    and the examples read the image back out of the run items. Against a
    third-party endpoint it is a local ``@function_tool`` that calls
    ``POST /images/generations`` and writes the result to a temp file, because
    hosting the tool is something only OpenAI does.

    Either way, read the image back with :func:`save_image`, which handles both.
    """
    if not USING_THIRD_PARTY_ENDPOINT:
        from agents import ImageGenerationTool

        return ImageGenerationTool(
            tool_config={
                "type": "image_generation",
                "quality": quality,
                "model": model,
                "size": size,
            }
        )

    from agents import function_tool

    resolved_model = IMAGE_MODEL or "dall-e-3"
    resolved_size = IMAGE_SIZE or size

    @function_tool(name_override="generate_image")
    def generate_image(prompt: str) -> str:
        """Generate a single image from a text prompt.

        Args:
            prompt: The full prompt describing the image to generate.
        """
        path = _generate_and_store(prompt, resolved_size, resolved_model)
        return f"{_IMAGE_PATH_PREFIX}{path}"

    return generate_image


def save_image(result, path: str) -> bytes | None:
    """Write the image produced by a run to ``path`` and return its bytes.

    The image comes from the run's items with the book's hosted tool, and from
    the temp file the local tool wrote when a third-party endpoint is in use.
    Returns ``None`` when the run produced no image.

    ``path`` is not used to pick the image - it is where you want the result to
    end up, so the examples can keep naming their files ``image3.png`` and the
    like while the tool stays free to write wherever it wants.
    """
    for item in getattr(result, "new_items", None) or []:
        raw_item = getattr(item, "raw_item", None)

        # Third-party: the local tool wrote a temp file and returned its path.
        output = getattr(item, "output", None)
        if isinstance(output, str) and output.startswith(_IMAGE_PATH_PREFIX):
            source = output[len(_IMAGE_PATH_PREFIX):]
            with open(source, "rb") as file:
                raw = file.read()
            os.remove(source)
            _write_file(path, raw)
            return raw

        # api.openai.com: the hosted tool returns the image inline.
        if (
            getattr(item, "type", None) == "tool_call_item"
            and getattr(raw_item, "type", None) == "image_generation_call"
            and (encoded := getattr(raw_item, "result", None))
        ):
            raw = base64.b64decode(encoded)
            _write_file(path, raw)
            return raw

    return None


def vision_completion(image_path: str, prompt: str, model: str) -> str:
    """Ask a vision model what is in the image at ``image_path``.

    Against api.openai.com this uses the Responses API, which is what the book
    used. Against a third-party endpoint it uses ``/v1/chat/completions``,
    because providers rarely implement ``/v1/responses``.
    """
    from openai import OpenAI

    with open(image_path, "rb") as file:
        encoded = base64.b64encode(file.read()).decode("utf-8")

    client = OpenAI()

    if USING_THIRD_PARTY_ENDPOINT:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                        },
                    ],
                }
            ],
        )
        return response.choices[0].message.content or ""

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{encoded}",
                    },
                ],
            }
        ],
    )
    return response.output_text


def _configure_agents_sdk() -> None:
    """Point the Agents SDK at the configured provider."""
    from agents import set_default_openai_api, set_tracing_disabled

    if USING_THIRD_PARTY_ENDPOINT and _flag("OPENAI_AGENTS_CHAT_API", True):
        set_default_openai_api("chat_completions")

    if _flag("OPENAI_AGENTS_DISABLE_TRACING", USING_THIRD_PARTY_ENDPOINT):
        set_tracing_disabled(True)


_configure_agents_sdk()
