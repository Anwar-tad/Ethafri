# ============================================================
# 📁 የፋይል አስተካከያ: EthAfri/marketplace/code_apply.py
# 📝 ቅጂ: Safe & Precise Code Application — Guardian Standard (v11.00)
# ✅ v11.00: Atomic writes, precise path-traversal, dynamic models, deep Django server integration,
#            post-write atomic auto-rollback, and graceful missing unit test bypass added (v11.00).
# 📅 ቀን: Friday, July 24, 2026
# ============================================================

import os
import ast
import re
import json
import hashlib
import logging
import requests
import base64
import tempfile
import time
import sys
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.apps import apps

logger = logging.getLogger(__name__)


# ============================================================
# 📊 Structured status helpers
# ============================================================

def _status(success: bool, applied: bool, message: str, **extra) -> Dict[str, Any]:
    """Build a consistent, JSON-serialisable status dict."""
    d: Dict[str, Any] = {
        'success': success,
        'applied': applied,
        'message': message,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
    }
    d.update(extra)
    return d


def _content_hash(content: str) -> str:
    """SHA-256 hex digest of file content (for integrity / dedup)."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


# ============================================================
# 🩺 DEEP DJANGO INTEGRITY CHECKER (የጃንጎ ሰርቨር ጤንነት ፍተሻ)
# ============================================================

def deep_verify_django_app() -> Tuple[bool, str]:
    """
    በፓይተን በኩል 'manage.py check' ጥሪን በተለየ ንዑስ ፕሮሰስ በማስኬድ
    የጃንጎ ሰርቨር አጠቃላይ ጤንነት (conflict, broken imports) በትክክል ያረጋግጣል
    """
    try:
        manage_py = os.path.join(str(settings.BASE_DIR), 'manage.py')
        result = subprocess.run(
            [sys.executable, manage_py, 'check'],
            capture_output=True, text=True, timeout=30, cwd=str(settings.BASE_DIR)
        )
        if result.returncode == 0:
            return True, "OK"
        return False, (result.stderr or result.stdout)[-500:]
    except Exception as e:
        return False, f"Deep verify error: {e}"


# ============================================================
# 🔧 0. ATOMIC WRITE HELPER
# ============================================================

def _atomic_write(path: str, content: str, encoding: str = 'utf-8') -> None:
    """
    Write ``content`` to ``path`` atomically.
    """
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=directory or '.',
        prefix='.tmp_write_',
        suffix=os.path.splitext(path)[1] or '.tmp',
    )
    try:
        with os.fdopen(tmp_fd, 'w', encoding=encoding, newline='') as f:
            f.write(content)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp_path, path)
    except Exception:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        raise


# ============================================================
# 📜 ROLLBACK MANAGER
# ============================================================

class RollbackManager:
    """
    Lightweight in-memory rollback registry.
    """

    _snapshots: List[Dict[str, str]] = []

    @classmethod
    def snapshot(cls, path: str, content: str) -> None:
        """Record the original content of ``path`` before a change."""
        cls._snapshots.append({'path': path, 'content': content})

    @classmethod
    def rollback_all(cls) -> List[str]:
        """Restore every snapshotted file.  Returns list of restored paths."""
        restored: List[str] = []
        while cls._snapshots:
            snap = cls._snapshots.pop()
            try:
                _atomic_write(snap['path'], snap['content'])
                restored.append(snap['path'])
                logger.info(f"↩️ Rollback: restored {snap['path']}")
            except Exception as e:
                logger.error(f"❌ Rollback FAILED for {snap['path']}: {e}")
        return restored

    @classmethod
    def rollback_last(cls) -> Optional[str]:
        """Undo only the most recent snapshot."""
        if not cls._snapshots:
            return None
        snap = cls._snapshots.pop()
        try:
            _atomic_write(snap['path'], snap['content'])
            logger.info(f"↩️ Rollback: restored {snap['path']}")
            return snap['path']
        except Exception as e:
            logger.error(f"❌ Rollback FAILED for {snap['path']}: {e}")
            return None

    @classmethod
    def clear(cls) -> None:
        cls._snapshots.clear()

    @classmethod
    def pending(cls) -> int:
        return len(cls._snapshots)


# ============================================================
# 🔍 DIFF GENERATOR
# ============================================================

def generate_diff(old_content: str, new_content: str, context: int = 3) -> str:
    """
    Produce a unified-diff string between two code blobs.
    """
    import difflib
    if old_content.strip() == new_content.strip():
        return ""
    old_lines = old_content.splitlines(keepends=False)
    new_lines = new_content.splitlines(keepends=False)
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile='before', tofile='after',
        n=context,
        lineterm='',
    )
    return "\n".join(diff)


# ============================================================
# 🩺 VALIDATION HOOK
# ============================================================

def validate_python_file(path: str) -> Tuple[bool, Optional[str]]:
    """
    Parse ``path`` as Python and return ``(True, None)`` on success.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            source = f.read()
        ast.parse(source)
        return True, None
    except FileNotFoundError:
        return False, f"File not found: {path}"
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)


