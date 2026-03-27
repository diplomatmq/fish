import sys

file_path = r'c:\Users\dip663322o2244\PycharmProjects\fishbot\database.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

body_base_indent_original = None

for i in range(426, 844):
    line = lines[i]
    if not line.strip(): 
        lines[i] = '\n'
        continue
        
    stripped = line.lstrip()
    curr_indent = len(line) - len(stripped)
    
    if stripped.startswith('def ') and ' Database' not in line and 'class ' not in line:
        lines[i] = '    ' + stripped
        body_base_indent_original = None
    else:
        if body_base_indent_original is None:
            body_base_indent_original = curr_indent
        offset = curr_indent - body_base_indent_original
        if offset < 0 and stripped.startswith(')'):
             pass
        lines[i] = ' ' * (8 + offset) + stripped

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Done!')
