import sys
import os
import subprocess
import shlex


listOfCommands = ["exit", "echo", "type", "pwd"]

def main():
    # TODO: Uncomment the code below to pass the first stage
    # Test
   
    while True:
        sys.stdout.write("$ ")
        userCommand = input()
        
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


def handleCD(userCommand):
    '''
    Checks if the given path actually exists in OS.
    If path exists then we update cwd accordingly
    '''
    path = userCommand.split(" ")[1]

    if os.path.exists(path) and os.path.idir(path):
        os.chdir(path)
    else:
        sys.stdout.write(f"{path}: No such file or directory \n")

def runExecutable(userCommand):
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    parts = userCommand.strip().split()

    if not parts:
        return  # Ignore empty command

    command = parts[0]
    args = parts  # includes program name and arguments

    for directory in path_dirs:
        full_path = os.path.join(directory, command)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            subprocess.run([command] + args[1:])
            return

    sys.stdout.write(f"{command}: command not found\n")

def handlePWD(userCommand): 
    sys.stdout.write(f"{os.getcwd()}\n")


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
    output = userCommand.split(" ")[1:]
    sys.stdout.write(" ".join(output) + '\n')

def handleExit(userCommand):
    cmdStus = userCommand.split(" ")
    cmd = cmdStus[0]
    statusCode = 0 if len(cmdStus) == 1 else int(cmdStus[1])

    sys.exit(statusCode)

if __name__ == "__main__":
    main()