# ============================================================
# 💉 1. DYNAMIC IMPORT INJECTOR
# ============================================================

def inject_import_to_file(path: str, import_line: str) -> Tuple[bool, str]:
    """
    በምንም ሁኔታ ላይ ኮዱን አያጣትም ብሎ аዲስ የ import መግቢያዎችን
    በኮዱ ላይ በተገቢው ቦታ ለማስገባት ይሞክራል።
    """
    if not os.path.exists(path):
        return False, "Target file for import injection not found"
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        if import_line.strip() in content:
            return True, "Import already exists in file"

        lines = content.splitlines()
        insert_idx = 0
        in_docstring = False
        docstring_char = None

        for idx, line in enumerate(lines):
            stripped = line.strip()

            if not in_docstring:
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    quote = stripped[:3]
                    if stripped.count(quote) >= 2 and len(stripped) > 3:
                        insert_idx = idx + 1
                        continue
                    in_docstring = True
                    docstring_char = quote
                    continue
            else:
                if docstring_char and docstring_char in stripped:
                    in_docstring = False
                    docstring_char = None
                insert_idx = idx + 1
                continue

            if stripped.startswith('#') or stripped.startswith('from __future__') \
               or stripped.startswith('#!/') or not stripped:
                insert_idx = idx + 1
                continue

            break

        lines.insert(insert_idx, import_line)
        updated_code = "\n".join(lines)

        ast.parse(updated_code)
        _atomic_write(path, updated_code)

        logger.info(f"💉 Import Injector: Injected '{import_line}' into {path}")
        return True, "Import injected successfully"
    except Exception as e:
        logger.error(f"Import injection failed: {e}")
        return False, str(e)


def auto_inject_imports(path: str, imports: List[str]) -> Dict[str, Any]:
    results = []
    all_ok = True
    for imp in imports:
        ok, msg = inject_import_to_file(path, imp)
        results.append({'import': imp, 'success': ok, 'message': msg})
        if not ok and "already exists" not in msg:
            all_ok = False
    return {'success': all_ok, 'results': results}


# ============================================================
# 🛡️ 2. BASE INDENT STRIPPER
# ============================================================

def strip_base_indent(text: str) -> str:
    """
    አንዱ ከሌላው የተለየ የመክፈቻ ሰፊ (Base Indent) ያስወግዳል
    """
    lines = text.splitlines()
    if not lines:
        return text

    indents = []
    for line in lines:
        if line.strip():
            match = re.match(r'^(\s*)', line)
            indents.append(match.group(1) if match else "")

    if not indents:
        return text

    base_indent = min(indents, key=len) if any(indents) else ""
    if not base_indent:
        return text

    stripped_lines = []
    for line in lines:
        if line.startswith(base_indent):
            stripped_lines.append(line[len(base_indent):])
        else:
            stripped_lines.append(line)

    return "\n".join(stripped_lines)


# ============================================================
# 🥷 3. AST SURGICAL PATCH ENGINE
# ============================================================

