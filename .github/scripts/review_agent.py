#!/usr/bin/env python3
"""
Python Code Review Agent with:
1. Pipeline Trigger context gathering
2. Context Pruning using Tiktoken
3. Structured Output using Pydantic & Gemini 3.1 Pro / 3.7 Flash
4. Feedback Loop using GitHub REST API for native inline PR comments
All designed to run 100% within free-tier limits.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Literal, Optional

import httpx
import tiktoken
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# ==============================================================================
# 1. Pydantic Schemas for Structured Review Output
# ==============================================================================

class InlineComment(BaseModel):
    path: str = Field(description="Relative path of the modified file (e.g. src/matcher.py)")
    line: int = Field(description="Line number in the newly changed file (RIGHT side of the diff)")
    severity: Literal["P0_CRITICAL", "P1_PERFORMANCE", "P2_MAINTAINABILITY", "P3_STYLE"] = Field(
        description="Severity level following python-code-reviewer standards"
    )
    issue: str = Field(description="Concise description of the problem or anti-pattern")
    suggestion: str = Field(description="Actionable fix or replacement code snippet")

class PRReviewResult(BaseModel):
    overall_assessment: Literal["APPROVE", "COMMENT", "REQUEST_CHANGES"] = Field(
        description="PR review decision"
    )
    standards_compliance: Literal["COMPLIANT", "MINOR_VIOLATIONS", "MAJOR_VIOLATIONS"] = Field(
        description="Compliance with Python Golden Rules"
    )
    code_quality_score: str = Field(
        description="Score between A+ and F with brief rationale"
    )
    production_risk: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        description="Risk of production outages, deadlocks, or resource leaks"
    )
    performance_impact: Literal["POSITIVE", "NEUTRAL", "NEGATIVE"] = Field(
        description="Estimated latency or throughput impact"
    )
    security_posture: Literal["EXCELLENT", "GOOD", "FAIR", "POOR"] = Field(
        description="Security assessment regarding injection, secrets, etc."
    )
    critical_issues_count: int = Field(default=0)
    high_priority_count: int = Field(default=0)
    medium_priority_count: int = Field(default=0)
    low_priority_count: int = Field(default=0)
    summary_markdown: str = Field(
        description="High-level executive summary in Markdown format"
    )
    inline_comments: list[InlineComment] = Field(
        default_factory=list,
        description="List of line-specific actionable review comments"
    )


# ==============================================================================
# 2. Context Pruning using Tiktoken
# ==============================================================================

IGNORED_PATTERNS = [
    r"\.lock$",
    r"package-lock\.json$",
    r"poetry\.lock$",
    r"Pipfile\.lock$",
    r"\.seen_deals\.json$",
    r"latest_deal_email\.html$",
    r"\.pyc$",
    r"__pycache__/",
    r"\.png$",
    r"\.jpg$",
    r"\.jpeg$",
    r"\.svg$",
    r"\.env.*",
]

def is_ignored_file(filepath: str) -> bool:
    for pattern in IGNORED_PATTERNS:
        if re.search(pattern, filepath):
            return True
    return False

def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    try:
        enc = tiktoken.get_encoding(encoding_name)
    except Exception:
        enc = tiktoken.encoding_for_model("gpt-4")
    return len(enc.encode(text))

def prune_and_chunk_diff(base_ref: str, max_tokens: int = 15000) -> tuple[str, list[dict]]:
    """
    Parses git diff by file, strips noise/lockfiles/caches,
    and budgets tokens using tiktoken.
    """
    # Get list of changed files
    diff_stat_cmd = f"git diff origin/{base_ref}...HEAD --name-only"
    changed_files = subprocess.run(diff_stat_cmd, shell=True, capture_output=True, text=True).stdout.strip().splitlines()

    valid_files = [f for f in changed_files if not is_ignored_file(f)]
    print(f"[Context Pruning] Total changed files: {len(changed_files)}, Kept after pruning: {len(valid_files)}")

    pruned_diffs = []
    total_tokens = 0
    parsed_files = []

    for file_path in valid_files:
        diff_cmd = f"git diff origin/{base_ref}...HEAD -- '{file_path}'"
        file_diff = subprocess.run(diff_cmd, shell=True, capture_output=True, text=True).stdout.strip()
        if not file_diff:
            continue

        file_tokens = count_tokens(file_diff)
        if total_tokens + file_tokens > max_tokens:
            print(f"[Context Pruning] Token limit reached ({total_tokens}/{max_tokens}). Skipping file: {file_path}")
            continue

        total_tokens += file_tokens
        pruned_diffs.append(file_diff)
        parsed_files.append({"path": file_path, "tokens": file_tokens})

    combined_diff = "\n\n".join(pruned_diffs)
    print(f"[Context Pruning] Final diff size: {total_tokens} tokens across {len(parsed_files)} files")
    return combined_diff, parsed_files


# ==============================================================================
# 3. LLM Review Engine (Gemini 3.1 Pro Preview / 3.7 Flash)
# ==============================================================================

def load_skill_instructions() -> str:
    candidates = [
        Path(".gemini/skills/python-code-reviewer/SKILL.md"),
        Path("skills/python-code-reviewer/SKILL.md"),
    ]
    for c in candidates:
        if c.exists():
            return c.read_text(encoding="utf-8")
    return "You are an expert Python code reviewer. Enforce PEP 8, strict types, asyncio hygiene, no bare except, and no blocking calls in coroutines."

def run_review(diff: str, phase1_report: str) -> PRReviewResult:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("Gemini_key") or os.getenv("GEMINI_KEY")
    if not api_key:
        print("[Error] No GEMINI_API_KEY or Gemini_key found in environment.")
        sys.exit(1)

    # Use updated model; gemini-3.1-pro-preview or gemini-3.7-flash
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview")
    print(f"[Review Agent] Invoking model: {model_name}")

    client = genai.Client(api_key=api_key)
    system_instruction = f"""
{load_skill_instructions()}

