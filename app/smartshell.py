import os
import sys
import subprocess
import shlex
from dotenv import load_dotenv
import json
from openai import OpenAI

load_dotenv()

CLAUDE_API_KEY = os.getenv("OPENROUTER_CLAUDE_API_KEY")
CLAUDE_BASE_URL = os.getenv("OPENROUTER_BASE_URL")
CLAUDE_MODEL = os.getenv("OPENROUTER_MODEL")


class ShellImplementation:
    """Translate natural-language prompts into shell commands and execute safely."""

    def __init__(self):
        """Initialize API client and start a single SmartShell interaction."""

        if not CLAUDE_API_KEY:
            raise RuntimeError("API_KEY is not set.")
            
        self.client = OpenAI(
            api_key=CLAUDE_API_KEY,
            base_url=CLAUDE_BASE_URL
        )
        sys.stdout.write("smartshell enabled.\n")

        self.process_input()
    

    def call_cmd(self, command):
        """Ask for confirmation before executing the generated shell command."""

        sys.stdout.write("Would you like to run this command?\n")
        user_input = input().lower()

        if user_input == "yes" or user_input == "y":
            try: 
                # Use PowerShell on Windows so shell built-ins resolve correctly.
                if os.name == "nt":
                    subprocess.run(["powershell", "-NoProfile", "-Command", command])
                else:
                    subprocess.run(command, shell=True)
            except Exception as e:
                sys.stdout.write(f"Error: {e}\n")





    def display_cmd(self, command):
        """Display the model-generated command before optional execution."""

        cmd = shlex.split(command)

        output = " ".join(cmd)
        sys.stdout.write(f"{output}\n")

        self.call_cmd(output)



    def process_input(self):
        """Collect user prompt, request a command from the model, and dispatch it."""

        userCommand = input("What command would you like to run? \n").strip()
        if not userCommand:
            sys.stdout.write("No prompt provided.\n")
            return

        messages = [{"role": "user", "content": userCommand}]

        chat = self.client.chat.completions.create(
            model=CLAUDE_MODEL,
            messages=messages,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "Bash",
                        "description": "Execute a shell command",
                        "parameters": {
                            "type": "object",
                            "required": ["command"],
                            "properties": {
                                "command": {
                                    "type": "string",
                                    "description": "The command to execute"
                                }
                            }
                        }
                    }
                }
            ],
            max_tokens=500
        )


        if not chat.choices or len(chat.choices) == 0: 
            raise RuntimeError("no choices present in response")

        for choice in chat.choices:
            message = choice.message

            if message.tool_calls == None:
                break
            messages.append(message)


            for tool in message.tool_calls:
                fn_name = tool.function.name

                if fn_name == "Bash":
                    args = json.loads(tool.function.arguments)
                    res = self.display_cmd(args["command"])


        