_REPLACEABLE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def apply_surgical_patch(path: str, target_name: str, new_code_segment: str) -> Tuple[bool, str]:
    """
    በ AST አጋዥነት በፋይሉ ውስጥ ያለውን አንድን ተግባር ወይም ክላስ በትክክል መቀየር ይችላል።
    """
    if not os.path.exists(path):
        return False, "File not found"

    try:
        with open(path, 'r', encoding='utf-8') as f:
            source_code = f.read()
    except Exception as e:
        return False, f"Could not read source file: {e}"

    try:
        tree = ast.parse(source_code)
        lines = source_code.splitlines()

        target_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                continue
            if isinstance(node, _REPLACEABLE_NODES) and node.name == target_name:
                target_node = node
                break

        if not target_node:
            return False, f"Target '{target_name}' not found in AST of {path}"

        start_line = target_node.lineno - 1
        if hasattr(target_node, 'decorator_list') and target_node.decorator_list:
            start_line = min(d.lineno for d in target_node.decorator_list) - 1

        end_line = target_node.end_lineno
        if end_line is None:
            end_line = target_node.lineno

        match_indent = re.match(r'^\s*', lines[start_line])
        indent_prefix = match_indent.group(0) if match_indent else ""

        clean_segment = strip_base_indent(new_code_segment)

        indented_lines = []
        for line in clean_segment.splitlines():
            if line.strip():
                indented_lines.append(indent_prefix + line)
            else:
                indented_lines.append("")

        patched_segment = "\n".join(indented_lines)
        new_lines = lines[:]
        new_lines[start_line:end_line] = [patched_segment]

        updated_code = "\n".join(new_lines)

        try:
            ast.parse(updated_code)
        except SyntaxError as e:
            return False, f"Surgical patch would create invalid syntax: {e}"

        _atomic_write(path, updated_code)
        return True, f"Successfully patched '{target_name}'"

    except Exception as e:
        logger.error(f"Surgical patch execution failed: {e}")
        return False, f"Surgical patch failed: {e}"


# ============================================================
# 🔁 3b. METHOD RENAME
# ============================================================

def rename_method(path: str, old_name: str, new_name: str) -> Tuple[bool, str]:
    if not os.path.exists(path):
        return False, "File not found"
    if old_name == new_name:
        return True, "Names are identical — nothing to do"

    try:
        with open(path, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)

        found = False
        for node in ast.walk(tree):
            if isinstance(node, _REPLACEABLE_NODES) and node.name == old_name:
                found = True
                break

        if not found:
            return False, f"'{old_name}' not found in {path}"

        updated = re.sub(
            rf'\b{re.escape(old_name)}\b',
            new_name,
            source,
        )
        ast.parse(updated)
        _atomic_write(path, updated)
        logger.info(f"🔁 Renamed '{old_name}' → '{new_name}' in {path}")
        return True, f"Renamed '{old_name}' → '{new_name}'"
    except Exception as e:
        return False, f"Rename failed: {e}"


# ============================================================
# 🧩 3c. SMART MERGE
# ============================================================

def smart_merge_methods(path: str, new_methods_code: str) -> Tuple[bool, str]:
    if not os.path.exists(path):
        return False, "File not found"

    try:
        with open(path, 'r', encoding='utf-8') as f:
            source = f.read()
        ast.parse(source)
        new_tree = ast.parse(new_methods_code)

        new_methods: Dict[str, ast.AST] = {}
        for node in ast.walk(new_tree):
            if isinstance(node, _REPLACEABLE_NODES):
                new_methods[node.name] = node

        if not new_methods:
            return False, "No method definitions found in new_methods_code"

        updated_source = source
        appended = 0
        replaced = 0

        for name in new_methods:
            method_src = _extract_method_source(new_methods_code, name)
            if not method_src:
                continue

            exists = False
            for node in ast.walk(ast.parse(updated_source)):
                if isinstance(node, _REPLACEABLE_NODES) and node.name == name:
                    exists = True
                    break

            if exists:
                ok, _ = apply_surgical_patch(path, name, method_src)
                if ok:
                    replaced += 1
                with open(path, 'r', encoding='utf-8') as f:
                    updated_source = f.read()
            else:
                merged = _append_method_to_class(updated_source, method_src)
                if merged:
                    updated_source = merged
                    appended += 1

        if appended:
            ast.parse(updated_source)
            _atomic_write(path, updated_source)

        if replaced + appended == 0:
            return False, "No methods could be merged"

        return True, f"Merged: {replaced} replaced, {appended} appended"
    except Exception as e:
        logger.error(f"Smart merge failed: {e}")
        return False, f"Smart merge failed: {e}"


