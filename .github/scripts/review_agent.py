#!/usr/bin/env python3
"""
Python Code Review Agent for GitHub Actions.
Driven by the python-code-reviewer skill guidelines.
"""
import os
import subprocess
import sys
from pathlib import Path
from google import genai
from google.genai import types

def run_cmd(cmd: str) -> str:
    """Run shell command and return stdout."""
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return res.stdout.strip()

def load_skill_instructions() -> str:
    """Load python-code-reviewer skill instructions if present, or fallback to core prompt."""
    skill_paths = [
        Path(".gemini/skills/python-code-reviewer/SKILL.md"),
        Path("skills/python-code-reviewer/SKILL.md"),
    ]
    for path in skill_paths:
        if path.exists():
            return path.read_text(encoding="utf-8")

    return """
You are an expert Python code reviewer with deep expertise in Python idioms, PEP 8, typing, asyncio concurrency, performance, security, and testing.
Enforce Python Golden Rules:
1. Correctness & Type Safety: Enforce strict type hints (typing/mypy), avoid Any abuse, use Pydantic/dataclasses.
2. Explicit is better than implicit: No wildcard imports, clear naming.
3. No bare exceptions: Catch specific exceptions, chain with 'raise ... from err'.
4. Mandatory testing: Minimum 80% test coverage, parameterized pytest cases.
5. No blocking calls in async: Never use time.sleep or synchronous requests in async def; use httpx.AsyncClient or asyncio.sleep.
6. Bounded concurrency: Guard asyncio.gather with asyncio.Semaphore.
7. Resource management: Use context managers ('with' / 'async with') for files, connections, and sessions.
8. Security by default: Prevent SQL/command injection, forbid shell=True in subprocess, no untrusted pickle.loads.
9. Linter & Formatter Cleanliness: Ruff/Black/Flake8/Mypy errors are build failures.
10. No AI Attribution: Never include AI references or badges.
"""

def main():
    base_ref = os.getenv("BASE_REF", "main")
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("Gemini_key") or os.getenv("GEMINI_KEY")

    if not api_key:
        print("Error: GEMINI_API_KEY / Gemini_key secret not found in environment.")
        sys.exit(1)

    # 1. Compute git diff for Python files and configs
    diff = run_cmd(f"git diff origin/{base_ref}...HEAD -- '*.py' 'requirements.txt' 'pyproject.toml'")
    if not diff:
        print("No Python changes detected in PR diff.")
        sys.exit(0)

    # 2. Gather Phase 1 Automated Validation results if available
    phase1_report = ""
    report_file = Path("phase1_report.txt")
    if report_file.exists():
        phase1_report = report_file.read_text(encoding="utf-8")

    system_instruction = f"""
{load_skill_instructions()}

CRITICAL OUTPUT REQUIREMENT:
Generate your review strictly in GitHub Flavored Markdown adhering to the <review_summary> template:

<review_summary>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 PYTHON CODE REVIEW ANALYSIS - STANDARDS COMPLIANCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall Assessment:    [APPROVE / APPROVE_WITH_COMMENTS / REQUEST_CHANGES]
Standards Compliance:  [COMPLIANT / MINOR_VIOLATIONS / MAJOR_VIOLATIONS]
Code Quality Score:    [A+ / A / A- / B+ / B / B- / C / D / F] with rationale
Production Risk:       [LOW / MEDIUM / HIGH / CRITICAL] with specific concerns
Performance Impact:    [POSITIVE / NEUTRAL / NEGATIVE] with metrics
Security Posture:      [EXCELLENT / GOOD / FAIR / POOR] with specific gaps

Critical Issues:       [count] | High Priority: [count] | Medium: [count] | Low: [count]
Test Coverage:         [percentage]% | Type Safety: [STRICT / MODERATE / WEAK]
Concurrency Safety:    [VERIFIED / CONCERNS / VIOLATIONS]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Quick Action Items
1. [Most critical item with specific file:line]

## Review Highlights
✅ **Strengths**: [Key positive aspects of the implementation]
⚠️  **Concerns**: [Main areas requiring remediation]
📚 **Learning**: [Educational insights and idiomatic suggestions]
</review_summary>

Follow with detailed findings for any P0, P1, or P2 issues with:
- Exact File:Line references
- Root cause and production impact
- Clean, corrected Python code example
"""

    prompt = f"""
Please perform a code review on the following Python Pull Request.

### Phase 1 Automated Validation Results:
{phase1_report or "No automated test/linter failures reported."}

### PR Diff:
```diff
{diff[:65000]}
```
"""

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2,
        ),
    )

    output_path = Path("pr_review.md")
    output_path.write_text(response.text, encoding="utf-8")
    print(f"Review saved to {output_path}")

if __name__ == "__main__":
    main()
