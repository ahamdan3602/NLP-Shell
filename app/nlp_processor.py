"""
nlp_processor.py — pure NLP pipeline: no I/O, no shell calls, no side effects.

Exports one entry-point (parse_user_input) consumed by the shell dispatcher,
plus individual stage functions for unit testing.
"""

import re
import shlex
from dataclasses import dataclass, field


# ── Intent constants ──────────────────────────────────────────────────────────

INTENT_EXIT               = "exit"
INTENT_ECHO               = "echo"
INTENT_CHANGE_DIR         = "change_directory"
INTENT_PRINT_DIR          = "print_directory"
INTENT_TYPE_CHECK         = "type_check"
INTENT_HELP               = "help"
INTENT_CLEAR              = "clear"
INTENT_SMARTSHELL         = "smartshell"
INTENT_SYSTEM_EXECUTABLE  = "system_executable"
INTENT_NATURAL_LANGUAGE   = "natural_language"
INTENT_UNKNOWN            = "unknown"


@dataclass
class ParseResult:
    raw_input: str
    parsed_tokens: list = field(default_factory=list)
    user_intent: str = INTENT_UNKNOWN
    extracted_entities: dict = field(default_factory=dict)
    is_natural_language: bool = False


# ── Lookup tables ─────────────────────────────────────────────────────────────

_BUILTIN_INTENT_MAP: dict[str, str] = {
    "exit":       INTENT_EXIT,
    "quit":       INTENT_EXIT,
    "bye":        INTENT_EXIT,
    "echo":       INTENT_ECHO,
    "print":      INTENT_ECHO,
    "cd":         INTENT_CHANGE_DIR,
    "pwd":        INTENT_PRINT_DIR,
    "type":       INTENT_TYPE_CHECK,
    "help":       INTENT_HELP,
    "?":          INTENT_HELP,
    "clear":      INTENT_CLEAR,
    "cls":        INTENT_CLEAR,
    "smartshell": INTENT_SMARTSHELL,
    "ai":         INTENT_SMARTSHELL,
    "smart":      INTENT_SMARTSHELL,
    "nlp":        INTENT_SMARTSHELL,
    "gpt":        INTENT_SMARTSHELL,
}

# Imperative verbs and sentence starters that mark natural-language utterances.
# Ordered most-specific to least-specific to short-circuit early.
_NL_TRIGGER_PATTERNS: list[str] = [
    r"^(please\s+)?(list|show|display|find|locate|search|look\s+for)\b",
    r"^(please\s+)?(create|make|generate|write|produce|build)\b",
    r"^(please\s+)?(delete|remove|erase|clean\s+up)\b",
    r"^(please\s+)?(move|copy|rename|transfer|compress|archive)\b",
    r"^(please\s+)?(install|uninstall|upgrade|update|setup)\b",
    r"^(what|where|when|who|how|why|which)\b",  # WH-question forms
    r"\?\s*$",                                    # trailing question mark
    r"^(can you|could you|would you|please)\b",  # polite directives
    r"^(i want|i need|i'd like|i would like)\b",
    r"^(tell me|give me|show me|help me)\b",
]

# Programs whose names are plain English words. Without this exclusion set,
# "find .", "make build", etc. would be misclassified as natural language.
_KNOWN_CLI_COMMANDS: frozenset[str] = frozenset([
    "git", "npm", "npx", "pip", "pip3", "python", "python3",
    "node", "make", "cmake", "cargo", "rustc", "go",
    "gcc", "g++", "clang", "clang++", "java", "javac",
    "mvn", "gradle", "ant", "docker", "docker-compose",
    "kubectl", "helm", "terraform", "ansible",
    "ssh", "scp", "sftp", "curl", "wget", "rsync",
    "grep", "find", "awk", "sed", "sort", "uniq", "wc",
    "cat", "ls", "dir", "cp", "mv", "rm", "mkdir", "touch",
    "chmod", "chown", "chgrp", "ln",
    "ps", "kill", "killall", "top", "htop", "df", "du", "lsof",
    "ping", "traceroute", "nslookup", "dig", "ifconfig", "ip",
    "tar", "gzip", "gunzip", "zip", "unzip",
    "vi", "vim", "nano", "emacs",
    "bash", "sh", "zsh", "fish", "powershell", "pwsh",
    "echo", "printf", "type", "which", "whereis", "man",
])

# Only patterns whose blast radius is truly catastrophic are blocked here.
# Destructive-but-recoverable commands (e.g. 'rm file.txt') reach the user's
# confirmation step so they retain full control.
_DANGEROUS_PATTERNS: list[str] = [
    r"\brm\s+(-[rRf]+\s+)+/\s*$",               # rm -rf /
    r"\bmkfs\b",                                  # format filesystem
    r"\bdd\b.*\bof=/dev/(sd|hd|nvme|xvd)",       # raw-disk overwrite
    r":\(\)\s*\{.*:\|:&\s*\};:",                  # fork bomb
    r"\bchmod\s+-R\s+777\s+/",                   # world-writable root
    r"\bformat\s+[A-Za-z]:",                      # Windows disk format
    r"\b(shutdown|halt|poweroff)\b",              # system power control
    r"\bdel\s+/[sfqSFQ]+\s+[A-Za-z]:\\",        # Windows recursive delete from root
]


# ── Stage 1: Tokenization ─────────────────────────────────────────────────────

