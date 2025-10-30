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


def handleRedirect(userCommand):
    cmds = userCommand.split(" ")
    '''
    ls /tmp/baz > /tmp/boo/baz.md
    [ls, /tmp/baz, >, /tmp/foo/baz/md]
    
    '''
    path_dir = cmds[1]
    path_exc = cmmds[-1]
    if not os.path.exists(path_dir) and os.path.exists(path_exc):
        return

    # if os.path.isdir(path_dir):
    if '>' in cmds:
        output = os.popen('ls /etc/services').read()
        path_for_exc = path_exc.split("/")[:-1]
        curr_dir = os.getcwd()
        os.chdir("".join(path_for_exc))
        subprocess.run([])
        
         
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
