
import argparse
import ast
import re
from datetime import datetime
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent


def parse_source(path):
    source = path.read_text(encoding='utf-8-sig')
    return source, ast.parse(source, filename=str(path))


def is_chat_view_file(path):
    try:
        _, tree = parse_source(path)
        names = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        return {'chat_dashboard', 'chat_room', 'chat_send_message'} <= names
    except (SyntaxError, UnicodeError, OSError):
        return False


def choose_one(paths, label, flag):
    unique = sorted(set(path.resolve() for path in paths))
    if len(unique) != 1:
        shown = '\n'.join(str(path) for path in unique) or '(none found)'
        raise ValueError(f'Could not choose one {label}. Found:\n{shown}\nRun again with {flag} and the correct path.')
    return unique[0]


def replace_chat_functions(original, tree, replacement):
    if '# CHAT FIX START --' in original:
        pattern = r'^# CHAT FIX START --[^\n]*\n[\s\S]*?^# CHAT FIX END\s*$'
        blocks = list(re.finditer(pattern, original, re.MULTILINE))
        if len(blocks) != 1:
            raise ValueError('The existing fix markers are incomplete or ambiguous.')
        result = original[:blocks[0].start()].rstrip() + '\n\n' + replacement + '\n' + original[blocks[0].end():].lstrip('\n')
        ast.parse(result)
        return result
    replacement_tree = ast.parse(replacement)
    names = {node.name for node in replacement_tree.body if isinstance(node, ast.FunctionDef)}
    required = {'chat_dashboard', 'chat_room', 'chat_send_message', 'chat_poll_messages'}
    existing = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    if not required <= existing:
        raise ValueError('The selected views file does not contain the expected chat functions.')
    lines = original.splitlines(keepends=True)
    remove = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            start = min([node.lineno] + [decorator.lineno for decorator in node.decorator_list])
            remove.update(range(start - 1, node.end_lineno))
    kept = ''.join(line for index, line in enumerate(lines) if index not in remove)
    # Old unused chat imports/constants may remain; unrelated app code is retained.
    result = kept.rstrip() + '\n\n' + replacement + '\n'
    ast.parse(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True, help='Folder containing manage.py')
    parser.add_argument('--views', type=Path, help='Exact views.py path (relative to --project or absolute)')
    parser.add_argument('--templates', type=Path, help='Template root containing chat/chat_base.html')
    parser.add_argument('--dry-run', action='store_true', help='Show destinations without writing')
    args = parser.parse_args()
    project = args.project.resolve()
    if not (project / 'manage.py').is_file():
        raise ValueError('--project must be the folder containing manage.py.')

    def resolve_override(value):
        return (project / value).resolve() if not value.is_absolute() else value.resolve()

    def allowed(path):
        ignored = {'.git', '.venv', 'venv', 'env', 'node_modules', '__pycache__'}
        return not any(part in ignored or part.startswith('chat_fix_backup_') for part in path.relative_to(project).parts)

    if args.views:
        views = resolve_override(args.views)
    else:
        views = choose_one([path for path in project.rglob('views.py') if allowed(path) and is_chat_view_file(path)], 'views.py', '--views')
    if args.templates:
        templates = resolve_override(args.templates)
    else:
        templates = choose_one([path.parent.parent for path in project.rglob('chat_base.html') if allowed(path) and path.parent.name == 'chat' and HERE not in path.parents], 'template root', '--templates')
    if not (templates / 'chat' / 'chat_base.html').is_file():
        raise ValueError('--templates must contain chat/chat_base.html.')
    if HERE in views.parents or HERE == templates or HERE in templates.parents:
        raise ValueError('Select the actual project files, not the downloaded fix folder.')
    # Backups are deliberately restricted to this project.
    views.relative_to(project)
    templates.relative_to(project)
    original, tree = parse_source(views)
    replacement = (HERE / 'chat_views_replacement.py').read_text(encoding='utf-8')
    updated = replace_chat_functions(original, tree, replacement)
    writes = [(views, updated.encode('utf-8'))]
    for source in sorted((HERE / 'templates').rglob('*.html')):
        writes.append((templates / source.relative_to(HERE / 'templates'), source.read_bytes()))
    print('Views:', views)
    print('Templates:', templates)
    print('Files to update:', len(writes))
    if args.dry_run:
        print('Dry run: no files changed.')
        return

    backup = project / ('chat_fix_backup_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir()
    existing = {}
    for target, _ in writes:
        existing[target] = target.exists()
        if target.exists():
            destination = backup / target.relative_to(project)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, destination)
    completed = []
    try:
        for target, content in writes:
            target.parent.mkdir(parents=True, exist_ok=True)
            completed.append(target)
            target.write_bytes(content)
    except Exception:
        for target in reversed(completed):
            if existing[target]:
                shutil.copy2(backup / target.relative_to(project), target)
            elif target.exists():
                target.unlink()
        raise
    (backup / 'RESTORE.txt').write_text('Restore backed-up files to the same relative paths under:\n' + str(project) + '\n', encoding='utf-8')
    print('Installed. Original files backed up at:', backup)
    print('Next, from your project folder: python manage.py check')
    print('Then restart Django and hard-refresh the browser (Ctrl+F5).')
    print('No model or database changes were installed.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, SyntaxError) as exc:
        sys.exit('Installation stopped: ' + str(exc))