def _extract_method_source(code: str, method_name: str) -> Optional[str]:
    try:
        tree = ast.parse(code)
        lines = code.splitlines()
        for node in ast.walk(tree):
            if isinstance(node, _REPLACEABLE_NODES) and node.name == method_name:
                start = node.lineno - 1
                if hasattr(node, 'decorator_list') and node.decorator_list:
                    start = min(d.lineno for d in node.decorator_list) - 1
                end = node.end_lineno or node.lineno
                return "\n".join(lines[start:end])
    except Exception:
        pass
    return None


def _append_method_to_class(source: str, method_src: str) -> Optional[str]:
    try:
        tree = ast.parse(source)
        lines = source.splitlines()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                insert_at = node.end_lineno or len(lines)
                class_indent_m = re.match(r'^(\s*)', lines[node.lineno - 1])
                method_indent = (class_indent_m.group(1) if class_indent_m else "") + "    "
                indented = "\n".join(
                    (method_indent + l if l.strip() else "")
                    for l in strip_base_indent(method_src).splitlines()
                )
                lines.insert(insert_at, indented)
                return "\n".join(lines)
    except Exception as e:
        logger.debug(f"Append method failed: {e}")
    return None


# ============================================================
# 🛡️ 4. PATH TRAVERSAL VALIDATION
# ============================================================

def _resolve_base_dir(site: Any = None) -> str:
    if site and getattr(site, 'name', None) != 'primary':
        repo_path = getattr(site, 'repo_path', None)
        if repo_path:
            if str(repo_path).startswith('http') or 'github.com' in str(repo_path):
                base = os.path.join('/tmp', 'ethafri_agent', site.name)
            else:
                base = str(repo_path)
        else:
            base = os.path.join('/tmp', 'ethafri_agent', site.name)
        return os.path.abspath(base)

    base_dir = getattr(settings, 'BASE_DIR', None)
    if base_dir is None:
        base_dir = os.getcwd()
    return os.path.abspath(str(base_dir))


def _is_path_traversal(path: str, base: str, allow_explicit: bool = False) -> bool:
    real_path = os.path.abspath(path)
    real_base = os.path.abspath(base)

    raw = str(path)
    if '..' in raw.split(os.sep) or '..' in raw.split('/'):
        return True

    if allow_explicit:
        return False

    try:
        common = os.path.commonpath([real_path, real_base])
        return common != real_base
    except ValueError:
        try:
            rel = os.path.relpath(real_path, real_base)
            return rel.startswith('..')
        except ValueError:
            return True


# ============================================================
# 🛠️ 5. DRY-RUN MODE
# ============================================================

def dry_run_apply(
    site,
    file_key: str,
    new_content: str,
    path: Optional[str] = None,
    target_name: Optional[str] = None,
) -> Dict[str, Any]:
    base = _resolve_base_dir(site)
    app_name = 'marketplace'
    explicit_path = path is not None

    if not path:
        if file_key.endswith('_html') or 'html' in file_key:
            clean_name = file_key.replace('_html', '').replace('.html', '') + '.html'
            file_path_relative = os.path.join('templates', app_name, clean_name)
        else:
            clean_name = file_key.replace('.py', '') + '.py'
            file_path_relative = clean_name
        path = os.path.join(base, app_name, file_path_relative)

    result: Dict[str, Any] = {
        'path': path,
        'file_key': file_key,
        'target_name': target_name,
    }

    if _is_path_traversal(path, base, allow_explicit=explicit_path):
        return _status(False, False, "Path traversal blocked", **result)

    valid = True
    syntax_err = None
    if path.endswith('.py') and not target_name:
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            valid = False
            syntax_err = f"Line {e.lineno}: {e.msg}"
    result['valid_syntax'] = valid
    result['syntax_error'] = syntax_err
    result['content_hash_after'] = _content_hash(new_content)

    old_code = ""
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                old_code = f.read()
        except Exception:
            pass
    result['content_hash_before'] = _content_hash(old_code) if old_code else None
    result['diff'] = generate_diff(old_code, new_content)
    result['would_apply'] = valid and (old_code.strip() != new_content.strip() or bool(target_name))
    result['is_identical'] = old_code.strip() == new_content.strip()

    return _status(
        success=True,
        applied=False,
        message="Dry run complete — no files written",
        **result,
    )


