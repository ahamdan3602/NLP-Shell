import sys
import os
import subprocess
import shlex


listOfCommands = ["exit", "echo", "type", "pwd", "cd"]

def main():
    # TODO: Uncomment the code below to pass the first stage
    # Test
   
    while True:
        sys.stdout.write("$ ")
        userCommand = input()

        args = userCommand.split()
        if ">" in args or "1>" in args:
            handleStdout(userCommand)
            continue
        elif "2>" in args:
            handleStderr(userCommand)
            continue

        command = userCommand.split(" ")[0]


        match (command):
            case "exit":
                handleExit(userCommand)
            case "echo":
                handleEcho(userCommand)
            case "type":
                handleType(userCommand)
            case "pwd":
                handlePWD(userCommand)
            case "cd":
                handleCD(userCommand)
            case _:
                runExecutable(userCommand)
        pass


def runExecutable(userCommand):
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


def handleCD(userCommand):
    '''
    Checks if the given path actually exists in OS.
    If path exists then we update cwd accordingly
    '''
    path = userCommand.split(" ")[1]

    if os.path.exists(path) and os.path.isdir(path):
        os.chdir(path)

    elif "~" in path:
        home_dir = os.environ.get("HOME", "")
        os.chdir(home_dir)

    else:
        sys.stdout.write(f"{path}: No such file or directory \n")


def handlePWD(userCommand): 
    sys.stdout.write(f"{os.getcwd()}\n")


def handleStderr(userCommand):
    symbol = "2>"
    parts = userCommand.split(symbol, 1)

    if len(parts) < 2:
        sys.stdout.write('Syntax error: no output file provided \n')
    
    cmd_part = parts[0].strip()
    output_file = parts[1].strip()

    if not output_file:
        sys.stdout.write("Syntax error: missing output file name")
    

    cmd_tokens = cmd_part.split()

    if not cmd_tokens:
        sys.stdout.write("Syntax error: missing command before redirect")
    
    if cmd_tokens[0] == "echo":
        handleEcho(cmd_part)
        try:
            with open(output_file, "w") as f:
                f.write("")
        except e:
            sys.stdout.write("Error")
        return

    
    res = subprocess.run(cmd_tokens,  capture_output=True, text=True)

    if res.stderr:
        try:
            with open(output_file, "a") as f:
                f.write(res.stderr)
        except FileNotFoundError:
            sys.stdout.write(f"{cmd_tokens[0]}: command not found\n")




def handleStdout(userCommand):
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
        sys.stdout.write('Syntax error: missing command before redirection\n')
        return
    
    if cmd_tokens[0] == "echo":
        output = " ".join(cmd_tokens[1:]).strip()

        if (output.startswith("'") and output.endswith("'")) or (output.startswith('"') and output.endswith('"')):
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


def handleType(userCommand):
    cmd = userCommand.split(" ")[1] if len(userCommand.split(" ")) > 1 else ""
    if cmd in listOfCommands:
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
 
def handleEcho(userCommand):
    try:
        tokens = shlex.split(userCommand)

        args = tokens[1:]

        output = " ".join(args)

        sys.stdout.write(f"{output}\n")

    except ValueError as e:
        sys.stderr.write(f"Error parsing command: {e}\n")


def handleExit(userCommand):
    cmdStus = userCommand.split(" ")
    cmd = cmdStus[0]
    statusCode = 0 if len(cmdStus) == 1 else int(cmdStus[1])

    sys.exit(statusCode)

if __name__ == "__main__":
    main()
