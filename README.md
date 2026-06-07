# NLP-Shell

An interactive command-line shell that understands natural language. Type a plain English request and the shell routes it to an AI backend that generates and executes the right command — with your confirmation before anything runs.

## Features

- Standard shell built-ins: `echo`, `cd`, `pwd`, `type`, `clear`, `exit`
- stdout / stderr redirection (`>`, `1>`, `2>`)
- PATH-resolved executable dispatch
- **SmartShell** — natural-language → shell command via Claude (OpenRouter)
  - `Bash` tool: generate and run shell commands
  - `WriteFile` tool: generate and write file content
  - `ReadFile` tool: read and display any file
  - Multi-turn conversation history within a session
  - Safety gate blocks catastrophically destructive commands before confirmation

## Requirements

- Python 3.10+
- An [OpenRouter](https://openrouter.ai) API key

## Setup

**1. Clone and enter the repo**

```bash
git clone <repo-url>
cd NLP-Shell
```

**2. Create and activate a virtual environment**

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

**3. Install dependencies**

```bash
pip install openai python-dotenv
```

**4. Configure environment variables**

Create a `.env` file in the project root:

```ini
OPENROUTER_CLAUDE_API_KEY=sk-or-v1-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=anthropic/claude-haiku-4-5
```

Get your key at [openrouter.ai/keys](https://openrouter.ai/keys). Any OpenRouter-supported model works.

**5. Run**

```bash
cd app
python app.py
```

## Usage

```
SmartShell[app]$ help                   # list built-ins
SmartShell[app]$ cd ..                  # change directory
SmartShell[app]$ echo "hello"           # echo
SmartShell[app]$ git status             # any PATH executable

# Enter SmartShell loop (multi-turn AI session)
SmartShell[app]$ smartshell

# One-shot inline query
SmartShell[app]$ smartshell list all Python files recursively

# Natural language is auto-routed — no prefix needed
SmartShell[app]$ show me disk usage for this directory
SmartShell[app]$ write a hello world script to hello.py
```

Inside SmartShell, the AI proposes a command before running anything:

```
SmartShell> find all .log files older than 7 days

Generated command:
  find . -name "*.log" -mtime +7

Run this command? [y/N]
```

Type `exit` or press `Ctrl-C` to return to the main shell from SmartShell.

## Project Structure

```
app/
  app.py            # Shell REPL and built-in handlers
  nlp_processor.py  # Pure NLP pipeline (tokenize → intent → entities → safety)
  smartshell.py     # LLM integration and tool dispatch
.env                # API credentials (not committed)
```