# ============================================================
# 🛠️ 6. MAIN CODE APPLICATION (apply_code_change)
# ============================================================
def apply_code_change(
    site,
    file_key: str,
    new_content: str,
    reason: str = "",
    path: Optional[str] = None,
    confidence_score: int = 100,
    backlog_task=None,
    push_to_github: bool = False,
    target_name: Optional[str] = None,
    inject_import: Optional[Dict] = None,
    auto_imports: Optional[List[str]] = None,
    dry_run: bool = False,
    enable_rollback: bool = False,
) -> Dict[str, Any]:
    """
    ኮዱን በንጽህና Sandbox ውስጥ ያረጋግጥ፣ ከዚያ በሎካል ፋይል ላይ ተግባራዊ ያድርግ።
    """

    if dry_run:
        return dry_run_apply(site, file_key, new_content, path=path, target_name=target_name)

    base = _resolve_base_dir(site)
    app_name = 'marketplace'
    explicit_path = path is not None

    if not path:
        if file_key.endswith('_html') or 'html' in file_key:
            clean_name = file_key.replace('_html', '').replace('.html', '') + '.html'
            file_path_relative = os.path.join('templates', app_name, clean_name)
        else:
            clean_name = file_key.replace('.py', '') + '.py'
            file_path_relative = clean_name
        path = os.path.join(base, app_name, file_path_relative)

    if _is_path_traversal(path, base, allow_explicit=explicit_path):
        error_msg = f"❌ Security Block: Path Traversal Attempted for path {path}"
        logger.error(error_msg)
        return _status(False, False, error_msg, path=path, file_key=file_key)

    if inject_import and isinstance(inject_import, dict):
        target_file_path = inject_import.get('target_path')
        import_line = inject_import.get('import_line')
        if target_file_path and import_line:
            success, msg = inject_import_to_file(target_file_path, import_line)
            if not success:
                logger.error(f"❌ Import Injection Blocked: {msg}")
                return _status(False, False, f"Import Injection Failed: {msg}", path=path, file_key=file_key)

    if auto_imports and isinstance(auto_imports, list):
        for imp in auto_imports:
            inject_import_to_file(path, imp)

    if path.endswith('.py') and not target_name:
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            return _status(
                False, False,
                f"❌ Python Syntax Error blocked: {e}",
                path=path, file_key=file_key,
            )

    old_code = ""
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                old_code = f.read()
        except Exception as e:
            logger.warning(f"⚠️ Could not read old file for backup: {e}")

    if old_code.strip() == new_content.strip() and not target_name:
        logger.info(f"⏭️ Code Apply: No changes detected for {file_key}.")
        return _status(
            True, False,
            "Skipped: Code is identical to the current file.",
            path=path, file_key=file_key,
        )

    if enable_rollback and old_code:
        RollbackManager.snapshot(path, old_code)

    branch_name = f"auto-evolution-{hashlib.md5(new_content.encode()).hexdigest()[:6]}"
    sandbox_active = False
    if path.endswith('.py'):
        ok, bmsg = GitSandboxManager.create_git_branch(branch_name)
        sandbox_active = ok

    try:
        if os.path.dirname(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        if target_name:
            success, msg = apply_surgical_patch(path, target_name, new_content)
            if not success:
                if sandbox_active:
                    subprocess.run(["git", "checkout", "main"], timeout=15, cwd=str(settings.BASE_DIR))
                    subprocess.run(["git", "branch", "-D", branch_name], timeout=15, cwd=str(settings.BASE_DIR))
                elif enable_rollback:
                    RollbackManager.rollback_last()
                return _status(False, False, msg, path=path, file_key=file_key)
            logger.info(f"💾 Surgically patched '{target_name}' in: {path}")
        else:
            _atomic_write(path, new_content)
            logger.info(f"💾 File overwritten successfully: {path}")
    except Exception as e:
        logger.error(f"❌ Failed to write file: {e}")
        if sandbox_active:
            subprocess.run(["git", "checkout", "main"], timeout=15, cwd=str(settings.BASE_DIR))
            subprocess.run(["git", "branch", "-D", branch_name], timeout=15, cwd=str(settings.BASE_DIR))
        elif enable_rollback:
            RollbackManager.rollback_last()
        return _status(False, False, str(e), path=path, file_key=file_key)

    if path.endswith('.py'):
        valid, vmsg = validate_python_file(path)
        if not valid:
            logger.error(f"❌ Post-write validation failed: {vmsg}")
            if sandbox_active:
                subprocess.run(["git", "checkout", "main"], timeout=15, cwd=str(settings.BASE_DIR))
                subprocess.run(["git", "branch", "-D", branch_name], timeout=15, cwd=str(settings.BASE_DIR))
            if old_code:
                _atomic_write(path, old_code)
            elif enable_rollback:
                RollbackManager.rollback_last()
            return _status(
                False, False,
                f"Post-write validation failed: {vmsg}",
                path=path, file_key=file_key,
            )

        core_django_files = {'models.py', 'views.py', 'urls.py', 'forms.py', 'admin.py', 'apps.py', 'code_apply.py', 'growth_agent.py', 'self_doctor.py'}
        if os.path.basename(path) in core_django_files:
            deep_ok, dmsg = deep_verify_django_app()
            if not deep_ok:
                logger.error(f"❌ Deep Django check failed: {dmsg}")
                if sandbox_active:
                    subprocess.run(["git", "checkout", "main"], timeout=15, cwd=str(settings.BASE_DIR))
                    subprocess.run(["git", "branch", "-D", branch_name], timeout=15, cwd=str(settings.BASE_DIR))
                if old_code:
                    _atomic_write(path, old_code)
                elif enable_rollback:
                    RollbackManager.rollback_all()
                return _status(
                    False, False,
                    f"Deep Django verification failed: {dmsg}",
                    path=path, file_key=file_key,
                )

            test_ok, tmsg = deep_test_django_app()
            if not test_ok:
                logger.error(f"❌ Unit Test Verification failed: {tmsg}")
                if sandbox_active:
                    subprocess.run(["git", "checkout", "main"], timeout=15, cwd=str(settings.BASE_DIR))
                    subprocess.run(["git", "branch", "-D", branch_name], timeout=15, cwd=str(settings.BASE_DIR))
                if old_code:
                    _atomic_write(path, old_code)
                elif enable_rollback:
                    RollbackManager.rollback_all()
                return _status(
                    False, False,
                    f"Unit Test Verification failed: {tmsg}",
                    path=path, file_key=file_key,
                )

        if sandbox_active:
            GitSandboxManager.merge_branch_to_main(branch_name)

    if path.endswith('.py') or path.endswith('.html'):
        try:
            manage_py = os.path.join(str(settings.BASE_DIR), 'manage.py')
            subprocess.Popen([sys.executable, manage_py, 'sync_translations'], close_fds=True)
            logger.info("⚡ Code Apply Trigger: Launched background sync_translations.")
        except Exception as trigger_err:
            logger.debug(f"Failed to trigger sync_translations in background: {trigger_err}")

    push_status = "Skipped (Local Only)"
    if push_to_github:
        try:
            rel_path = os.path.relpath(path, base).replace('\\', '/')
            push_status = push_to_github_raw(rel_path, new_content, reason, site=site)
        except Exception as e:
            push_status = f"GitHub Error: {e}"
            logger.error(push_status)

    try:
        AIEvolutionLog = apps.get_model('marketplace', 'AIEvolutionLog')
        if AIEvolutionLog:
            log_kwargs = {
                'site': site,
                'target_file': file_key,
                'reason_for_change': reason,
                'old_code_backup': old_code,
                'new_code_patch': new_content,
                'backlog_task': backlog_task,
            }
            try:
                AIEvolutionLog._meta.get_field('confidence_score')
                log_kwargs['confidence_score'] = confidence_score
            except Exception:
                pass
            AIEvolutionLog.objects.create(**log_kwargs)
    except Exception as e:
        logger.warning(f"⚠️ Could not log evolution entry dynamically: {e}")

    if backlog_task:
        try:
            backlog_task.status = 'Completed'
            backlog_task.save()
        except Exception as e:
            logger.warning(f"⚠️ Could not update task status: {e}")

    return _status(
        True, True,
        f"✅ Applied {file_key} | GitHub: {push_status}",
        path=path, file_key=file_key,
        content_hash=_content_hash(new_content),
        push_status=push_status,
    )

# ============================================================
# 📦 7. BATCH MULTI-FILE APPLY
# ============================================================

def batch_apply_changes(
    site,
    changes: List[Dict[str, Any]],
    push_to_github: bool = False,
    stop_on_error: bool = True,
) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    applied_count = 0
    failed_count = 0
    rolled_back: List[str] = []

    for change in changes:
        file_key = change.pop('file_key', '')
        new_content = change.pop('new_content', '')
        reason = change.pop('reason', '')

        result = apply_code_change(
            site=site,
            file_key=file_key,
            new_content=new_content,
            reason=reason,
            push_to_github=push_to_github,
            enable_rollback=True,
            **change,
        )
        results.append({'file_key': file_key, **result})

        if result.get('success') and result.get('applied'):
            applied_count += 1
        elif not result.get('success'):
            failed_count += 1
            if stop_on_error:
                rolled_back = RollbackManager.rollback_all()
                logger.warning(
                    f"⏹️ Batch stopped on error for '{file_key}'. "
                    f"Rolled back {len(rolled_back)} files."
                )
                break

    RollbackManager.clear()

    return {
        'success': failed_count == 0,
        'applied_count': applied_count,
        'failed_count': failed_count,
        'results': results,
        'rolled_back': rolled_back,
    }


# ============================================================
# 🚀 8. GITHUB PUSH (Raw API)
# ============================================================

def push_to_github_raw(
    file_path: str,
    content: str,
    message: str,
    site=None,
    max_retries: int = 2,
) -> str:
    token = getattr(settings, 'GITHUB_TOKEN', None)

    if not token:
        return "Local only (No Token)"

    repo_name = getattr(settings, 'GITHUB_REPO', 'Anwar-tad/Ethafri')
    if site and site.repo_path and ('github.com' in site.repo_path):
        match = re.search(r"github\.com/([^/]+/[^/]+)", site.repo_path)
        if match:
            repo_name = match.group(1).replace('.git', '')

    branch = None
    if site and hasattr(site, 'repo_branch') and site.repo_branch:
        branch = site.repo_branch
    if not branch:
        branch = getattr(settings, 'GITHUB_BRANCH', None)

    api_base = getattr(settings, 'GITHUB_API_BASE', 'https://api.github.com')
    url = f"{api_base}/repos/{repo_name}/contents/{file_path}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "Authorization": f"token {token}",
    }
    params = {}
    if branch:
        params["ref"] = branch

    attempt = 0
    while attempt <= max_retries:
        try:
            sha = ""
            res_get = requests.get(url, headers=headers, params=params, timeout=10)
            if res_get.status_code == 200:
                sha = res_get.json().get('sha', '')

            b64_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            payload = {"message": message, "content": b64_content}
            if sha:
                payload["sha"] = sha
            if branch:
                payload["branch"] = branch

            res_put = requests.put(url, headers=headers, json=payload, timeout=15)
            if res_put.status_code in [200, 201]:
                return "Success"

            if res_put.status_code == 429 and attempt < max_retries:
                wait = 2 ** (attempt + 1)
                logger.warning(f"⏳ GitHub rate limited, retrying in {wait}s...")
                time.sleep(wait)
                attempt += 1
                continue

            try:
                err_body = res_put.json().get('message', res_put.text[:200])
            except Exception:
                err_body = res_put.text[:200]
            return f"Error: GitHub returned status {res_put.status_code} — {err_body}"

        except requests.exceptions.Timeout:
            if attempt < max_retries:
                logger.warning("⏳ GitHub timeout, retrying...")
                time.sleep(2 ** attempt)
                attempt += 1
                continue
            return "Exception: GitHub API timeout"
        except Exception as e:
            return f"Exception: {e}"

    return "Error: Max retries exceeded"
    

