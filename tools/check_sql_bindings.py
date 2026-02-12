import re
from pathlib import Path


def main():
    base = Path(__file__).resolve().parents[1]
    py_files = list(base.glob('*.py'))
    py_files += list((base / 'tools').glob('*.py'))
    issues = []
    for p in py_files:
        s = p.read_text(encoding='utf-8')

    # Match cursor.execute('SQL', (params)) with single-quoted SQL literals
    pattern = re.compile(r"cursor\.execute\(\s*(['\"][\s\S]*?['\"])\s*,\s*(\([\s\S]*?\)|\[[\s\S]*?\])\s*\)")

    issues = []
    for m in pattern.finditer(s):
        sql_literal = m.group(1)
        params_literal = m.group(2)

        # crude removal of surrounding quotes for SQL literal
        sql_content = sql_literal[1:-1]
        qcount = sql_content.count('?')

        params = params_literal.strip()
        inner = params[1:-1].strip()
        if inner == '':
            plen = 0
        else:
            # approximate count: split top-level by commas
            parts = [p for p in re.split(r',\s*(?![^\(]*\))', inner) if p.strip()]
            plen = len(parts)

        from pathlib import Path


        def find_balanced(s: str, start: int) -> int:
            """Find index of closing parenthesis matching the opening at start."""
            stack = []
            for i in range(start, len(s)):
                ch = s[i]
                if ch == '(':
                    stack.append(ch)
                elif ch == ')':
                    stack.pop()
                    if not stack:
                        return i
            return -1


        def main():
            p = Path(__file__).resolve().parents[1] / "database.py"
            s = p.read_text(encoding="utf-8")

                idx = 0
            while True:
                idx = s.find('cursor.execute(', idx)
                if idx == -1:
                    break
                open_paren = s.find('(', idx + len('cursor.execute'))
                if open_paren == -1:
                    idx += 1
                    continue
                close = find_balanced(s, open_paren)
                if close == -1:
                    idx = open_paren + 1
                    continue
                call = s[open_paren + 1:close].strip()
                # split by first comma not inside quotes/parens
                # crude parser: find comma separating args
                arg_comma = None
                in_single = in_double = False
                paren_level = 0
                for i, ch in enumerate(call):
                    if ch == "'" and not in_double:
                        in_single = not in_single
                    elif ch == '"' and not in_single:
                        in_double = not in_double
                    elif ch == '(' and not in_single and not in_double:
                        paren_level += 1
                    elif ch == ')' and not in_single and not in_double:
                        paren_level -= 1
                    elif ch == ',' and not in_single and not in_double and paren_level == 0:
                        arg_comma = i
                        break

                if arg_comma is None:
                    idx = close + 1
                    continue

                sql_literal = call[:arg_comma].strip()
                params_literal = call[arg_comma + 1:].strip()

                # Extract SQL content if literal
                sql_content = None
                if sql_literal.startswith(('"', "'")) and sql_literal.endswith(('"', "'")):
                    sql_content = sql_literal[1:-1]
                else:
                    # skip non-literal SQL
                    idx = close + 1
                    continue

                qcount = sql_content.count('?')

                # params literal: count top-level commas
                plen = None
                if params_literal.startswith('(') and params_literal.endswith(')'):
                    inner = params_literal[1:-1].strip()
                    if inner == '':
                        plen = 0
                    else:
                        parts = [p for p in inner.split(',') if p.strip()]
                        plen = len(parts)

                if plen is not None and qcount != plen:
                    lineno = s.count('\n', 0, idx) + 1
                    issues.append((str(p), lineno, qcount, plen, sql_content.strip(), params_literal.strip()))

                idx = close + 1

            if not issues:
                print('No obvious literal mismatches found')
            else:
                for path, ln, q, p_len, sql, params in issues:
                    print(f"File {path} Line {ln}: placeholders={q}, params={p_len}\nSQL: {sql}\nParams: {params}\n")


        if __name__ == '__main__':
            main()
