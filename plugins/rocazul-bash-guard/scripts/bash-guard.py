#!/usr/bin/env python3
"""
Bash command guard for Claude Code — static layer.

Works across any project: detects the project root from git or cwd.
Never denies — only allows or asks. Emits "uncertain" so the next hook
(LLM-backed) can decide on commands this layer doesn't recognize.

Decision flow:
  Static analysis → allow / ask / uncertain
  If 'uncertain', the next hook (LLM prompt) analyzes the command.
"""

import json
import sys
import re
import os
import subprocess


def detect_project_dir() -> str:
    """Detect project root from git or fall back to cwd."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return os.getcwd()


PROJECT_DIR = detect_project_dir()
HOME_DIR = os.path.expanduser("~")
CLAUDE_CONFIG_DIR = os.path.join(HOME_DIR, ".claude")

ALLOWED_WRITE_DIRS = [
    PROJECT_DIR,
    "/tmp",
    "/var/folders",
    CLAUDE_CONFIG_DIR,
]

SAFE_COMMANDS = {
    "ls", "cat", "head", "tail", "less", "more", "file", "wc",
    "stat", "tree", "du", "df", "realpath", "readlink", "basename", "dirname",
    "grep", "rg", "find", "which", "where", "type", "locate", "fd",
    "echo", "printf",
    "date", "pwd", "whoami", "id", "uname", "env", "printenv",
    "hostname", "uptime", "ps", "top", "htop",
    "true", "false", "test", "expr", "[",
    "jq", "yq", "cut", "sort", "uniq", "tr", "awk", "sed",
    "git status", "git log", "git diff", "git branch", "git show",
    "git ls-files", "git blame", "git stash list", "git remote",
    "git config --get", "git config --list",
}

WRITE_COMMANDS = {
    "rm", "rmdir", "mv", "cp", "touch", "mkdir", "ln",
    "chmod", "chown", "chgrp",
    "tee", "install",
}

DANGEROUS_PATTERNS = [
    (r"sudo\s+", "sudo command"),
    (r"curl\s+[^|]*\|\s*(ba)?sh", "curl piped to shell"),
    (r"wget\s+[^|]*\|\s*(ba)?sh", "wget piped to shell"),
    (r"dd\s+.*of=/dev/", "dd writing to device"),
    (r"\bmkfs", "filesystem formatting"),
    (r":\s*\(\s*\)\s*\{", "fork bomb pattern"),
]


def is_path_allowed(path: str) -> bool:
    resolved = os.path.abspath(os.path.expanduser(path))
    return any(resolved.startswith(d) for d in ALLOWED_WRITE_DIRS)


def extract_paths(cmd: str) -> list:
    paths = []
    for match in re.finditer(r'(?:^|\s)(/[^\s;|&>"\']+)', cmd):
        paths.append(match.group(1))
    for match in re.finditer(r'(?:^|\s)(~/[^\s;|&>"\']+)', cmd):
        paths.append(match.group(1))
    return paths


def _combine_decisions(decisions: list):
    reasons_ask = [r for d, r in decisions if d == "ask"]
    if reasons_ask:
        return "ask", reasons_ask[0]
    reasons_uncertain = [r for d, r in decisions if d == "uncertain"]
    if reasons_uncertain:
        return "uncertain", reasons_uncertain[0]
    return "allow", ""


def _strip_quotes(cmd: str) -> str:
    return re.sub(r'"[^"]*"', '""', re.sub(r"'[^']*'", "''", cmd))


def analyze_command(cmd: str):
    cmd_stripped = cmd.strip()
    if not cmd_stripped:
        return "allow", ""

    for pattern, label in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd_stripped):
            return "ask", f"Potentially dangerous: {label}"

    unquoted = _strip_quotes(cmd_stripped)
    if any(sep in unquoted for sep in ["&&", "||", ";"]):
        parts = re.split(r'\s*(?:&&|\|\||;)\s*', cmd_stripped)
        decisions = [analyze_command(p) for p in parts if p.strip()]
        return _combine_decisions(decisions)

    if "|" in unquoted:
        parts = [p.strip() for p in cmd_stripped.split("|") if p.strip()]
        decisions = [analyze_command(p) for p in parts]
        return _combine_decisions(decisions)

    tokens = cmd_stripped.split()
    first_word = tokens[0] if tokens else ""
    base_cmd = os.path.basename(first_word)

    if base_cmd in WRITE_COMMANDS:
        paths = extract_paths(cmd_stripped)
        for p in paths:
            if not is_path_allowed(p):
                return "ask", f"'{base_cmd}' targets '{p}' outside allowed dirs"
        return "allow", ""

    if re.search(r"git\s+push", cmd_stripped):
        return "ask", "git push modifies remote repository"
    if re.match(r"git\s+", cmd_stripped):
        return "allow", ""

    SAFE_REDIRECT_TARGETS = {"/dev/null", "/dev/stdout", "/dev/stderr", "/dev/tty", "/dev/zero"}

    if base_cmd in SAFE_COMMANDS or cmd_stripped in SAFE_COMMANDS:
        redirect = re.search(r'[12]?>+\s*([^\s;|&]+)', cmd_stripped)
        if redirect:
            target = redirect.group(1)
            if target not in SAFE_REDIRECT_TARGETS and (target.startswith("/") or target.startswith("~")) and not is_path_allowed(target):
                return "ask", f"Output redirect to '{target}' outside allowed dirs"
        return "allow", ""

    redirect = re.search(r'[12]?>+\s*(/[^\s;|&]+|~/[^\s;|&]+)', cmd_stripped)
    if redirect:
        target = redirect.group(1)
        if target not in SAFE_REDIRECT_TARGETS and not is_path_allowed(target):
            return "ask", f"Output redirect to '{target}' outside allowed dirs"

    return "uncertain", f"Unknown command: {base_cmd}"


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow"
        }}))
        return

    command = input_data.get("tool_input", {}).get("command", "")
    decision, reason = analyze_command(command)

    if decision == "uncertain":
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": f"[bash-guard] project={PROJECT_DIR}. Static analysis uncertain: {reason}"
            }
        }))
        return

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
        }
    }
    if reason:
        output["hookSpecificOutput"]["permissionDecisionReason"] = reason
    if decision == "ask":
        output["systemMessage"] = f"[guard] {reason}\nCommand: {command}"

    print(json.dumps(output))


if __name__ == "__main__":
    main()