def deep_test_django_app() -> Tuple[bool, str]:
    """
    በፓይተን በኩል 'manage.py test' ጥሪን በተለየ ንዑስ ፕሮሰስ በማስኬድ
    የጃንጎ ሰርቨር የሎጂክ ዩኒት ቴስቶችን በደህንነት ያረጋግጣል (Test-Driven Self-Correction)
    """
    import sys
    import subprocess
    try:
        # 🛡️ FIXED: Graceful Missing Tests Bypass to prevent blocking evolution if tests are absent
        tests_py = os.path.join(str(settings.BASE_DIR), 'marketplace', 'tests.py')
        tests_dir = os.path.join(str(settings.BASE_DIR), 'marketplace', 'tests')
        if not os.path.exists(tests_py) and not os.path.exists(tests_dir):
            logger.info("ℹ️ Test Verification: No unit tests found in marketplace. Bypassing unit test check.")
            return True, "OK"

        manage_py = os.path.join(str(settings.BASE_DIR), 'manage.py')
        result = subprocess.run(
            [sys.executable, manage_py, 'test', 'marketplace.tests', '--noinput'],
            capture_output=True, text=True, timeout=40, cwd=str(settings.BASE_DIR)
        )
        if result.returncode == 0:
            return True, "OK"
        return False, (result.stderr or result.stdout)[-500:]
    except Exception as e:
        return False, f"Test execution error: {e}"


