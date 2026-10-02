"""Repository checks for the AI Agents in Action, Second Edition sample code.

Run from anywhere inside the repository:

    python tools/check_repo.py              # static checks; standard library only
    python tools/check_repo.py --servers    # start every MCP server once (no API key needed)
    python tools/check_repo.py --smoke      # run a few examples against the OpenAI API (paid)

--servers doubles as a one-time warm-up: it downloads every MCP server the
examples launch through npx or uvx, so the first real run starts quickly.
Add --cold to measure start-up against empty npm and uv caches instead.

Every finding is labeled with the ID it guards from the Spanish-edition
defect report (B blocker, M major, m minor, P prerequisite, V version drift,
Q question, X found while fixing the report).
"""

import argparse
import ast
import asyncio
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tokenize
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".venv", "venv", "env", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
TEXT_SUFFIXES = {".py", ".md", ".html", ".txt", ".json", ".yml", ".yaml", ".toml", ".mmd"}
MAX_FILE_BYTES = 5 * 1024 * 1024

# MCP servers the examples may launch, and how long a cold start may take
ALLOWED_PACKAGES = {
    "@modelcontextprotocol/server-filesystem",
    "@modelcontextprotocol/server-memory",
    "@modelcontextprotocol/server-sequential-thinking",
    "@brave/brave-search-mcp-server",
    "chroma-mcp",
}
PINNED_NPX = re.compile(r"^(@[\w.-]+/)?[\w.-]+@\d[\w.-]*$")
PINNED_UVX = re.compile(r"^[\w.-]+(@|==)\d[\w.-]*$")

TYPOS_IN_NAMES = ["monitroing", "agent__", "soluriont", "vecotr"]
TYPOS_IN_TEXT = ["soruce", "ouput", "atleast", "braching", "Critque", "end of the end", "we there is", "closed the first and"]

# Import name -> distribution name, where the two differ
DISTRIBUTIONS = {
    "agents": "openai-agents",
    "sklearn": "scikit-learn",
    "dotenv": "python-dotenv",
    "phoenix": "arize-phoenix-otel",  # the examples import phoenix.otel
    "openinference": "openinference-instrumentation",
}
REQUIRED_ENV = ["OPENAI_API_KEY", "BRAVE_API_KEY", "OPENAI_DEFAULT_MODEL"]

# Header comments that name a file other than their own, on purpose
HEADER_NOTES = {
    "chapter_03/01_complete_agent.py": "named as in the chapter 3 text (author to confirm)",
    "chapter_03/01_complete_mcp_server.py": "named as in the chapter 3 text (author to confirm)",
    "chapter_08/02_app.py": "named as in the chapter 8 text (author to confirm)",
}


class Report:
    def __init__(self):
        self.failures = []
        self.notes = []

    def fail(self, check_id, where, message):
        self.failures.append((check_id, where, message))

    def note(self, check_id, where, message):
        self.notes.append((check_id, where, message))

    def print(self, title):
        print(f"\n{title}")
        for check_id, where, message in sorted(self.failures):
            print(f"  FAIL [{check_id}] {where}: {message}")
        for check_id, where, message in sorted(self.notes):
            print(f"  note [{check_id}] {where}: {message}")
        if not self.failures:
            print("  all checks passed")
        return 1 if self.failures else 0


# ---------------------------------------------------------------- file discovery

def tracked_files():
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
        files = [ROOT / p for p in out.decode("utf-8").split("\0") if p]
        return [f for f in files if f.exists()]
    except (OSError, subprocess.CalledProcessError):
        files = []  # not a git checkout (for example a downloaded ZIP)
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            files.extend(Path(dirpath) / f for f in filenames)
        return files


def rel(path):
    return path.relative_to(ROOT).as_posix()


def read_text(path):
    return path.read_text(encoding="utf-8", errors="replace")


def line_of(text, index):
    return text.count("\n", 0, index) + 1