Analyze the PR diff and automated test results against Python standards.
Identify exact line numbers on changed files for any issues.
Output MUST strictly conform to the provided JSON schema.
"""

    prompt = f"""
Please perform a code review on the following Python Pull Request.

### Phase 1 Automated Validation Results:
{phase1_report or "No automated test/linter failures reported."}

### PR Diff:
```diff
{diff}
```
"""

    # We use client.chats.create + chat.send_message with AFC disabled to avoid
    # the GHA warning: "Direct use of automatic function calling (AFC) in Models.generate_content is not recommended"
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.2,
        response_mime_type="application/json",
        response_schema=PRReviewResult,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    try:
        chat = client.chats.create(model=model_name, config=config)
        response = chat.send_message(prompt)
    except Exception as e:
        print(f"[Warning] Call with {model_name} failed: {e}. Falling back to gemini-3.7-flash...")
        chat = client.chats.create(model="gemini-3.7-flash", config=config)
        response = chat.send_message(prompt)

    # Parse response into Pydantic model
    try:
        data = json.loads(response.text)
        return PRReviewResult.model_validate(data)
    except Exception as e:
        print(f"[Error] Failed to validate structured output with Pydantic: {e}")
        print(f"Raw Response: {response.text}")
        raise


# ==============================================================================
# 4. Feedback Loop using GitHub REST API
# ==============================================================================

def post_github_review(review: PRReviewResult):
    github_token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")
    pr_number = os.getenv("PR_NUMBER")
    head_sha = os.getenv("HEAD_SHA")

    if not all([github_token, repo, pr_number, head_sha]):
        print("[Feedback Loop] Incomplete GitHub environment; writing local pr_review.md instead.")
        with open("pr_review.md", "w") as f:
            f.write(review.summary_markdown)
        return

    # Build executive summary body
    summary_body = f"""### 📊 Python Code Review Summary

| Metric | Status |
| :--- | :--- |
| **Assessment** | `{review.overall_assessment}` |
| **Standards Compliance** | `{review.standards_compliance}` |
| **Code Quality Score** | `{review.code_quality_score}` |
| **Production Risk** | `{review.production_risk}` |
| **Performance Impact** | `{review.performance_impact}` |
| **Security Posture** | `{review.security_posture}` |

**Issues Found:** 🚨 Critical: `{review.critical_issues_count}` | ⚡ High: `{review.high_priority_count}` | ⚠️ Medium: `{review.medium_priority_count}` | ℹ️ Low: `{review.low_priority_count}`

---

{review.summary_markdown}
"""

    # Prepare inline comments
    comments_payload = []
    overflow_comments = []

    for c in review.inline_comments:
        comment_text = f"**[{c.severity}]** {c.issue}\n\n**Suggestion:**\n```python\n{c.suggestion}\n```"
        if c.line > 0:
            comments_payload.append({
                "path": c.path,
                "line": c.line,
                "side": "RIGHT",
                "body": comment_text,
            })
        else:
            overflow_comments.append(f"- **{c.path}**: {c.issue}")

    if overflow_comments:
        summary_body += "\n\n### Additional Comments:\n" + "\n".join(overflow_comments)

    # Determine GitHub Review Event
    event = "COMMENT"
    if review.overall_assessment == "REQUEST_CHANGES":
        event = "REQUEST_CHANGES"
    elif review.overall_assessment == "APPROVE":
        event = "APPROVE"

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews"
    review_data = {
        "commit_id": head_sha,
        "body": summary_body,
        "event": event,
        "comments": comments_payload,
    }

    print(f"[Feedback Loop] Submitting GitHub Review ({event}) with {len(comments_payload)} inline comments...")
    with httpx.Client(timeout=30.0) as http_client:
        res = http_client.post(url, headers=headers, json=review_data)
        if res.status_code == 200:
            print("[Feedback Loop] ✅ Successfully posted GitHub PR Review with inline comments!")
        elif res.status_code == 422:
            # 422 Unprocessable Entity can happen if a line number is outside diff range.
            print(f"[Feedback Loop] Warning: Some inline lines were outside diff hunk (422). Posting review body without inline comments...")
            review_data["comments"] = []
            res_retry = http_client.post(url, headers=headers, json=review_data)
            if res_retry.status_code == 200:
                print("[Feedback Loop] ✅ Posted general PR Review successfully.")
            else:
                print(f"[Feedback Loop] Error: {res_retry.status_code} {res_retry.text}")
        else:
            print(f"[Feedback Loop] Error submitting review: {res.status_code} {res.text}")


# ==============================================================================
# Main Orchestration
# ==============================================================================

def main():
    base_ref = os.getenv("BASE_REF", "main")
    diff, files = prune_and_chunk_diff(base_ref=base_ref)

    if not diff:
        print("[Review Agent] No code files to review after pruning.")
        sys.exit(0)

    phase1_report = ""
    report_file = Path("phase1_report.txt")
    if report_file.exists():
        phase1_report = report_file.read_text(encoding="utf-8")

    review_result = run_review(diff=diff, phase1_report=phase1_report)
    post_github_review(review_result)
    print("[Review Agent] Review completed successfully.")

if __name__ == "__main__":
    main()