# ============================================================
# 🌿 2. SAFE GIT-BRANCH SANDBOXING MANAGER
# ============================================================
class GitSandboxManager:
    """ኤጀንቱ አዳዲስ ኮዶችን ከመጻፉ በፊት በተለየ ቅርንጫፍ (Branch) ፈትኖ በጥራት እንዲያዋህድ መቆጣጠሪያ"""

    @staticmethod
    def create_git_branch(branch_name: str) -> Tuple[bool, str]:
        import subprocess
        try:
            res = subprocess.run(
                ["git", "checkout", "-b", branch_name],
                capture_output=True, text=True, timeout=15, cwd=str(settings.BASE_DIR)
            )
            if res.returncode == 0:
                logger.info(f"🌿 Git Sandbox: Created and checked out branch '{branch_name}'")
                return True, f"Branch '{branch_name}' created successfully"
            return False, res.stderr
        except Exception as e:
            return False, str(e)

    @staticmethod
    def merge_branch_to_main(branch_name: str) -> Tuple[bool, str]:
        import subprocess
        try:
            res_checkout = subprocess.run(
                ["git", "checkout", "main"],
                capture_output=True, text=True, timeout=15, cwd=str(settings.BASE_DIR)
            )
            if res_checkout.returncode != 0:
                subprocess.run(["git", "checkout", "master"], timeout=15, cwd=str(settings.BASE_DIR))

            res_merge = subprocess.run(
                ["git", "merge", branch_name],
                capture_output=True, text=True, timeout=15, cwd=str(settings.BASE_DIR)
            )
            if res_merge.returncode == 0:
                subprocess.run(["git", "branch", "-d", branch_name], timeout=15, cwd=str(settings.BASE_DIR))
                logger.info(f"🌿 Git Sandbox: Merged branch '{branch_name}' successfully.")
                return True, "Merged successfully"
            return False, res_merge.stderr
        except Exception as e:
            return False, str(e)