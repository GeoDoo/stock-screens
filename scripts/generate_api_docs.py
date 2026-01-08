#!/usr/bin/env python3
"""
Generate API documentation from FastAPI's OpenAPI schema.

This ensures API.md is always in sync with actual endpoints.
Run: python scripts/generate_api_docs.py
"""

import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from fastapi.openapi.utils import get_openapi
from app.main import app


def get_type_string(schema: dict) -> str:
    """Convert JSON schema type to readable string."""
    if "type" in schema:
        return schema["type"]
    if "$ref" in schema:
        return schema["$ref"].split("/")[-1]
    if "anyOf" in schema:
        types = [get_type_string(s) for s in schema["anyOf"]]
        return " | ".join(types)
    return "any"


def format_parameters(parameters: list) -> str:
    """Format query/path parameters as markdown table."""
    if not parameters:
        return ""
    
    lines = [
        "",
        "**Parameters**",
        "",
        "| Name | Type | Required | Description |",
        "|------|------|----------|-------------|",
    ]
    
    for param in parameters:
        name = param.get("name", "")
        schema = param.get("schema", {})
        param_type = get_type_string(schema)
        required = "Yes" if param.get("required", False) else "No"
        description = param.get("description", "")
        default = schema.get("default")
        if default is not None:
            description += f" (default: `{default}`)"
        
        lines.append(f"| `{name}` | {param_type} | {required} | {description} |")
    
    return "\n".join(lines)


def format_request_body(request_body: dict, schemas: dict) -> str:
    """Format request body as markdown."""
    if not request_body:
        return ""
    
    content = request_body.get("content", {})
    json_content = content.get("application/json", {})
    schema = json_content.get("schema", {})
    
    if "$ref" in schema:
        ref_name = schema["$ref"].split("/")[-1]
        schema = schemas.get(ref_name, {})
    
    lines = [
        "",
        "**Request Body**",
        "",
        "```json",
        json.dumps(generate_example(schema, schemas), indent=2),
        "```",
    ]
    
    # Add field descriptions
    properties = schema.get("properties", {})
    required_fields = schema.get("required", [])
    
    if properties:
        lines.extend([
            "",
            "| Field | Type | Required | Description |",
            "|-------|------|----------|-------------|",
        ])
        
        for name, prop in properties.items():
            prop_type = get_type_string(prop)
            required = "Yes" if name in required_fields else "No"
            description = prop.get("description", "")
            lines.append(f"| `{name}` | {prop_type} | {required} | {description} |")
    
    return "\n".join(lines)


def generate_example(schema: dict, schemas: dict) -> dict:
    """Generate example JSON from schema."""
    if "$ref" in schema:
        ref_name = schema["$ref"].split("/")[-1]
        schema = schemas.get(ref_name, {})
    
    if schema.get("type") == "object":
        result = {}
        for name, prop in schema.get("properties", {}).items():
            result[name] = generate_example(prop, schemas)
        return result
    
    if schema.get("type") == "array":
        items = schema.get("items", {})
        return [generate_example(items, schemas)]
    
    if schema.get("type") == "string":
        if schema.get("format") == "date-time":
            return "2024-01-15T10:30:00Z"
        return schema.get("example", "string")
    
    if schema.get("type") == "number":
        return schema.get("example", 0.0)
    
    if schema.get("type") == "integer":
        return schema.get("example", 0)
    
    if schema.get("type") == "boolean":
        return schema.get("example", True)
    
    if "anyOf" in schema:
        # Return first non-null type
        for s in schema["anyOf"]:
            if s.get("type") != "null":
                return generate_example(s, schemas)
        return None
    
    return None


def format_response(responses: dict, schemas: dict) -> str:
    """Format response as markdown."""
    success_response = responses.get("200") or responses.get("201")
    if not success_response:
        return ""
    
    content = success_response.get("content", {})
    json_content = content.get("application/json", {})
    schema = json_content.get("schema", {})
    
    if not schema:
        return ""
    
    example = generate_example(schema, schemas)
    
    lines = [
        "",
        "**Response**",
        "",
        "```json",
        json.dumps(example, indent=2),
        "```",
    ]
    
    return "\n".join(lines)


def generate_docs() -> str:
    """Generate full API documentation."""
    openapi = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    
    schemas = openapi.get("components", {}).get("schemas", {})
    paths = openapi.get("paths", {})
    
    lines = [
        "# API Reference",
        "",
        "> **Auto-generated** from FastAPI OpenAPI schema.",
        "> ",
        "> Do not edit manually. Run `python scripts/generate_api_docs.py` to regenerate.",
        "",
        "Base URL: `http://localhost:8000`",
        "",
    ]
    
    # Group endpoints by tag
    tagged_endpoints = {}
    for path, methods in paths.items():
        for method, details in methods.items():
            if method in ("get", "post", "put", "delete", "patch"):
                tags = details.get("tags", ["Other"])
                for tag in tags:
                    if tag not in tagged_endpoints:
                        tagged_endpoints[tag] = []
                    tagged_endpoints[tag].append((path, method, details))
    
    # Generate docs for each tag
    for tag in sorted(tagged_endpoints.keys()):
        lines.append(f"## {tag}")
        lines.append("")
        
        for path, method, details in tagged_endpoints[tag]:
            summary = details.get("summary", path)
            description = details.get("description", "")
            
            lines.append(f"### {summary}")
            lines.append("")
            
            if description:
                lines.append(description)
                lines.append("")
            
            lines.append(f"```")
            lines.append(f"{method.upper()} {path}")
            lines.append(f"```")
            
            # Parameters
            params = details.get("parameters", [])
            lines.append(format_parameters(params))
            
            # Request body
            request_body = details.get("requestBody")
            lines.append(format_request_body(request_body, schemas))
            
            # Response
            responses = details.get("responses", {})
            lines.append(format_response(responses, schemas))
            
            lines.append("")
            lines.append("---")
            lines.append("")
    
    return "\n".join(lines)


def main():
    docs = generate_docs()
    
    # Output directly to API.md (single source of truth)
    output_path = Path(__file__).parent.parent / "docs" / "API.md"
    output_path.write_text(docs)
    
    print(f"✓ Generated {output_path}")
    print(f"  {len(docs.splitlines())} lines")
    
    # Clean up old generated file if it exists
    old_generated = Path(__file__).parent.parent / "docs" / "API_GENERATED.md"
    if old_generated.exists():
        old_generated.unlink()
        print(f"✓ Removed old {old_generated.name}")


if __name__ == "__main__":
    main()
