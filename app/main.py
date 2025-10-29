import sys
import os


listOfCommands = ["exit", "echo", "type"]

def main():
    # TODO: Uncomment the code below to pass the first stage
    # Test
   
    while True:
        sys.stdout.write("$ ")
        userCommand = input()
        
        command = userCommand.split(" ")[0]

        if command not in listOfCommands:
            sys.stdout.write(f"{userCommand}: command not found\n")
            continue

        if command == "exit":
            handleExit(userCommand)

        elif command == "echo":
            handleEcho(userCommand)

        elif command == "type":
            handleType(userCommand)

        pass

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
