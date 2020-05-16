"""
Tools for manipulating YAML files.

I want to preserve formatting and comments, therefore I cannot use a standard
YAML parser and serializer.
"""

from typing import Callable, Collection, Dict, List, Optional, Tuple, Union

from ..utils import FileLines, warn


def update_yaml_list(
    orig_lines: FileLines,
    key: Union[str, Tuple[str, ...]],
    new_value: List[str],
    *,
    filename: str,
    keep: Optional[Callable[[str], bool]] = None,
    replacements: Optional[Dict[str, str]] = None,
) -> FileLines:
    """Update a list of values in a YAML document.

    The document is represented as a list of lines (``orig_lines``), because
    we want to preserve the exact formatting including comments.

    ``key`` is a tuple that represents the traversal path from the root of
    the document.  As a special case it can be a string instead of a 1-tuple
    for top-level keys.

    The new value of the list will consist of ``new_value``, plus whatever
    old values need to be kept according to the ``keep`` callback.  Any of the
    kept old values will also be optionally replaced with a replacement
    from the ``replacements`` dict.

    No YAML decoding is done for old values passed to ``keep()`` or
    ``replacements.get()``.

    No YAML escaping or formatting is done for new values or replacements.

    ``filename`` is used for error reporting.

    Returns an updated list of lines.
    """
    if not isinstance(key, tuple):
        key = (key,)

    lines = iter(enumerate(orig_lines))
    current = 0
    indents = [0]
    for n, line in lines:
        stripped = line.lstrip()
        if not stripped or stripped.startswith('#'):
            continue
        indent = len(line) - len(stripped)
        if current >= len(indents):
            indents.append(indent)
        elif indent > indents[current]:
            continue
        else:
            while current > 0 and indent < indents[current]:
                del indents[current]
                current -= 1
        if stripped.startswith(f'{key[current]}:'):
            current += 1
            if current == len(key):
                break
    else:
        warn(f'Did not find {".".join(key)}: setting in {filename}')
        return orig_lines

    start = n
    end = n + 1
    indent = 2
    list_indent = None
    keep_before: List[str] = []
    keep_after: List[str] = []
    lines_to_keep = keep_before
    kept_last: Optional[bool] = False
    for n, line in lines:
        stripped = line.lstrip()
        line_indent = len(line) - len(stripped)
        if list_indent is None and stripped.startswith('- '):
            list_indent = line_indent
        if stripped.startswith('- ') and line_indent == list_indent:
            lines_to_keep = keep_after
            indent = line_indent
            end = n + 1
            value = stripped[2:].strip()
            kept_last = keep and keep(value)
            if kept_last:
                if replacements and value in replacements:
                    lines_to_keep.append(
                        f"{' '* indent}- {replacements[value]}\n"
                    )
                else:
                    lines_to_keep.append(line)
        elif stripped.startswith('#'):
            lines_to_keep.append(line)
            end = n + 1
        elif line_indent > indent:
            if kept_last:
                lines_to_keep.append(line)
            end = n + 1
        elif line == '\n':
            continue
        elif line[0] != ' ':
            break
        elif list_indent is not None and line_indent < list_indent:
            break

    new_lines = orig_lines[:start] + [
        f"{' ' * indents[-1]}{key[-1]}:\n"
    ] + keep_before + [
        f"{' ' * indent}- {value}\n"
        for value in new_value
    ] + keep_after + orig_lines[end:]
    return new_lines


def drop_yaml_node(
    orig_lines: FileLines,
    key: str,
    *,
    filename: str,
) -> FileLines:
    """Drop a value from a YAML document.

    The document is represented as a list of lines (``orig_lines``), because
    we want to preserve the exact formatting including comments.

    ``key`` is a string.  Currently only top-level nodes can be dropped.

    ``filename`` is used for error reporting.

    It is not an error if ``key`` is not present in the document.  In this
    case ``orig_lines`` is returned unmodified.

    Returns an updated list of lines.
    """
    lines = iter(enumerate(orig_lines))
    where = None
    for n, line in lines:
        if line.startswith(f'{key}:'):
            if where is not None:
                warn(
                    f"Duplicate {key}: setting in {filename}"
                    f" (lines {where + 1} and {n + 1})"
                )
            where = n
    if where is None:
        return orig_lines

    lines = iter(enumerate(orig_lines[where + 1:], where + 1))

    start = where
    end = start + 1
    for n, line in lines:
        if line and line[0] != ' ':
            break
        else:
            end = n + 1
    new_lines = orig_lines[:start] + orig_lines[end:]

    return new_lines


def add_yaml_node(
    orig_lines: FileLines,
    key: str,
    value: str,
    *,
    before: Optional[Union[str, Collection[str]]] = None,
) -> FileLines:
    """Add a value to a YAML document.

    The document is represented as a list of lines (``orig_lines``), because
    we want to preserve the exact formatting including comments.

    ``key`` is a string.  Currently only top-level nodes can be added.

    ``value`` is the new value, as a string.  No YAML escaping or formatting
    is done.

    ``before`` can specify a key or a set of keys.  If specified, the new
    key will be added before the first of existing keys from this set.

    Returns an updated list of lines.
    """
    lines = iter(enumerate(orig_lines))
    where = len(orig_lines)
    if before:
        if isinstance(before, str):
            before = (before, )
        lines = iter(enumerate(orig_lines))
        for n, line in lines:
            if any(line == f'{key}:\n' for key in before):
                where = n
                break

    new_lines = orig_lines[:where] + [
        f'{key}: {value}\n'
    ] + orig_lines[where:]
    return new_lines