def tokenize_user_input(raw_input: str) -> list[str]:
    """Tokenize using shell-aware lexing; degrade gracefully on unmatched quotes."""
    if not raw_input or not raw_input.strip():
        return []
    try:
        return shlex.split(raw_input.strip())
    except ValueError:
        # Unmatched quotes — split on whitespace so the shell stays alive.
        return raw_input.strip().split()


# ── Stage 2: Intent classification ───────────────────────────────────────────

def extract_intent(parsed_tokens: list[str], raw_input: str = "") -> str:
    """Classify dominant intent from the token list and original raw string.

    Token-level lookup is tried first (exact, O(1)). NL pattern matching on
    the full raw string runs second because tokens lose word-boundary context.
    The length-plus-vocabulary heuristic is a last-resort signal.
    """
    if not parsed_tokens:
        return INTENT_UNKNOWN

    primary_token = parsed_tokens[0].lower()

    if primary_token in _BUILTIN_INTENT_MAP:
        return _BUILTIN_INTENT_MAP[primary_token]

    raw_lower = raw_input.lower().strip()
    for nl_pattern in _NL_TRIGGER_PATTERNS:
        if re.search(nl_pattern, raw_lower):
            return INTENT_NATURAL_LANGUAGE

    # A 5+ character lowercase word not in the known-CLI set is a strong
    # indicator that the user typed prose rather than a command name.
    if (
        re.match(r"^[a-z]{5,}$", primary_token)
        and primary_token not in _KNOWN_CLI_COMMANDS
    ):
        return INTENT_NATURAL_LANGUAGE

    return INTENT_SYSTEM_EXECUTABLE


# ── Stage 3: Entity extraction ────────────────────────────────────────────────

def extract_entities(parsed_tokens: list[str]) -> dict:
    """Extract typed entities from a tokenized input.

    Entity types: command_name, file_paths, flags, numeric_args, remaining_args.
    """
    extracted_entities: dict = {
        "command_name": None,
        "file_paths": [],
        "flags": [],
        "numeric_args": [],
        "remaining_args": [],
    }

    if not parsed_tokens:
        return extracted_entities

    extracted_entities["command_name"] = parsed_tokens[0]

    # Matches POSIX absolute/relative paths and Windows drive-letter paths.
    path_pattern = re.compile(
        r"^(?:[A-Za-z]:[\\\/]|[\/~]|\.{1,2}[\/\\]).+|^\.{1,2}$"
    )

    for token in parsed_tokens[1:]:
        if token.startswith("--") or re.match(r"^-[a-zA-Z]$", token):
            extracted_entities["flags"].append(token)
        elif path_pattern.match(token):
            extracted_entities["file_paths"].append(token)
        elif re.match(r"^-?\d+(\.\d+)?$", token):
            # Store as float to uniformly handle int and decimal arguments.
            extracted_entities["numeric_args"].append(float(token))
        else:
            extracted_entities["remaining_args"].append(token)

    return extracted_entities


# ── Stage 3b: NL signal ───────────────────────────────────────────────────────

def is_natural_language_query(raw_input: str) -> bool:
    """Return True when the input resembles a natural-language sentence.

    This supplements extract_intent() for borderline inputs (e.g. a known CLI
    command name used in a sentence context).
    """
    raw_lower = raw_input.lower().strip()

    for pattern in _NL_TRIGGER_PATTERNS:
        if re.search(pattern, raw_lower):
            return True

    # Four-or-more-word inputs whose first token is an unknown plain word are
    # almost certainly prose; shell invocations typically have few tokens.
    words = raw_input.split()
    if len(words) >= 4:
        first_word = words[0].lower()
        if (
            re.match(r"^[a-z][a-z0-9_-]*$", first_word)
            and first_word not in _KNOWN_CLI_COMMANDS
        ):
            return True

    return False


# ── Stage 4: Safety validation ────────────────────────────────────────────────

def validate_command_safety(command: str) -> tuple[bool, str]:
    """Scan a generated command string for catastrophically destructive patterns.

    Returns (is_safe, warning_message). Safe commands pass through to the
    user's confirmation prompt; only truly irreversible ones are hard-blocked.
    """
    for danger_pattern in _DANGEROUS_PATTERNS:
        if re.search(danger_pattern, command, re.IGNORECASE):
            return False, f"Matches dangerous pattern: {danger_pattern!r}"
    return True, ""


# ── Pipeline entry point ──────────────────────────────────────────────────────

def parse_user_input(raw_input: str) -> ParseResult:
    """Run the full NLP pipeline and return a structured ParseResult.

    This is the only symbol that app.py and smartshell.py need to import.
    """
    if not raw_input or not raw_input.strip():
        return ParseResult(raw_input=raw_input or "")

    parsed_tokens     = tokenize_user_input(raw_input)
    user_intent       = extract_intent(parsed_tokens, raw_input)
    extracted_entities = extract_entities(parsed_tokens)
    is_natural_language = is_natural_language_query(raw_input)

    # NL signal overrides a weak SYSTEM_EXECUTABLE classification so that
    # prose typed into the main shell is automatically routed to SmartShell.
    if is_natural_language and user_intent == INTENT_SYSTEM_EXECUTABLE:
        user_intent = INTENT_NATURAL_LANGUAGE

    return ParseResult(
        raw_input=raw_input,
        parsed_tokens=parsed_tokens,
        user_intent=user_intent,
        extracted_entities=extracted_entities,
        is_natural_language=is_natural_language,
    )
