import sys
import os
import subprocess
import shlex
from smartshell import ShellImplementation


class Shell:
    """Interactive shell with built-ins, redirection, and SmartShell integration."""

    def __init__(self):
        self.listOfCommands = ["exit", "echo", "type", "pwd", "cd", "help", "clear", "smartshell"]

    def showBanner(self):
        """Print a startup banner for the custom shell."""

        sys.stdout.write("\n")
        sys.stdout.write("=" * 52 + "\n")
        sys.stdout.write(" SmartShell | Custom Terminal\n")
        sys.stdout.write(" Built-ins: help, clear, smartshell\n")
        sys.stdout.write("=" * 52 + "\n\n")

    def getPrompt(self):
        """Build a dynamic prompt that includes the current working folder."""

        cwd_name = os.path.basename(os.getcwd()) or os.getcwd()
        return f"SmartShell[{cwd_name}]$ "

    def run(self):
        """Run the interactive shell loop and dispatch supported commands."""

        self.showBanner()

        while True:
            try:
                userCommand = input(self.getPrompt()).strip()
            except KeyboardInterrupt:
                sys.stdout.write("\n")
                continue
            except EOFError:
                sys.stdout.write("\n")
                break

            if not userCommand:
                continue

            args = userCommand.split()
            # Handle redirection before normal command dispatch.
            if ">" in args or "1>" in args:
                self.handleStdout(userCommand)
                continue
            elif "2>" in args:
                self.handleStderr(userCommand)
                continue

            command = userCommand.split(" ")[0]

            match (command):
                case "exit":
                    self.handleExit(userCommand)
                case "echo":
                    self.handleEcho(userCommand)
                case "type":
                    self.handleType(userCommand)
                case "pwd":
                    self.handlePWD(userCommand)
                case "cd":
                    self.handleCD(userCommand)
                case "help":
                    self.handleHelp()
                case "clear":
                    self.handleClear()
                case "smartshell":
                    ShellImplementation()
                case _:
                    self.runExecutable(userCommand)

    def runExecutable(self, userCommand):
        """Execute non-builtin commands by resolving them from PATH."""

        path_dirs = os.environ.get("PATH", "").split(os.pathsep)
        parts = shlex.split(userCommand)

        if not parts:
            return

        command = parts[0]
        args = parts

        for directory in path_dirs:
            full_path = os.path.join(directory, command)
            if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                subprocess.run([command] + args[1:])
                return

        sys.stdout.write(f"{command}: command not found\n")

    def handleCD(self, userCommand):
        """Change the current working directory."""

        parts = userCommand.split(maxsplit=1)

        if len(parts) == 1:
            default_home = os.environ.get("USERPROFILE") or os.environ.get("HOME") or os.getcwd()
            os.chdir(default_home)
            return

        path = parts[1].strip()

        if os.path.exists(path) and os.path.isdir(path):
            os.chdir(path)
        elif "~" in path:
            home_dir = os.environ.get("USERPROFILE") or os.environ.get("HOME", "")
            os.chdir(home_dir)
        else:
            sys.stdout.write(f"{path}: No such file or directory \n")

    def handlePWD(self, userCommand):
        """Print the current working directory."""

        sys.stdout.write(f"{os.getcwd()}\n")

    def handleStderr(self, userCommand):
        """Redirect command stderr to a file using 2>."""

        symbol = "2>"
        parts = userCommand.split(symbol, 1)

        if len(parts) < 2:
            sys.stdout.write("Syntax error: no output file provided \n")

        cmd_part = parts[0].strip()
        output_file = parts[1].strip()

        if not output_file:
            sys.stdout.write("Syntax error: missing output file name")

        cmd_tokens = cmd_part.split()

        if not cmd_tokens:
            sys.stdout.write("Syntax error: missing command before redirect")

        if cmd_tokens[0] == "echo":
            self.handleEcho(cmd_part)
            try:
                with open(output_file, "w") as f:
                    f.write("")
            except Exception as e:
                sys.stdout.write(f"Error: {e}\n")
            return

        res = subprocess.run(cmd_tokens, capture_output=True, text=True)

        if res.stderr:
            try:
                with open(output_file, "a") as f:
                    f.write(res.stderr)
            except FileNotFoundError:
                sys.stdout.write(f"{cmd_tokens[0]}: command not found\n")

    def handleStdout(self, userCommand):
        """Redirect command stdout to a file using > or 1>."""

        if "1>" in userCommand:
            symbol = "1>"
        else:
            symbol = ">"

        parts = userCommand.split(symbol, 1)

        if len(parts) < 2:
            sys.stdout.write("Syntax error: no output file provided \n")

        cmd_part = parts[0].strip()
        output_file = parts[1].strip()

        if not output_file:
            sys.stdout.write("Syntax error: missing output file name")
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
            with open(output_file, "w") as f:
                f.write(output + "\n")
            return

        try:
            with open(output_file, "a") as f:
                res = subprocess.run(cmd_tokens, capture_output=True, text=True)
                f.write(res.stdout)

                if res.stderr:
                    sys.stderr.write(res.stderr)

        except FileNotFoundError:
            sys.stdout.write(f"{cmd_tokens[0]}: command not found\n")

    def handleType(self, userCommand):
        """Report whether a command is a builtin or an executable in PATH."""

        cmd = userCommand.split(" ")[1] if len(userCommand.split(" ")) > 1 else ""
        if cmd in self.listOfCommands:
            sys.stdout.write(f"{cmd} is a shell builtin\n")
        else:
            path_env = os.getenv("PATH", "")
            path_dirs = path_env.split(os.pathsep)
            found = False

            for directory in path_dirs:
                file_path = os.path.join(directory, cmd)
                if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
                    print(f"{cmd} is {file_path}")
                    found = True
                    break
            if not found:
                sys.stdout.write(f"{cmd}: not found\n")

    def handleEcho(self, userCommand):
        """Print parsed echo arguments with shell-style tokenization."""

        try:
            tokens = shlex.split(userCommand)
            args = tokens[1:]
            output = " ".join(args)
            sys.stdout.write(f"{output}\n")
        except ValueError as e:
            sys.stderr.write(f"Error parsing command: {e}\n")

    def handleExit(self, userCommand):
        """Exit the shell with an optional numeric status code."""

        cmdStus = userCommand.split(" ")
        statusCode = 0 if len(cmdStus) == 1 else int(cmdStus[1])
        sys.exit(statusCode)

    def handleHelp(self):
        """Display supported built-in commands."""

        sys.stdout.write("Built-ins: exit, echo, type, pwd, cd, help, clear, smartshell\n")

    def handleClear(self):
        """Clear the terminal screen."""

        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")


def main():
    """Application entrypoint."""

    Shell().run()

if __name__ == "__main__":
    main()
