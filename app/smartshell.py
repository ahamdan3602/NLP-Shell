"""
smartshell.py — natural-language → shell-action translator.

Maintains a multi-turn conversation history with the model and dispatches
to three distinct tool handlers: Bash (run a command), WriteFile (write
content to disk), and ReadFile (read and display a file).
"""

import os
import sys
import json
import shlex
import subprocess
from dotenv import load_dotenv
from openai import OpenAI, APIError

from nlp_processor import parse_user_input, validate_command_safety

load_dotenv()

_API_KEY  = os.getenv("OPENROUTER_CLAUDE_API_KEY")
_BASE_URL = os.getenv("OPENROUTER_BASE_URL")
_MODEL    = os.getenv("OPENROUTER_MODEL")

_SYSTEM_PROMPT = (
    "You are a shell-command expert assistant. "
    "When the user describes a task, call exactly ONE of the available tools: "
    "use Bash to run a shell command, WriteFile to write text content to a file, "
    "or ReadFile to read an existing file. "
    "Never add explanatory prose — only call a tool."
)

_TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "Bash",
            "description": "Execute a shell command on the user's machine.",
            "parameters": {
                "type": "object",
                "required": ["command"],
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to run.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "WriteFile",
            "description": "Write text content to a file on disk.",
            "parameters": {
                "type": "object",
                "required": ["file_path", "content"],
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Relative or absolute path of the file to write.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full text content to write into the file.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ReadFile",
            "description": "Read and return the content of a file from disk.",
            "parameters": {
                "type": "object",
                "required": ["file_path"],
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path of the file to read.",
                    }
                },
            },
        },
    },
]


