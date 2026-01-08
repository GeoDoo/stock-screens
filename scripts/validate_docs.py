#!/usr/bin/env python3
"""
Validate documentation is up-to-date and accurate.

Checks:
1. API endpoints in docs match actual FastAPI routes
2. Code examples are syntactically valid
3. Internal links resolve
4. Required sections exist

Run: python scripts/validate_docs.py
"""

import re
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

DOCS_DIR = Path(__file__).parent.parent / "docs"
ERRORS = []
WARNINGS = []


def error(msg: str):
    ERRORS.append(f"ERROR: {msg}")


def warn(msg: str):
    WARNINGS.append(f"WARNING: {msg}")


def check_api_endpoints():
    """Verify documented endpoints exist in FastAPI app."""
    from app.main import app
    
    # Get actual routes
    actual_routes = set()
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            for method in route.methods:
                if method != "HEAD":
                    actual_routes.add((method, route.path))
    
    # Parse documented endpoints from API.md
    api_md = DOCS_DIR / "API.md"
    if not api_md.exists():
        error("docs/API.md not found")
        return
    
    content = api_md.read_text()
    
    # Find all documented endpoints (```\nGET /api/...\n```)
    pattern = r"```\n(GET|POST|PUT|DELETE|PATCH) (/api/[^\n]+)\n```"
    documented = set()
    
    for match in re.finditer(pattern, content):
        method, path = match.groups()
        # Normalize path parameters
        normalized = re.sub(r"\{[^}]+\}", "{param}", path)
        documented.add((method, normalized))
    
    # Normalize actual routes
    actual_normalized = set()
    for method, path in actual_routes:
        normalized = re.sub(r"\{[^}]+\}", "{param}", path)
        actual_normalized.add((method, normalized))
    
    # Check for undocumented endpoints
    undocumented = actual_normalized - documented
    api_endpoints = {(m, p) for m, p in undocumented if p.startswith("/api/")}
    
    for method, path in sorted(api_endpoints):
        warn(f"Undocumented endpoint: {method} {path}")
    
    # Check for documented but non-existent endpoints
    nonexistent = documented - actual_normalized
    for method, path in sorted(nonexistent):
        error(f"Documented endpoint does not exist: {method} {path}")


def check_internal_links():
    """Verify internal markdown links resolve."""
    for md_file in DOCS_DIR.glob("*.md"):
        content = md_file.read_text()
        
        # Find relative links
        pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        for match in re.finditer(pattern, content):
            text, link = match.groups()
            
            # Skip external links
            if link.startswith("http"):
                continue
            
            # Skip anchor links
            if link.startswith("#"):
                continue
            
            # Check file exists
            target = (md_file.parent / link).resolve()
            if not target.exists():
                error(f"{md_file.name}: Broken link [{text}]({link})")


def check_required_sections():
    """Verify required documentation sections exist."""
    required = {
        "README.md": ["Quick Start", "Features", "Architecture"],
        "API.md": ["Stock Analysis", "Investment Memos"],
        "ARCHITECTURE.md": ["Overview", "Data Flow", "Database Schema"],
        "DEVELOPMENT.md": ["Prerequisites", "Testing", "Code Style"],
        "DCF_MODEL.md": ["Free Cash Flow", "WACC", "Terminal Value"],
    }
    
    for filename, sections in required.items():
        filepath = DOCS_DIR.parent / filename if filename == "README.md" else DOCS_DIR / filename
        
        if not filepath.exists():
            error(f"{filename} not found")
            continue
        
        content = filepath.read_text()
        
        for section in sections:
            # Check for ## Section or # Section
            pattern = rf"#+ {re.escape(section)}"
            if not re.search(pattern, content, re.IGNORECASE):
                warn(f"{filename}: Missing section '{section}'")


def check_code_blocks():
    """Validate code blocks are syntactically correct."""
    import ast
    import json
    import textwrap
    
    for md_file in DOCS_DIR.glob("*.md"):
        content = md_file.read_text()
        
        # Find Python code blocks
        python_pattern = r"```python\n(.*?)```"
        for i, match in enumerate(re.finditer(python_pattern, content, re.DOTALL)):
            code = match.group(1)
            # Dedent to handle code in markdown lists
            code = textwrap.dedent(code)
            try:
                ast.parse(code)
            except SyntaxError as e:
                warn(f"{md_file.name}: Invalid Python in block {i+1}: {e.msg}")
        
        # Find JSON code blocks
        json_pattern = r"```json\n(.*?)```"
        for i, match in enumerate(re.finditer(json_pattern, content, re.DOTALL)):
            code = match.group(1)
            try:
                json.loads(code)
            except json.JSONDecodeError as e:
                warn(f"{md_file.name}: Invalid JSON in block {i+1}: {e.msg}")


def check_glossary_sync():
    """Verify glossary.ts terms are documented."""
    glossary_ts = Path(__file__).parent.parent / "frontend" / "src" / "glossary.ts"
    
    if not glossary_ts.exists():
        warn("glossary.ts not found")
        return
    
    content = glossary_ts.read_text()
    
    # Extract term IDs
    pattern = r"id:\s*['\"]([^'\"]+)['\"]"
    glossary_terms = set(re.findall(pattern, content))
    
    # Check DCF_MODEL.md references key terms
    dcf_md = DOCS_DIR / "DCF_MODEL.md"
    if dcf_md.exists():
        dcf_content = dcf_md.read_text().lower()
        
        key_terms = ["fcf", "wacc", "nopat", "ebit", "terminal-value", "capex"]
        for term in key_terms:
            if term not in dcf_content and term.replace("-", " ") not in dcf_content:
                warn(f"DCF_MODEL.md may be missing explanation of '{term}'")


def main():
    print("Validating documentation...\n")
    
    check_api_endpoints()
    check_internal_links()
    check_required_sections()
    check_code_blocks()
    check_glossary_sync()
    
    # Print results
    for warning in WARNINGS:
        print(f"⚠️  {warning}")
    
    for err in ERRORS:
        print(f"❌ {err}")
    
    print()
    
    if ERRORS:
        print(f"Found {len(ERRORS)} error(s) and {len(WARNINGS)} warning(s)")
        sys.exit(1)
    elif WARNINGS:
        print(f"Found {len(WARNINGS)} warning(s), no errors")
        sys.exit(0)
    else:
        print("✅ All documentation checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