def parse(path, report):
    try:
        return ast.parse(read_text(path), filename=rel(path))
    except SyntaxError as e:
        report.fail("syntax", f"{rel(path)}:{e.lineno}", e.msg)
        return None


# ---------------------------------------------------------------- MCP launch discovery

def literal(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError, TypeError):
        return None


COMPUTED = "<computed>"


def literal_list(node):
    """Literal list elements, with computed ones (paths built at run time) as a placeholder."""
    if not isinstance(node, (ast.List, ast.Tuple)):
        return literal(node)
    return [v if isinstance(v := literal(e), str) else COMPUTED for e in node.elts]


def mcp_launches(path, tree):
    """Yield (line, call, command, args) for every MCPServerStdio(...) call."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
        if name != "MCPServerStdio":
            continue
        params = next((k.value for k in node.keywords if k.arg == "params"), None)
        command, args = None, None
        if isinstance(params, ast.Dict):
            for key, value in zip(params.keys, params.values):
                key = literal(key) if key is not None else None
                if key == "command":
                    command = literal(value)
                elif key == "args":
                    args = literal_list(value)
        elif isinstance(params, ast.Call):
            for k in params.keywords:
                if k.arg == "command":
                    command = literal(k.value)
                elif k.arg == "args":
                    args = literal_list(k.value)
        yield node.lineno, node, command, args


def package_spec(command, args):
    """Return the package argument of an npx or uvx launch."""
    takes_value = {"--with", "--from", "--python", "-p", "--index-url"}
    skip_next = False
    for arg in args or []:
        if skip_next:
            skip_next = False
            continue
        if arg in takes_value:
            skip_next = True
            continue
        if arg.startswith("-") or arg == COMPUTED:
            continue
        return arg
    return None


def package_name(spec):
    if spec.startswith("@"):
        scope, _, rest = spec[1:].partition("/")
        return "@" + scope + "/" + re.split(r"@|==", rest)[0]
    return re.split(r"@|==", spec)[0]


# ---------------------------------------------------------------- static checks

def check_python_files(py_files, report):
    trees = {}
    for path in py_files:
        if path.stat().st_size == 0:
            if path.name != "__init__.py":
                report.fail("B-05", rel(path), "empty file")
            continue
        tree = parse(path, report)
        if tree is not None:
            trees[path] = tree
    return trees


def check_unreachable(path, tree, report):
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            stmts = getattr(node, field, None)
            if not isinstance(stmts, list):
                continue
            for first, second in zip(stmts, stmts[1:]):
                if isinstance(first, (ast.Return, ast.Raise, ast.Continue, ast.Break)):
                    report.fail("M-02", f"{rel(path)}:{second.lineno}", "unreachable statement after return/raise")


def check_braces_without_f(path, tree, report):
    in_fstring = {id(v) for n in ast.walk(tree) if isinstance(n, ast.JoinedStr) for v in n.values}
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in in_fstring:
            for m in re.finditer(r"\{([^{}\n]+)\}", node.value):
                expr = m.group(1)
                if "(" not in expr:
                    continue
                try:
                    ast.parse(expr, mode="eval")
                except SyntaxError:
                    continue
                report.fail("M-01", f"{rel(path)}:{node.lineno}", f"'{{{expr}}}' in a string without the f prefix")


def check_module_level_streams(path, tree, report):
    def visit(node, top_level):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            return
        if top_level and isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute) and f.attr == "run_streamed" and isinstance(f.value, ast.Name) and f.value.id == "Runner":
                report.fail("M-04", f"{rel(path)}:{node.lineno}", "Runner.run_streamed() outside a coroutine")
        for child in ast.iter_child_nodes(node):
            visit(child, top_level)

    for stmt in tree.body:
        visit(stmt, True)


def check_string_joins(path, report):
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(read_text(path)).readline))
    except (tokenize.TokenError, SyntaxError):
        return
    skip = {tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT}
    significant = [t for t in tokens if t.type not in skip]
    for left, right in zip(significant, significant[1:]):
        if left.type != tokenize.STRING or right.type != tokenize.STRING:
            continue
        a, b = literal_str(left.string), literal_str(right.string)
        if a and b and a[-1] in ".!?:;" and b[0].isalpha():
            report.fail("M-03/M-08", f"{rel(path)}:{left.start[0]}", f"missing space joining ...{a[-20:]!r} + {b[:20]!r}...")


def literal_str(token_text):
    try:
        value = ast.literal_eval(token_text)
    except (ValueError, SyntaxError):
        return None  # f-strings on Python 3.11 and earlier
    return value if isinstance(value, str) else None


def check_travel_forward(path, tree, report):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "travel_forward":
            func = ast.FunctionDef(**{**node.__dict__, "decorator_list": []})
            module = ast.fix_missing_locations(ast.Module(body=[func], type_ignores=[]))
            namespace = {}
            exec(compile(module, rel(path), "exec"), namespace)
            with open(os.devnull, "w") as devnull:
                stdout, sys.stdout = sys.stdout, devnull
                try:
                    result = namespace["travel_forward"](2000, 5)
                finally:
                    sys.stdout = stdout
            if "2005" not in str(result):
                report.fail("B-03", f"{rel(path)}:{node.lineno}", f"travel_forward(2000, 5) returned {result!r}")


def check_header(path, report):
    first = read_text(path).split("\n", 1)[0].strip()
    m = re.fullmatch(r"#\s*([\w./\\-]+\.py)", first)
    if not m:
        return
    named = m.group(1).replace("\\", "/")
    if named in (path.name, rel(path)):
        return
    if rel(path) in HEADER_NOTES:
        report.note("m-04", rel(path), f"header '# {named}' {HEADER_NOTES[rel(path)]}")
    else:
        report.fail("m-04", f"{rel(path)}:1", f"header names '{named}', not this file")


def check_with_name(path, tree, report):
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "with_name"
                and node.args and isinstance(literal(node.args[0]), str)):
            target = path.with_name(literal(node.args[0]))
            if not target.exists():
                report.fail("m-05", f"{rel(path)}:{node.lineno}", f"with_name target {target.name!r} does not exist")


def check_mcp_launches(trees, report):
    versions = defaultdict(set)
    for path, tree in trees.items():
        for line, call, command, args in mcp_launches(path, tree):
            where = f"{rel(path)}:{line}"
            if command not in ("npx", "uvx"):
                continue
            spec = package_spec(command, args)
            if spec is None:
                report.note("V", where, f"{command} launch with arguments that are not literals")
                continue
            name = package_name(spec)
            if name not in ALLOWED_PACKAGES:
                report.fail("B-01/B-02", where, f"unknown or non-existent package {spec!r}")
            pattern = PINNED_NPX if command == "npx" else PINNED_UVX
            if not pattern.match(spec):
                report.fail("V", where, f"{spec!r} is not pinned to an exact version")
            else:
                versions[name].add(spec)
            if not any(k.arg == "client_session_timeout_seconds" for k in call.keywords):
                report.fail("P-01", where, "no client_session_timeout_seconds (the first launch downloads the server)")
            if name == "chroma-mcp" and "--data-dir" in args and "persistent" not in args:
                report.fail("X-01", where, "--data-dir is ignored unless --client-type persistent is given")
    for name, specs in versions.items():
        if len(specs) > 1:
            report.fail("V", name, f"launched with different versions: {sorted(specs)}")


def check_text(files, report):
    for path in files:
        if path.suffix not in TEXT_SUFFIXES or rel(path).startswith("tools/"):
            continue
        text = read_text(path)
        for word in TYPOS_IN_TEXT:
            for m in re.finditer(re.escape(word), text):
                report.fail("m-02/m-03", f"{rel(path)}:{line_of(text, m.start())}", f"typo {word!r}")
        for m in re.finditer(r"contentReference\[oaicite", text):
            report.fail("m-06", f"{rel(path)}:{line_of(text, m.start())}", "ChatGPT citation marker")
        if path.suffix == ".py":
            for m in re.finditer(r"@anthropic/", text):
                report.fail("B-01/B-02", f"{rel(path)}:{line_of(text, m.start())}", "the @anthropic npm scope does not exist")
            for m in re.finditer(r'os\.environ\.get\(\s*"BRAVE_API_KEY"\s*,\s*""\s*\)', text):
                report.fail("M-10", f"{rel(path)}:{line_of(text, m.start())}", "an unset key silently becomes an empty string")
            if rel(path).startswith("chapter_09/"):
                for m in re.finditer(r'model="gpt-4o"', text):
                    report.fail("Q-03", f"{rel(path)}:{line_of(text, m.start())}", "the printed listings use gpt-5.1")


def check_layout(files, report):
    for path in files:
        name = rel(path)
        if any(t in name for t in TYPOS_IN_NAMES):
            report.fail("m-01", name, "typo in file name")
        if path.stat().st_size > MAX_FILE_BYTES:
            report.fail("m-07", name, f"{path.stat().st_size // 1_000_000} MB file in the book material")
        if path.suffix == ".pptx" or name.endswith(".claude/settings.local.json"):
            report.fail("m-07", name, "not book material")
        if path.name == ".env":
            report.fail("M-10", name, ".env must never be committed")
    for folder in ("demo_project", "chapter_12"):
        if (ROOT / folder).is_dir() and any(rel(f).startswith(folder + "/") for f in files):
            report.fail("m-07", folder, "move to extras/")


def requirement_lines(path):
    for raw in read_text(path).splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            yield line


def normalize(dist):
    return re.sub(r"[-_.]+", "-", dist).lower()


def check_requirements(files, trees, report):
    req_files = [f for f in files if f.name == "requirements.txt"]
    root_names = set()
    for req in req_files:
        for line in requirement_lines(req):
            if "==" not in line:
                report.fail("M-05", rel(req), f"{line!r} is not pinned with ==")
            name = normalize(re.split(r"[\[=<>!~ ;]", line, 1)[0])
            if req.parent == ROOT:
                root_names.add(name)
            if name == "mcp":
                m = re.search(r"==\s*(\d+)", line)
                if m and int(m.group(1)) >= 2:
                    report.fail("B-04", rel(req), "mcp 2.x removed FastMCP; the listings need mcp<2")
    local = {p.stem for p in trees} | {p.name for p in ROOT.iterdir() if p.is_dir()}
    missing = defaultdict(set)
    for path, tree in trees.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            else:
                continue
            for top in (n.split(".")[0] for n in names):
                if top in sys.stdlib_module_names or top in local or top == "__future__":
                    continue
                if normalize(DISTRIBUTIONS.get(top, top)) not in root_names:
                    missing[top].add(rel(path))
    for top, where in sorted(missing.items()):
        report.fail("M-05", "requirements.txt", f"'{top}' is imported by {len(where)} file(s) but not declared, e.g. {sorted(where)[0]}")


def load_jsonc(path):
    text = re.sub(r"^\s*//.*$", "", read_text(path), flags=re.M)
    return json.loads(re.sub(r",(\s*[}\]])", r"\1", text))


def check_vscode(report):
    launch, tasks = ROOT / ".vscode" / "launch.json", ROOT / ".vscode" / "tasks.json"
    if not launch.exists() or not tasks.exists():
        return
    labels = {}
    for task in load_jsonc(tasks).get("tasks", []):
        labels[task.get("label")] = task
        command = " ".join([task.get("command", "")] + task.get("args", []))
        if "--upgrade" in command:
            report.fail("M-06", ".vscode/tasks.json", f"task {task.get('label')!r} upgrades every package on each run")
    for config in load_jsonc(launch).get("configurations", []):
        if config.get("preLaunchTask") not in labels:
            report.fail("M-06", ".vscode/launch.json", f"{config.get('name')!r} does not install the requirements first")
        if config.get("type") == "python":
            report.fail("M-06", ".vscode/launch.json", f"{config.get('name')!r} uses the deprecated type 'python' (use 'debugpy')")


def check_readme(report):
    readme, license_file = ROOT / "README.md", ROOT / "LICENSE"
    if not readme.exists():
        return
    text = read_text(readme)
    if "Build a Deep Research Agent" in text:
        report.fail("M-07", "README.md", "names a different book")
    if license_file.exists() and read_text(license_file).lstrip().startswith("Apache License"):
        if re.search(r"license-MIT", text):
            report.fail("M-07", "README.md", "license badge says MIT; LICENSE is Apache 2.0")
    versions = set(re.findall(r"python-3\.(\d+)%2B", text)) | set(re.findall(r"Python \*{0,2}3\.(\d+)\+", text))
    if len(versions) > 1:
        report.fail("M-07", "README.md", f"asks for different Python versions: 3.{', 3.'.join(sorted(versions))}")


def check_env_example(trees, report):
    example = ROOT / ".env.example"
    if not example.exists():
        report.fail("M-10", ".env.example", "missing")
        return
    text = read_text(example)
    if not text.endswith("\n"):
        report.fail("M-10", ".env.example", "no trailing newline")
    declared = set(re.findall(r"^\s*#?\s*([A-Z][A-Z0-9_]*)\s*=", text, flags=re.M))
    required = set(REQUIRED_ENV)
    for tree in trees.values():
        for node in ast.walk(tree):
            if (isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load)
                    and isinstance(node.value, ast.Attribute) and node.value.attr == "environ"
                    and isinstance(literal(node.slice), str)):
                required.add(literal(node.slice))
    for key in sorted(required - declared):
        report.fail("M-10", ".env.example", f"{key} is needed by the examples but not declared")


def run_static():
    report = Report()
    files = tracked_files()
    py_files = [f for f in files if f.suffix == ".py" and not rel(f).startswith("tools/")]
    trees = check_python_files(py_files, report)
    for path, tree in trees.items():
        check_unreachable(path, tree, report)
        check_braces_without_f(path, tree, report)
        check_module_level_streams(path, tree, report)
        check_string_joins(path, report)
        check_travel_forward(path, tree, report)
        check_header(path, report)
        check_with_name(path, tree, report)
    check_mcp_launches(trees, report)
    check_text(files, report)
    check_layout(files, report)
    check_requirements(files, trees, report)
    check_vscode(report)
    check_readme(report)
    check_env_example(trees, report)
    print(f"Checked {len(py_files)} Python files and {len(files)} tracked files under {ROOT}")
    return report.print("Static checks")


# ---------------------------------------------------------------- --servers

def check_signatures(trees, report):
    """Every keyword argument passed to an Agents SDK name must exist in its signature."""
    import importlib
    import inspect

    for path, tree in trees.items():
        imported = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "agents":
                for a in node.names:
                    try:
                        imported[a.asname or a.name] = getattr(importlib.import_module(node.module), a.name)
                    except (ImportError, AttributeError) as e:
                        report.fail("API", rel(path), f"from {node.module} import {a.name}: {e}")
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f, target, label = node.func, None, None
            if isinstance(f, ast.Name) and f.id in imported:
                target, label = imported[f.id], f.id
            elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in imported:
                target, label = getattr(imported[f.value.id], f.attr, None), f"{f.value.id}.{f.attr}"
            if target is None:
                continue
            if hasattr(target, "__required_keys__"):  # TypedDict
                allowed = set(target.__required_keys__) | set(target.__optional_keys__)
                accepts_any = False
            else:
                try:
                    params = inspect.signature(target).parameters
                except (TypeError, ValueError):
                    continue
                allowed = set(params)
                accepts_any = any(p.kind is p.VAR_KEYWORD for p in params.values())
            for kw in node.keywords:
                if kw.arg and not accepts_any and kw.arg not in allowed:
                    report.fail("API", f"{rel(path)}:{node.lineno}", f"{label}() has no parameter {kw.arg!r}")


def distinct_servers(trees):
    """One entry per distinct npx/uvx package, plus every local FastMCP server file."""
    servers = {}
    for path, tree in trees.items():
        for line, call, command, args in mcp_launches(path, tree):
            if command not in ("npx", "uvx") or not args:
                continue
            spec = package_spec(command, args)
            if spec and spec not in servers:
                servers[spec] = (command, list(args), f"{rel(path)}:{line}")
    fastmcp = sorted(p for p, t in trees.items() if "FastMCP(" in read_text(p))
    return servers, fastmcp


def launch_args(command, args, scratch):
    """Swap directory arguments for a scratch folder so nothing in the repository is touched."""
    spec = package_spec(command, args)
    out = list(args[: args.index(spec) + 1])
    if package_name(spec) == "@modelcontextprotocol/server-filesystem":
        out.append(str(scratch))
    elif package_name(spec) == "chroma-mcp":
        out += ["--client-type", "persistent", "--data-dir", str(scratch / "chroma")]
    return out


async def start_server(label, params, timeout, calls=()):
    from agents.mcp import MCPServerStdio

    started = time.perf_counter()
    try:
        async with MCPServerStdio(name=label, params=params, client_session_timeout_seconds=timeout) as server:
            tools = [t.name for t in await server.list_tools()]
            for tool, arguments in calls:
                result = await server.call_tool(tool, arguments)
                if getattr(result, "isError", False):
                    raise RuntimeError(f"{tool} returned an error: {result.content}")
        return True, f"{time.perf_counter() - started:5.1f}s  {len(tools)} tools: {', '.join(sorted(tools))[:110]}"
    except BaseException as e:  # noqa: BLE001 - report every failure and keep going
        return False, f"{time.perf_counter() - started:5.1f}s  {type(e).__name__}: {str(e)[:160]}"


async def run_servers_async(cold):
    report = Report()
    files = tracked_files()
    py_files = [f for f in files if f.suffix == ".py" and f.stat().st_size and not rel(f).startswith("tools/")]
    trees = {p: t for p in py_files if (t := parse(p, report)) is not None}

    try:
        import agents  # noqa: F401
        from agents.mcp import MCPServerStdio  # noqa: F401
    except ImportError:
        print("Install the requirements first: pip install -r requirements.txt")
        return 2

    check_signatures(trees, report)
    try:
        from agents.models.default_models import get_default_model
        print(f"Default model for agents without model=: {get_default_model()}"
              f" (set OPENAI_DEFAULT_MODEL to change it)")
    except ImportError:
        pass

    servers, fastmcp = distinct_servers(trees)
    with tempfile.TemporaryDirectory(prefix="check_repo_") as tmp:
        scratch = Path(tmp)
        env = {"BRAVE_API_KEY": os.environ.get("BRAVE_API_KEY") or "check-repo-placeholder"}
        if cold:
            env.update({"npm_config_cache": str(scratch / "npm"), "UV_CACHE_DIR": str(scratch / "uv")})
            print("Using empty npm and uv caches (--cold)")
        print("\nMCP servers launched through npx/uvx:")
        for spec, (command, args, where) in sorted(servers.items()):
            params = {"command": command, "args": launch_args(command, args, scratch), "env": env}
            ok, detail = await start_server(spec, params, timeout=300)
            print(f"  {'ok  ' if ok else 'FAIL'} {spec:55s} {detail}")
            if not ok:
                report.fail("P-01", where, f"{spec} did not start: {detail.strip()}")

        print("\nLocal FastMCP servers (mcp run):")
        mcp_cli = shutil.which("mcp", path=str(Path(sys.executable).parent)) or shutil.which("mcp") or "mcp"
        calls = {"chapter_03/06_mcp_time_travel_tracker.py": [("record_event", {"entry": "check_repo"}), ("load_journal", {})]}
        for path in fastmcp:
            params = {"command": mcp_cli, "args": ["run", str(path)], "cwd": str(path.parent)}
            ok, detail = await start_server(rel(path), params, timeout=60, calls=calls.get(rel(path), ()))
            print(f"  {'ok  ' if ok else 'FAIL'} {rel(path):55s} {detail}")
            if not ok:
                report.fail("B-04", rel(path), detail.strip())
    return report.print("Server checks")


# ---------------------------------------------------------------- --smoke

SMOKE_RUNS = [
    # (script, stdin, timeout seconds, text the output must contain, extra env keys needed)
    ("chapter_04/07_input_output_guardrails.py", "", 300, "research plan length: ", []),
    ("chapter_05/02_ReAct_agent.py", "", 300, None, []),
    ("chapter_05/04_time_travel_agent.py", "", 600, None, []),
    ("chapter_06/02_RAG_agent_vector.py", "", 600, None, []),
    ("chapter_06/04_hybrid_memory_agent.py", "\n" * 5, 900, None, []),
    ("chapter_06/03_create_memories_mcp.py", "\n" * 5, 600, None, []),
    ("chapter_06/03_mcp_memory_agent.py", "\n" * 5, 600, None, []),
    ("chapter_09/04_deep_research_loop.py", "", 1200, None, ["BRAVE_API_KEY"]),
    ("chapter_09/07_task_loop.py", "", 1200, "Completed: 3/3", ["BRAVE_API_KEY"]),
    ("chapter_10/09_cognitive_agent.py", "", 1500, None, ["BRAVE_API_KEY"]),
    ("chapter_11/03_reasoning_planning_tips.py", "", 600, None, []),
]


def load_env_file():
    env = dict(os.environ)
    path = ROOT / ".env"
    if path.exists():
        for line in read_text(path).splitlines():
            m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$", line)
            if m and not line.lstrip().startswith("#"):
                env.setdefault(m.group(1), m.group(2).strip("'\""))
    return env


def run_smoke(only):
    env = load_env_file()
    if not env.get("OPENAI_API_KEY"):
        print("--smoke calls the OpenAI API: set OPENAI_API_KEY (or add it to .env) first")
        return 2
    env["PYTHONIOENCODING"] = "utf-8"
    report = Report()
    for script, stdin, timeout, expect, needs in SMOKE_RUNS:
        if only and not any(o in script for o in only):
            continue
        missing = [k for k in needs if not env.get(k)]
        if missing:
            print(f"  skip {script} (needs {', '.join(missing)})")
            continue
        started = time.perf_counter()
        try:
            proc = subprocess.run([sys.executable, script], cwd=ROOT, env=env, input=stdin, text=True,
                                  encoding="utf-8", errors="replace", capture_output=True, timeout=timeout)
            output, code = proc.stdout + proc.stderr, proc.returncode
        except subprocess.TimeoutExpired as e:
            output, code = e.stdout if isinstance(e.stdout, str) else "", "timeout"
        ok = code == 0 and (expect is None or expect in output)
        tail = " | ".join(output.strip().splitlines()[-3:])[:220]
        print(f"  {'ok  ' if ok else 'FAIL'} {script:50s} {time.perf_counter() - started:6.1f}s  {tail}")
        if not ok:
            report.fail("smoke", script, f"exit {code}; expected {expect!r}" if expect else f"exit {code}")
    return report.print("Smoke runs")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--servers", action="store_true", help="start every MCP server once (also warms the npm/uv caches)")
    parser.add_argument("--cold", action="store_true", help="with --servers: use empty npm and uv caches")
    parser.add_argument("--smoke", action="store_true", help="run a few examples against the OpenAI API (paid)")
    parser.add_argument("--only", nargs="*", help="with --smoke: run only scripts whose path contains one of these")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.servers:
        return asyncio.run(run_servers_async(args.cold))
    if args.smoke:
        return run_smoke(args.only)
    return run_static()


if __name__ == "__main__":
    sys.exit(main())