class ShellImplementation:
    """Translate natural-language prompts into shell actions and execute safely."""

    def __init__(self):
        if not _API_KEY:
            raise RuntimeError(
                "OPENROUTER_CLAUDE_API_KEY is not set — add it to .env"
            )

        self.client = OpenAI(api_key=_API_KEY, base_url=_BASE_URL)
        self.conversation_history: list[dict] = [
            {"role": "system", "content": _SYSTEM_PROMPT}
        ]

    # ── Public interface ──────────────────────────────────────────────────────

    def run(self):
        """Enter the SmartShell interactive loop. Type 'exit' or Ctrl-C to return."""
        sys.stdout.write(
            "\nSmartShell active — describe what you want to do.\n"
            "Type 'exit' or press Ctrl-C to return to the main shell.\n\n"
        )

        while True:
            try:
                nl_query = input("SmartShell> ").strip()
            except KeyboardInterrupt:
                sys.stdout.write("\nSmartShell interrupted. Returning to shell.\n")
                break
            except EOFError:
                break

            if not nl_query:
                continue

            if nl_query.lower() in {"exit", "quit", "bye", "back"}:
                sys.stdout.write("Returning to main shell.\n")
                break

            self.handle_nl_query(nl_query)

    def handle_nl_query(self, nl_query: str):
        """Process a single natural-language query end-to-end.

        Public so that app.py can invoke inline (one-shot) SmartShell
        interactions without entering the interactive loop.
        """
        parse_result = parse_user_input(nl_query)
        self.conversation_history.append({"role": "user", "content": nl_query})

        try:
            model_message = self._request_tool_call(self.conversation_history)
        except APIError as api_err:
            sys.stdout.write(f"API error: {api_err}\n")
            self.conversation_history.pop()
            return
        except Exception as unexpected_err:
            sys.stdout.write(f"Unexpected error: {unexpected_err}\n")
            self.conversation_history.pop()
            return

        if not model_message.tool_calls:
            text_reply = model_message.content or "(no response from model)"
            sys.stdout.write(f"{text_reply}\n")
            self.conversation_history.append(
                {"role": "assistant", "content": text_reply}
            )
            return

        self.conversation_history.append(
            self._message_to_history_dict(model_message)
        )

        for tool_call in model_message.tool_calls:
            self._dispatch_tool_call(tool_call)

    # ── API layer ─────────────────────────────────────────────────────────────

    def _request_tool_call(self, messages: list[dict]):
        """Send conversation history to the model and return the response message."""
        chat = self.client.chat.completions.create(
            model=_MODEL,
            messages=messages,
            tools=_TOOL_SCHEMAS,
            max_tokens=1024,
        )
        if not chat.choices:
            raise RuntimeError("Model returned an empty choices list.")
        return chat.choices[0].message

    # ── Tool dispatcher ───────────────────────────────────────────────────────

    def _dispatch_tool_call(self, tool_call):
        """Route a single model tool call to the appropriate handler."""
        fn_name = tool_call.function.name

        try:
            fn_args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            sys.stdout.write(
                f"Malformed tool arguments from model: {tool_call.function.arguments!r}\n"
            )
            return

        if fn_name == "Bash":
            self._handle_bash_tool(fn_args.get("command", ""), tool_call.id)
        elif fn_name == "WriteFile":
            self._handle_write_file_tool(
                fn_args.get("file_path", ""),
                fn_args.get("content", ""),
                tool_call.id,
            )
        elif fn_name == "ReadFile":
            self._handle_read_file_tool(fn_args.get("file_path", ""), tool_call.id)
        else:
            sys.stdout.write(f"Unknown tool requested by model: {fn_name!r}\n")

    # ── Tool handlers ─────────────────────────────────────────────────────────

    def _handle_bash_tool(self, command: str, tool_call_id: str):
        """Validate safety, display the command, and execute only after confirmation."""
        if not command:
            sys.stdout.write("Model returned an empty command.\n")
            return

        is_safe, safety_warning = validate_command_safety(command)
        if not is_safe:
            sys.stdout.write(f"Command blocked — {safety_warning}\n")
            self._append_tool_result(tool_call_id, f"Blocked: {safety_warning}")
            return

        normalized_command = self._normalize_command_display(command)
        sys.stdout.write(f"\nGenerated command:\n  {normalized_command}\n\n")

        if self._user_confirmed_execution("Run this command? [y/N] "):
            self._execute_shell_command(normalized_command, tool_call_id)
        else:
            sys.stdout.write("Command skipped.\n")
            self._append_tool_result(tool_call_id, "User declined execution.")

    def _handle_write_file_tool(
        self, file_path: str, content: str, tool_call_id: str
    ):
        """Preview file content and write to disk after confirmation."""
        if not file_path:
            sys.stdout.write("Model did not provide a file path for WriteFile.\n")
            return

        preview_lines = content.splitlines()[:12]
        preview_text  = "\n".join(preview_lines)
        is_truncated  = len(content.splitlines()) > 12

        sys.stdout.write(f"\nWill write to: {file_path}\n")
        sys.stdout.write("─" * 40 + "\n")
        sys.stdout.write(preview_text)
        if is_truncated:
            sys.stdout.write("\n  [...truncated — full content will be written...]")
        sys.stdout.write("\n" + "─" * 40 + "\n\n")

        if self._user_confirmed_execution("Write this file? [y/N] "):
            try:
                parent_dir = os.path.dirname(os.path.abspath(file_path))
                os.makedirs(parent_dir, exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as fh:
                    fh.write(content)
                sys.stdout.write(f"Written: {file_path}\n")
                self._append_tool_result(tool_call_id, f"File written: {file_path}")
            except OSError as io_err:
                sys.stdout.write(f"Write failed: {io_err}\n")
                self._append_tool_result(tool_call_id, f"Write failed: {io_err}")
        else:
            sys.stdout.write("File write skipped.\n")
            self._append_tool_result(tool_call_id, "User declined file write.")

    def _handle_read_file_tool(self, file_path: str, tool_call_id: str):
        """Read a file from disk and display its contents."""
        if not file_path:
            sys.stdout.write("Model did not provide a file path for ReadFile.\n")
            return

        if not os.path.isfile(file_path):
            msg = f"File not found: {file_path}"
            sys.stdout.write(f"{msg}\n")
            self._append_tool_result(tool_call_id, msg)
            return

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
                file_content = fh.read()
            sys.stdout.write(f"\n─── {file_path} ───\n")
            sys.stdout.write(file_content)
            sys.stdout.write("\n─── end ───\n")
            self._append_tool_result(tool_call_id, file_content)
        except OSError as io_err:
            sys.stdout.write(f"Read failed: {io_err}\n")
            self._append_tool_result(tool_call_id, f"Read failed: {io_err}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _normalize_command_display(self, command: str) -> str:
        """Collapse irregular whitespace; preserve semantic content."""
        try:
            return " ".join(shlex.split(command))
        except ValueError:
            return command.strip()

    def _user_confirmed_execution(self, prompt: str) -> bool:
        """Require explicit 'y'/'yes' — default-deny prevents accidental runs."""
        try:
            response = input(prompt).strip().lower()
        except (KeyboardInterrupt, EOFError):
            return False
        return response in {"y", "yes"}

    def _execute_shell_command(self, command: str, tool_call_id: str):
        """Run the confirmed command in the platform-appropriate shell."""
        try:
            if os.name == "nt":
                proc = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", command],
                    text=True,
                )
            else:
                proc = subprocess.run(command, shell=True, text=True)
            self._append_tool_result(tool_call_id, f"Exit code: {proc.returncode}")
        except Exception as exec_err:
            sys.stdout.write(f"Execution error: {exec_err}\n")
            self._append_tool_result(tool_call_id, f"Error: {exec_err}")

    def _append_tool_result(self, tool_call_id: str, result_text: str):
        """Record tool output so the model has execution feedback on the next turn."""
        self.conversation_history.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result_text,
        })

    @staticmethod
    def _message_to_history_dict(message) -> dict:
        """Serialize an OpenAI Message object to a plain dict for conversation history."""
        history_entry: dict = {"role": message.role, "content": message.content}
        if message.tool_calls:
            history_entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]
        return history_entry
