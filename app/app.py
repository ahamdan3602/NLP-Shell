import sys
import os
import subprocess
import shlex

from nlp_processor import (
    parse_user_input,
    INTENT_EXIT,
    INTENT_ECHO,
    INTENT_CHANGE_DIR,
    INTENT_PRINT_DIR,
    INTENT_TYPE_CHECK,
    INTENT_HELP,
    INTENT_CLEAR,
    INTENT_SMARTSHELL,
    INTENT_NATURAL_LANGUAGE,
    INTENT_SYSTEM_EXECUTABLE,
)

try:
    from smartshell import ShellImplementation
    _SMARTSHELL_AVAILABLE = True
except Exception as _smartshell_err:
    _SMARTSHELL_AVAILABLE = False
    _SMARTSHELL_ERROR = str(_smartshell_err)


class Shell:
    """Interactive shell with built-ins, redirection, NLP routing, and SmartShell."""

    def __init__(self):
        self._builtin_names = [
            "exit", "echo", "type", "pwd", "cd",
            "help", "clear", "smartshell",
        ]

    def showBanner(self):
        sys.stdout.write("\n")
        sys.stdout.write("=" * 52 + "\n")
        sys.stdout.write(" SmartShell | NLP-Powered Terminal\n")
        sys.stdout.write(" Built-ins : help, clear, smartshell\n")
        sys.stdout.write(" Tip       : type naturally — NLP routes for you\n")
        sys.stdout.write("=" * 52 + "\n\n")

    def getPrompt(self):
        cwd_name = os.path.basename(os.getcwd()) or os.getcwd()
        return f"SmartShell[{cwd_name}]$ "

    def run(self):
        """Main REPL: read input → classify via NLP → dispatch."""
        self.showBanner()

        while True:
            try:
                raw_input = input(self.getPrompt()).strip()
            except KeyboardInterrupt:
                sys.stdout.write("\n")
                continue
            except EOFError:
                sys.stdout.write("\n")
                break

            if not raw_input:
                continue

            # Redirection must be detected before NLP classification because
            # tokens like '>' and '2>' confuse the intent classifier.
            raw_tokens = raw_input.split()
            if ">" in raw_tokens or "1>" in raw_tokens:
                self.handleStdout(raw_input)
                continue
            if "2>" in raw_tokens:
                self.handleStderr(raw_input)
                continue

            parse_result = parse_user_input(raw_input)
            self._dispatch(parse_result)

    # ── NLP-driven dispatcher ─────────────────────────────────────────────────

    def _dispatch(self, parse_result):
        """Route a ParseResult to the matching handler — pure dispatch, no logic."""
        intent = parse_result.user_intent

        if intent == INTENT_EXIT:
            self.handleExit(parse_result.raw_input)
        elif intent == INTENT_ECHO:
            self.handleEcho(parse_result.raw_input)
        elif intent == INTENT_CHANGE_DIR:
            self.handleCD(parse_result.raw_input)
        elif intent == INTENT_PRINT_DIR:
            self.handlePWD(parse_result.raw_input)
        elif intent == INTENT_TYPE_CHECK:
            self.handleType(parse_result.raw_input)
        elif intent == INTENT_HELP:
            self.handleHelp()
        elif intent == INTENT_CLEAR:
            self.handleClear()
        elif intent == INTENT_SMARTSHELL:
            self._launch_smartshell(parse_result)
        elif intent == INTENT_NATURAL_LANGUAGE:
            self._route_nl_to_smartshell(parse_result.raw_input)
        else:
            self.runExecutable(parse_result.raw_input)

    def _launch_smartshell(self, parse_result):
        """Enter SmartShell loop, or handle an inline query if args were given.

        'smartshell'              → interactive loop
        'smartshell list files'   → one-shot NL query, then back to main shell
        """
        if not _SMARTSHELL_AVAILABLE:
            sys.stdout.write(f"SmartShell unavailable: {_SMARTSHELL_ERROR}\n")
            return

        inline_tokens = parse_result.parsed_tokens[1:]
        if inline_tokens:
            inline_query = " ".join(inline_tokens)
            try:
                ShellImplementation().handle_nl_query(inline_query)
            except RuntimeError as init_err:
                sys.stdout.write(f"SmartShell error: {init_err}\n")
        else:
            try:
                ShellImplementation().run()
            except RuntimeError as init_err:
                sys.stdout.write(f"SmartShell error: {init_err}\n")

    def _route_nl_to_smartshell(self, nl_query: str):
        """Automatically forward a natural-language query to SmartShell inline."""
        if not _SMARTSHELL_AVAILABLE:
            sys.stdout.write(
                f"Natural-language routing unavailable: {_SMARTSHELL_ERROR}\n"
                "Try installing dependencies: pip install openai python-dotenv\n"
            )
            return

        sys.stdout.write("[NLP] Routing to SmartShell...\n")
        try:
            ShellImplementation().handle_nl_query(nl_query)
        except RuntimeError as init_err:
            sys.stdout.write(f"SmartShell error: {init_err}\n")

    # ── Built-in handlers ─────────────────────────────────────────────────────

    def runExecutable(self, raw_input: str):
        """Execute a non-builtin command by resolving it from PATH."""
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)

        try:
            parts = shlex.split(raw_input)
        except ValueError:
            parts = raw_input.split()

        if not parts:
            return

        command = parts[0]

        for directory in path_dirs:
            full_path = os.path.join(directory, command)
            if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                subprocess.run([command] + parts[1:])
                return

        sys.stdout.write(f"{command}: command not found\n")

    def handleCD(self, raw_input: str):
        """Change the current working directory."""
        parts = raw_input.split(maxsplit=1)

        if len(parts) == 1:
            home = os.environ.get("USERPROFILE") or os.environ.get("HOME") or os.getcwd()
            os.chdir(home)
            return

        path = parts[1].strip()

        if "~" in path:
            home = os.environ.get("USERPROFILE") or os.environ.get("HOME", "")
            os.chdir(home)
        elif os.path.isdir(path):
            os.chdir(path)
        else:
            sys.stdout.write(f"cd: {path}: No such file or directory\n")

    def handlePWD(self, raw_input: str):
        sys.stdout.write(f"{os.getcwd()}\n")

    def handleStderr(self, raw_input: str):
        """Redirect command stderr to a file using 2>."""
        symbol = "2>"
        parts = raw_input.split(symbol, 1)

        if len(parts) < 2:
            sys.stdout.write("Syntax error: no output file provided\n")
            return

        cmd_part    = parts[0].strip()
        output_file = parts[1].strip()

        if not output_file:
            sys.stdout.write("Syntax error: missing output file name\n")
            return

        cmd_tokens = cmd_part.split()
        if not cmd_tokens:
            sys.stdout.write("Syntax error: missing command before redirect\n")
            return

        if cmd_tokens[0] == "echo":
            self.handleEcho(cmd_part)
            try:
                with open(output_file, "w") as fh:
                    fh.write("")
            except OSError as io_err:
                sys.stdout.write(f"Error: {io_err}\n")
            return

        res = subprocess.run(cmd_tokens, capture_output=True, text=True)
        if res.stderr:
            try:
                with open(output_file, "a") as fh:
                    fh.write(res.stderr)
            except FileNotFoundError:
                sys.stdout.write(f"{cmd_tokens[0]}: command not found\n")

    def handleStdout(self, raw_input: str):
        """Redirect command stdout to a file using > or 1>."""
        symbol = "1>" if "1>" in raw_input else ">"
        parts  = raw_input.split(symbol, 1)

        if len(parts) < 2:
            sys.stdout.write("Syntax error: no output file provided\n")
            return

        cmd_part    = parts[0].strip()
        output_file = parts[1].strip()

        if not output_file:
            sys.stdout.write("Syntax error: missing output file name\n")
            return

        cmd_tokens = cmd_part.split()
        if not cmd_tokens:
            sys.stdout.write("Syntax error: missing command before redirection\n")
            return

        if cmd_tokens[0] == "echo":
            output = " ".join(cmd_tokens[1:]).strip()
            if (output.startswith("'") and output.endswith("'")) or (
                output.startswith('"') and output.endswith('"')
            ):
                output = output[1:-1]
            with open(output_file, "w") as fh:
                fh.write(output + "\n")
            return

        try:
            with open(output_file, "a") as fh:
                res = subprocess.run(cmd_tokens, capture_output=True, text=True)
                fh.write(res.stdout)
                if res.stderr:
                    sys.stderr.write(res.stderr)
        except FileNotFoundError:
            sys.stdout.write(f"{cmd_tokens[0]}: command not found\n")

    def handleType(self, raw_input: str):
        """Report whether a token is a builtin or a PATH-resolved executable."""
        parts = raw_input.split()
        cmd   = parts[1] if len(parts) > 1 else ""

        if not cmd:
            sys.stdout.write("type: missing argument\n")
            return

        if cmd in self._builtin_names:
            sys.stdout.write(f"{cmd} is a shell builtin\n")
            return

        for directory in os.getenv("PATH", "").split(os.pathsep):
            candidate = os.path.join(directory, cmd)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                sys.stdout.write(f"{cmd} is {candidate}\n")
                return

        sys.stdout.write(f"{cmd}: not found\n")

    def handleEcho(self, raw_input: str):
        """Print echo arguments with shell-style tokenization."""
        try:
            tokens = shlex.split(raw_input)
            output = " ".join(tokens[1:])
            sys.stdout.write(f"{output}\n")
        except ValueError as parse_err:
            sys.stderr.write(f"echo: parse error: {parse_err}\n")

    def handleExit(self, raw_input: str):
        """Exit the shell with an optional numeric status code."""
        parts = raw_input.split()
        try:
            status_code = int(parts[1]) if len(parts) > 1 else 0
        except ValueError:
            sys.stdout.write(f"exit: {parts[1]!r}: numeric argument required\n")
            status_code = 1
        sys.exit(status_code)

    def handleHelp(self):
        sys.stdout.write(
            "Built-ins: exit, echo, type, pwd, cd, help, clear, smartshell\n"
            "NLP tip  : type a natural-language request and SmartShell handles it.\n"
        )

    def handleClear(self):
        os.system("cls" if os.name == "nt" else "clear")


def main():
    Shell().run()


if __name__ == "__main__":
    main()
