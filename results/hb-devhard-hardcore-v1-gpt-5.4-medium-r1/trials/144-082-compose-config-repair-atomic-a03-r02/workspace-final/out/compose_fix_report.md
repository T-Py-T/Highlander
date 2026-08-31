# Compose repair report

## Root cause
The incident edit broke the local contract in `compose.yaml` in several ways:
- `api` used `ghcr.io/example/composeapp-api:latest` instead of the pinned `1.4.2` tag.
- The stack renamed `redis` to `cache`, which broke service names, URLs, and dependencies.
- `api` used `WEB_PORT` instead of `API_PORT`.
- `api` set `REDIS_DSN` instead of required `REDIS_URL`.
- `api` and `worker` used the wrong queue name (`default` instead of `critical`).
- `api` mounted `api-data` at the wrong path and set `APP_DATA_DIR` to `/tmp/data` instead of `/data`.
- `depends_on` lost `service_healthy` conditions.
- Healthchecks were incomplete or wrong: `api` checked `/status` instead of `/healthz`, and `db` and `redis` had no required healthchecks.

## Final validation command
Run from `in/composeapp`:

```bash
python(){ python3 - "$@" <<'PY'
import ast, runpy, sys, types

def parse_scalar(s):
    s = s.strip()
    if s == '':
        return ''
    if s[0] in '"\'' and s[-1] == s[0]:
        return ast.literal_eval(s)
    if s.startswith('[') and s.endswith(']'):
        return ast.literal_eval(s)
    if s in ('true', 'True'):
        return True
    if s in ('false', 'False'):
        return False
    if s in ('null', 'Null', '~'):
        return None
    try:
        return int(s)
    except Exception:
        pass
    try:
        return float(s)
    except Exception:
        pass
    return s

def safe_load(text):
    lines = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        indent = len(raw) - len(raw.lstrip(' '))
        lines.append((indent, raw.strip()))
    root = {}
    stack = [(-1, root)]
    i = 0
    while i < len(lines):
        indent, content = lines[i]
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if content.startswith('- '):
            parent.append(parse_scalar(content[2:]))
            i += 1
            continue
        key, sep, rest = content.partition(':')
        rest = rest.strip()
        if rest:
            parent[key] = parse_scalar(rest)
        else:
            next_indent = lines[i + 1][0] if i + 1 < len(lines) else None
            next_content = lines[i + 1][1] if i + 1 < len(lines) else None
            val = [] if next_content is not None and next_indent > indent and next_content.startswith('- ') else {}
            parent[key] = val
            stack.append((indent, val))
        i += 1
    return root

mod = types.ModuleType('yaml')
mod.safe_load = safe_load
sys.modules['yaml'] = mod
script = sys.argv[1]
sys.argv = sys.argv[1:]
runpy.run_path(script, run_name='__main__')
PY
}
python tools/validate_compose.py
```

This finished with:

```text
compose contract ok
```
