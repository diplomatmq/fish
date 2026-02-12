import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
files = list(ROOT.glob('*.py'))
files += list((ROOT / 'tools').glob('*.py'))

issues = []
for f in files:
    src = f.read_text(encoding='utf-8')
    try:
        tree = ast.parse(src)
    except Exception:
        continue

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # check function name endswith execute
            func = node.func
            name = None
            if isinstance(func, ast.Attribute):
                name = func.attr
            elif isinstance(func, ast.Name):
                name = func.id
            if name != 'execute':
                continue
            # get args
            if not node.args:
                continue
            sql_node = node.args[0]
            params_node = node.args[1] if len(node.args) > 1 else None
            if isinstance(sql_node, ast.Constant) and isinstance(sql_node.value, str) and params_node is not None:
                sql = sql_node.value
                qcount = sql.count('?')
                # count params if tuple or list
                plen = None
                if isinstance(params_node, (ast.Tuple, ast.List)):
                    plen = len(params_node.elts)
                elif isinstance(params_node, ast.Call):
                    # e.g., tuple([...]) not handled
                    plen = None
                elif isinstance(params_node, ast.Name):
                    plen = None
                # handle keyword args? ignore
                if plen is not None and qcount != plen:
                    lineno = sql_node.lineno
                    issues.append((str(f), lineno, qcount, plen, sql.strip()))

if not issues:
    print('No mismatches found')
else:
    for path, ln, q, p, sql in issues:
        print(f'File {path} Line {ln}: placeholders={q}, params={p}\nSQL: {sql}\n')
