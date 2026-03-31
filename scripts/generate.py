#!/usr/bin/env python3
"""Gemini API wrapper for infographic generation, analysis, and comparison.

Usage:
    python generate.py generate --prompt "..." --output path.png [--reference ref.png]
    python generate.py analyze  --prompt "..." --image path.png
    python generate.py compare  --prompt "..." --image1 a.png --image2 b.png

    Use --prompt-file instead of --prompt for long prompts.

Environment:
    GOOGLE_API_KEY              Required. Your Gemini API key.
    GEMINI_GENERATION_MODEL     Optional. Default: gemini-3.1-flash-image-preview
    GEMINI_ANALYSIS_MODEL       Optional. Default: gemini-2.0-flash
"""

import argparse
import os
import sys
from pathlib import Path


def get_client():
    """Create a Gemini API client."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    from google import genai

    return genai.Client(api_key=api_key)


def read_prompt(args):
    """Read prompt from --prompt or --prompt-file."""
    if getattr(args, "prompt_file", None):
        return Path(args.prompt_file).read_text().strip()
    return args.prompt


GENERATION_MODELS = [
    "gemini-3.1-flash-image-preview",
    "gemini-3-pro-image-preview",
]


def _generate_once(client, model, contents):
    """Attempt image generation with a single model. Returns image bytes or None."""
    from google.genai import types

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["image", "text"],
        ),
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            return part.inline_data.data

    return None


def cmd_generate(args):
    """Generate an image using Gemini, with automatic model fallback."""
    from google.genai import types
    from google.genai.errors import APIError

    client = get_client()
    prompt = read_prompt(args)

    contents = []

    if args.reference:
        ref_path = Path(args.reference)
        if not ref_path.exists():
            print(f"Error: Reference image not found: {args.reference}", file=sys.stderr)
            sys.exit(1)
        contents.append(
            types.Part.from_bytes(data=ref_path.read_bytes(), mime_type="image/png")
        )

    contents.append(prompt)

    # If user explicitly set a model, use only that model
    env_model = os.environ.get("GEMINI_GENERATION_MODEL")
    models = [env_model] if env_model else GENERATION_MODELS

    last_error = None
    for model in models:
        try:
            print(f"Using model: {model}", file=sys.stderr)
            image_data = _generate_once(client, model, contents)
            if image_data:
                out = Path(args.output)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(image_data)
                print(f"Image saved to: {args.output}")
                return
            last_error = "No image in response"
        except APIError as e:
            print(f"Model {model} failed: {e}", file=sys.stderr)
            last_error = str(e)
            continue

    print(f"Error: All models failed. Last error: {last_error}", file=sys.stderr)
    sys.exit(1)


def cmd_analyze(args):
    """Analyze an image using Gemini vision."""
    from google.genai import types

    client = get_client()
    prompt = read_prompt(args)
    model = os.environ.get("GEMINI_ANALYSIS_MODEL", "gemini-2.0-flash")

    img_path = Path(args.image)
    if not img_path.exists():
        print(f"Error: Image not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(
                data=img_path.read_bytes(), mime_type="image/png"
            ),
            prompt,
        ],
    )

    print(response.text)


def cmd_compare(args):
    """Compare two images using Gemini vision."""
    from google.genai import types

    client = get_client()
    prompt = read_prompt(args)
    model = os.environ.get("GEMINI_ANALYSIS_MODEL", "gemini-2.0-flash")

    for p in [args.image1, args.image2]:
        if not Path(p).exists():
            print(f"Error: Image not found: {p}", file=sys.stderr)
            sys.exit(1)

    response = client.models.generate_content(
        model=model,
        contents=[
            "Image 1 (style anchor):",
            types.Part.from_bytes(
                data=Path(args.image1).read_bytes(), mime_type="image/png"
            ),
            "Image 2 (panel under review):",
            types.Part.from_bytes(
                data=Path(args.image2).read_bytes(), mime_type="image/png"
            ),
            prompt,
        ],
    )

    print(response.text)


def main():
    parser = argparse.ArgumentParser(
        description="Gemini image generation and analysis for infographics"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -- generate --
    gen = subparsers.add_parser("generate", help="Generate an image from a prompt")
    gen_prompt = gen.add_mutually_exclusive_group(required=True)
    gen_prompt.add_argument("--prompt", help="Generation prompt text")
    gen_prompt.add_argument("--prompt-file", help="Path to file containing the prompt")
    gen.add_argument("--output", required=True, help="Output image path")
    gen.add_argument("--reference", help="Reference image for style consistency")

    # -- analyze --
    ana = subparsers.add_parser("analyze", help="Analyze an image with a prompt")
    ana_prompt = ana.add_mutually_exclusive_group(required=True)
    ana_prompt.add_argument("--prompt", help="Analysis prompt text")
    ana_prompt.add_argument("--prompt-file", help="Path to file containing the prompt")
    ana.add_argument("--image", required=True, help="Image path to analyze")

    # -- compare --
    cmp = subparsers.add_parser("compare", help="Compare two images")
    cmp_prompt = cmp.add_mutually_exclusive_group(required=True)
    cmp_prompt.add_argument("--prompt", help="Comparison prompt text")
    cmp_prompt.add_argument("--prompt-file", help="Path to file containing the prompt")
    cmp.add_argument("--image1", required=True, help="First image (style anchor)")
    cmp.add_argument("--image2", required=True, help="Second image (under review)")

    args = parser.parse_args()

    {"generate": cmd_generate, "analyze": cmd_analyze, "compare": cmd_compare}[
        args.command
    ](args)


if __name__ == "__main__":
    main()
