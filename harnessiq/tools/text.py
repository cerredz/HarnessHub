"""
===============================================================================
File: harnessiq/tools/text.py

What this file does:
- Defines the `_LinkParser` type and the supporting logic it needs in the
  `harnessiq/tools` module.
- Deterministic text tools.

Use cases:
- Import `_LinkParser` when composing higher-level HarnessIQ runtime behavior
  from this package.

How to use it:
- Use the public class and any exported helpers here as the supported entry
  points for this module.

Intent:
- Keep this package responsibility encapsulated behind one focused module
  instead of duplicating the same logic elsewhere.
===============================================================================
"""

from __future__ import annotations

import html
import math
import re
import unicodedata
from collections.abc import Mapping, Sequence
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

from harnessiq.shared.tools import (
    RegisteredTool,
    TEXT_CHUNK,
    TEXT_ESTIMATE_TOKENS,
    TEXT_EXTRACT_CODE_BLOCKS,
    TEXT_EXTRACT_EMAILS,
    TEXT_EXTRACT_LINKS,
    TEXT_NORMALIZE,
    TEXT_REGEX_EXTRACT,
    TEXT_STRIP_MARKDOWN,
    TEXT_TEMPLATE_FILL,
    TEXT_TRUNCATE,
    ToolArguments,
    ToolDefinition,
)

_FLAGS = {"IGNORECASE": re.IGNORECASE, "MULTILINE": re.MULTILINE, "DOTALL": re.DOTALL}
_SMART_QUOTES = str.maketrans(
    {
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
    }
)
_URL_RE = re.compile(r"(?P<url>(?:https?|ftp)://[^\s<>()]+)", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b(?P<local>[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+)@(?P<domain>[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
_STRICT_EMAIL_RE = re.compile(r"^(?=.{1,254}$)(?P<local>[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64})@(?P<domain>(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,63})$")
_MD_LINK_RE = re.compile(r"!\[(?P<img_text>[^\]]*)\]\((?P<img_url>[^)]+)\)|\[(?P<text>[^\]]+)\]\((?P<url>[^)]+)\)")
_MD_AUTOLINK_RE = re.compile(r"<(?P<url>(?:https?|ftp)://[^>]+)>", re.IGNORECASE)
_FENCE_RE = re.compile(r"^(?P<fence>`{3,}|~{3,})(?P<lang>[^\n`]*)$")


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str | None]] = []
        self._href: str | None = None
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            href = dict(attrs).get("href")
            if href:
                self._href = href
                self._chunks = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.links.append({"url": self._href, "anchor_text": "".join(self._chunks).strip() or None})
            self._href = None
            self._chunks = []


def normalize_text(
    text: str,
    *,
    unicode_normalize: bool = True,
    collapse_whitespace: bool = True,
    strip_control_chars: bool = True,
    lowercase: bool = False,
    normalize_quotes: bool = False,
    strip_per_line: bool = False,
) -> str:
    result = unicodedata.normalize("NFKC", text) if unicode_normalize else text
    if strip_control_chars:
        result = "".join(ch for ch in result if ord(ch) >= 0x20 or ch in {"\n", "\t"})
    if normalize_quotes:
        result = result.translate(_SMART_QUOTES)
    if strip_per_line:
        result = "\n".join(line.strip() for line in result.splitlines())
    if collapse_whitespace:
        result = "\n".join(re.sub(r"[^\S\n]+", " ", line).strip() for line in result.splitlines()).strip()
    return result.lower() if lowercase else result


def estimate_tokens(text: str, *, model_family: str = "claude") -> int:
    words = max(1, len(re.findall(r"\S+", text)) or math.ceil(len(text.strip()) / 4))
    multiplier = {"claude": 1.28, "gpt": 1.33, "generic": 1.3}.get(model_family, 1.3)
    return 0 if not text.strip() else max(1, math.ceil(words * multiplier))


def truncate_text(
    text: str,
    max_length: int,
    *,
    unit: str = "chars",
    ellipsis: str = "...",
    boundary: str = "word",
    position: str = "end",
) -> str:
    if max_length < 0:
        raise ValueError("max_length must be greater than or equal to zero.")
    if unit == "tokens":
        if estimate_tokens(text) <= max_length:
            return text
        words = re.findall(r"\S+", text)
        keep = max(1, math.floor(max_length / 1.3))
        if len(words) <= keep:
            return text
        if position == "middle":
            head = (keep + 1) // 2
            tail = keep // 2
            return f"{' '.join(words[:head])}{ellipsis}{' ' + ' '.join(words[-tail:]) if tail else ''}"
        return f"{' '.join(words[:keep])}{ellipsis}"
    if len(text) <= max_length:
        return text
    if max_length <= len(ellipsis):
        return ellipsis[:max_length]
    available = max_length - len(ellipsis)
    if position == "middle":
        left = text[: (available + 1) // 2]
        right = text[-(available // 2) :] if available // 2 else ""
        if boundary == "word":
            left = re.sub(r"\s+\S*$", "", left) or left
            right = re.sub(r"^\S+\s+", "", right) or right
        return f"{left}{ellipsis}{right}"
    visible = text[:available]
    if boundary == "word":
        visible = re.sub(r"\s+\S*$", "", visible) or visible
    return f"{visible}{ellipsis}"


def regex_extract(text: str, pattern: str, *, mode: str = "all", flags: Sequence[str] = (), group: int | None = None) -> dict[str, Any]:
    try:
        compiled = re.compile(pattern, _compile_flags(flags))
    except re.error as exc:
        return {"matched": False, "matches": [], "error": f"Invalid regex pattern: {exc}"}
    matches = list(compiled.finditer(text))
    if not matches:
        return {"matched": False, "matches": []}
    if mode == "named":
        rendered: Any = [match.groupdict() for match in matches]
    elif mode == "first":
        rendered = _render_match(matches[0], group)
    else:
        rendered = [_render_match(match, group) for match in matches]
    return {"matched": True, "matches": rendered, "count": len(matches)}


def chunk_text(text: str, size: int, *, unit: str = "chars", overlap: int = 0, boundary: str = "word", sentence_lookahead: int = 200) -> list[dict[str, Any]]:
    if size <= 0:
        raise ValueError("size must be greater than zero.")
    max_chars = size if unit == "chars" else max(1, size * 4)
    overlap_chars = overlap if unit == "chars" else max(0, overlap * 4)
    items: list[dict[str, Any]] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        if boundary == "word" and end < len(text):
            match = re.search(r"\s", text[end:])
            if match:
                end += match.start()
        if boundary == "sentence" and end < len(text):
            match = re.search(r"[.!?](?=\s)", text[end : min(len(text), end + sentence_lookahead)])
            if match:
                end += match.end()
        items.append({"index": len(items), "text": text[start:end], "start_offset": start, "end_offset": end})
        if end >= len(text):
            break
        start = max(0, end - overlap_chars)
    return items


def extract_links(
    text: str,
    *,
    format: str = "auto",
    schemes: Sequence[str] = ("http", "https"),
    domain_allowlist: Sequence[str] = (),
    domain_denylist: Sequence[str] = (),
    deduplicate: bool = True,
) -> list[dict[str, Any]]:
    detected = _detect_format(text) if format == "auto" else format
    if detected == "html":
        parser = _LinkParser()
        parser.feed(text)
        raw = parser.links
    elif detected == "markdown":
        raw = []
        raw.extend({"url": m.group("url") or m.group("img_url"), "anchor_text": m.group("text") or m.group("img_text") or None} for m in _MD_LINK_RE.finditer(text))
        raw.extend({"url": m.group("url"), "anchor_text": None} for m in _MD_AUTOLINK_RE.finditer(text))
    else:
        raw = [{"url": m.group("url"), "anchor_text": None} for m in _URL_RE.finditer(text)]
    schemes_set = {value.lower() for value in schemes}
    allow = {value.lower() for value in domain_allowlist}
    deny = {value.lower() for value in domain_denylist}
    seen: set[str] = set()
    links: list[dict[str, Any]] = []
    for item in raw:
        parsed = urlparse(str(item["url"]))
        scheme = parsed.scheme.lower()
        host = parsed.hostname.lower() if parsed.hostname else ""
        if schemes_set and scheme not in schemes_set:
            continue
        if allow and not any(host == domain or host.endswith(f".{domain}") for domain in allow):
            continue
        if deny and any(host == domain or host.endswith(f".{domain}") for domain in deny):
            continue
        if deduplicate and str(item["url"]) in seen:
            continue
        seen.add(str(item["url"]))
        links.append({"url": str(item["url"]), "anchor_text": item.get("anchor_text"), "scheme": scheme})
    return links


def extract_emails(text: str, *, strict_validation: bool = False, deobfuscate: bool = False, domain_filter: Sequence[str] = (), deduplicate: bool = True) -> list[dict[str, str]]:
    source = re.sub(r"\s*(?:\[|\()?\s*at\s*(?:\]|\))?\s*", "@", text, flags=re.IGNORECASE) if deobfuscate else text
    source = re.sub(r"\s*(?:\[|\()?\s*dot\s*(?:\]|\))?\s*", ".", source, flags=re.IGNORECASE) if deobfuscate else source
    allowed = {value.lower() for value in domain_filter}
    seen: set[str] = set()
    emails: list[dict[str, str]] = []
    for match in _EMAIL_RE.finditer(source):
        email = match.group(0)
        strict = _STRICT_EMAIL_RE.match(email) if strict_validation else None
        if strict_validation and strict is None:
            continue
        local = (strict or match).group("local")
        domain = (strict or match).group("domain").lower()
        normalized = f"{local}@{domain}"
        if allowed and domain not in allowed:
            continue
        if deduplicate and normalized in seen:
            continue
        seen.add(normalized)
        emails.append({"email": normalized, "local_part": local, "domain": domain})
    return emails


def strip_markdown(text: str, *, preserve_links: bool = False, preserve_code_language: bool = False, collapse_blank_lines: bool = True, table_separator: str = "\t") -> str:
    def replace_fence(match: re.Match[str]) -> str:
        lang = (match.group("lang") or "").strip()
        code = (match.group("code") or "").rstrip("\n")
        return f"{lang}\n{code}".strip() if preserve_code_language and lang else code

    result = re.sub(r"```(?P<lang>[^\n`]*)\n(?P<code>.*?)```|~~~(?P<lang>[^\n~]*)\n(?P<code>.*?)~~~", replace_fence, text, flags=re.DOTALL)
    result = re.sub(r"!\[(?P<alt>[^\]]*)\]\((?P<url>[^)]+)\)", lambda m: m.group("alt"), result)
    result = re.sub(r"\[(?P<text>[^\]]+)\]\((?P<url>[^)]+)\)", lambda m: f"{m.group('text')} ({m.group('url')})" if preserve_links else m.group("text"), result)
    result = re.sub(r"<((?:https?|ftp)://[^>]+)>", r"\1", result)
    result = re.sub(r"^\s{0,3}#{1,6}\s*", "", result, flags=re.MULTILINE)
    lines: list[str] = []
    for line in result.splitlines():
        if "|" in line:
            parts = [part.strip() for part in line.strip().strip("|").split("|")]
            if parts and not all(re.fullmatch(r":?-{3,}:?", part) for part in parts):
                lines.append(table_separator.join(parts))
        else:
            lines.append(line)
    result = "\n".join(lines)
    result = re.sub(r"^\s*[-*+]\s+", "", result, flags=re.MULTILINE)
    result = re.sub(r"^\s*\d+\.\s+", "", result, flags=re.MULTILINE)
    result = re.sub(r"[*_~`]+", "", result)
    if collapse_blank_lines:
        result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def estimate_tokens_payload(text: str, *, model_family: str = "claude", context_limit: int | None = None) -> dict[str, Any]:
    estimated = estimate_tokens(text, model_family=model_family)
    fraction = None if context_limit in {None, 0} else estimated / context_limit
    return {"estimated_tokens": estimated, "budget_fraction": fraction, "warning": bool(fraction is not None and fraction >= 0.8)}


def extract_code_blocks(text: str, *, language_filter: Sequence[str] = (), include_offsets: bool = False, strip_trailing_newline: bool = True) -> list[dict[str, Any]]:
    allowed = {item.lower() for item in language_filter}
    lines = text.splitlines(keepends=True)
    blocks: list[dict[str, Any]] = []
    line_index = 0
    offset = 0
    while line_index < len(lines):
        current = lines[line_index].rstrip("\r\n")
        match = _FENCE_RE.match(current)
        if match is None:
            offset += len(lines[line_index])
            line_index += 1
            continue
        start_offset = offset
        fence = match.group("fence")
        language = match.group("lang").strip().lower()
        line_index += 1
        offset += len(lines[line_index - 1])
        content: list[str] = []
        while line_index < len(lines) and not lines[line_index].rstrip("\r\n").startswith(fence):
            content.append(lines[line_index])
            offset += len(lines[line_index])
            line_index += 1
        if line_index < len(lines):
            offset += len(lines[line_index])
            line_index += 1
        code = "".join(content)
        if strip_trailing_newline:
            code = code.rstrip("\n")
        if allowed and language not in allowed:
            continue
        item: dict[str, Any] = {"language": language or None, "code": code}
        if include_offsets:
            item["start_offset"] = start_offset
            item["end_offset"] = offset
        blocks.append(item)
    return blocks


def template_fill(template: str, values: Mapping[str, Any], *, delimiter: str = "double_brace", strict: bool = False, escape_missing: bool = False) -> dict[str, Any]:
    if delimiter == "brace":
        pattern = re.compile(r"\{(?P<name>[A-Za-z_][A-Za-z0-9_]*)\}")
    elif delimiter == "double_brace":
        pattern = re.compile(r"\{\{(?P<name>[A-Za-z_][A-Za-z0-9_]*)\}\}")
    elif delimiter == "dollar":
        pattern = re.compile(r"\$(?:\{(?P<name1>[A-Za-z_][A-Za-z0-9_]*)\}|(?P<name2>[A-Za-z_][A-Za-z0-9_]*))")
    else:
        raise ValueError("Unsupported delimiter.")

    found = []
    missing = set()

    def replace(match: re.Match[str]) -> str:
        name = match.groupdict().get("name") or match.groupdict().get("name1") or match.groupdict().get("name2") or ""
        found.append(name)
        if name in values:
            return str(values[name])
        missing.add(name)
        token = match.group(0)
        return html.escape(token) if escape_missing else token

    rendered = pattern.sub(replace, template)
    if strict and missing:
        raise ValueError(f"Missing template values for: {', '.join(sorted(missing))}")
    return {"text": rendered, "filled_placeholders": [name for name in found if name in values], "missing_placeholders": sorted(missing)}


def create_text_tools() -> tuple[RegisteredTool, ...]:
    return (
        RegisteredTool(_tool("text.normalize", "normalize", {"text": {"type": "string"}, "unicode_normalize": {"type": "boolean"}, "collapse_whitespace": {"type": "boolean"}, "strip_control_chars": {"type": "boolean"}, "lowercase": {"type": "boolean"}, "normalize_quotes": {"type": "boolean"}, "strip_per_line": {"type": "boolean"}}, "Normalize raw text.", ("text",)), _normalize_tool),
        RegisteredTool(_tool("text.truncate", "truncate", {"text": {"type": "string"}, "max_length": {"type": "integer"}, "unit": {"type": "string", "enum": ["chars", "tokens"]}, "ellipsis": {"type": "string"}, "boundary": {"type": "string", "enum": ["exact", "word"]}, "position": {"type": "string", "enum": ["end", "middle"]}}, "Truncate text.", ("text", "max_length")), _truncate_tool),
        RegisteredTool(_tool(TEXT_REGEX_EXTRACT, "regex_extract", {"text": {"type": "string"}, "pattern": {"type": "string"}, "mode": {"type": "string", "enum": ["first", "all", "named"]}, "flags": {"type": "array", "items": {"type": "string"}}, "group": {"type": ["integer", "null"]}}, "Extract regex matches.", ("text", "pattern")), _regex_tool),
        RegisteredTool(_tool(TEXT_CHUNK, "chunk", {"text": {"type": "string"}, "size": {"type": "integer"}, "unit": {"type": "string", "enum": ["chars", "tokens"]}, "overlap": {"type": "integer"}, "boundary": {"type": "string", "enum": ["exact", "word", "sentence"]}, "sentence_lookahead": {"type": "integer"}}, "Chunk long text.", ("text", "size")), _chunk_tool),
        RegisteredTool(_tool(TEXT_EXTRACT_LINKS, "extract_links", {"text": {"type": "string"}, "format": {"type": "string", "enum": ["auto", "plaintext", "markdown", "html"]}, "schemes": {"type": "array", "items": {"type": "string"}}, "domain_allowlist": {"type": "array", "items": {"type": "string"}}, "domain_denylist": {"type": "array", "items": {"type": "string"}}, "deduplicate": {"type": "boolean"}}, "Extract links.", ("text",)), _extract_links_tool),
        RegisteredTool(_tool(TEXT_EXTRACT_EMAILS, "extract_emails", {"text": {"type": "string"}, "strict_validation": {"type": "boolean"}, "deobfuscate": {"type": "boolean"}, "domain_filter": {"type": "array", "items": {"type": "string"}}, "deduplicate": {"type": "boolean"}}, "Extract email addresses.", ("text",)), _extract_emails_tool),
        RegisteredTool(_tool(TEXT_STRIP_MARKDOWN, "strip_markdown", {"text": {"type": "string"}, "preserve_links": {"type": "boolean"}, "preserve_code_language": {"type": "boolean"}, "collapse_blank_lines": {"type": "boolean"}, "table_separator": {"type": "string"}}, "Strip Markdown syntax.", ("text",)), _strip_markdown_tool),
        RegisteredTool(_tool(TEXT_ESTIMATE_TOKENS, "estimate_tokens", {"text": {"type": "string"}, "model_family": {"type": "string", "enum": ["claude", "gpt", "generic"]}, "context_limit": {"type": ["integer", "null"]}}, "Estimate token usage.", ("text",)), _estimate_tool),
        RegisteredTool(_tool(TEXT_EXTRACT_CODE_BLOCKS, "extract_code_blocks", {"text": {"type": "string"}, "language_filter": {"type": "array", "items": {"type": "string"}}, "include_offsets": {"type": "boolean"}, "strip_trailing_newline": {"type": "boolean"}}, "Extract fenced code blocks.", ("text",)), _code_blocks_tool),
        RegisteredTool(_tool(TEXT_TEMPLATE_FILL, "template_fill", {"template": {"type": "string"}, "values": {"type": "object"}, "delimiter": {"type": "string", "enum": ["brace", "double_brace", "dollar"]}, "strict": {"type": "boolean"}, "escape_missing": {"type": "boolean"}}, "Fill a placeholder template.", ("template", "values")), _template_tool),
    )


def _normalize_tool(arguments: ToolArguments) -> dict[str, Any]:
    text = _require_str(arguments, "text")
    value = normalize_text(text, unicode_normalize=_require_bool(arguments, "unicode_normalize", True), collapse_whitespace=_require_bool(arguments, "collapse_whitespace", True), strip_control_chars=_require_bool(arguments, "strip_control_chars", True), lowercase=_require_bool(arguments, "lowercase", False), normalize_quotes=_require_bool(arguments, "normalize_quotes", False), strip_per_line=_require_bool(arguments, "strip_per_line", False))
    return {"text": value, "changed": value != text}


def _truncate_tool(arguments: ToolArguments) -> dict[str, Any]:
    text = _require_str(arguments, "text")
    value = truncate_text(text, _require_int(arguments, "max_length"), unit=_require_str(arguments, "unit", "chars"), ellipsis=_require_str(arguments, "ellipsis", "..."), boundary=_require_str(arguments, "boundary", "word"), position=_require_str(arguments, "position", "end"))
    return {"text": value, "original_length": len(text), "output_length": len(value), "was_truncated": value != text}


def _regex_tool(arguments: ToolArguments) -> dict[str, Any]:
    return regex_extract(_require_str(arguments, "text"), _require_str(arguments, "pattern"), mode=_require_str(arguments, "mode", "all"), flags=_require_str_list(arguments, "flags"), group=_require_opt_int(arguments, "group"))


def _chunk_tool(arguments: ToolArguments) -> dict[str, Any]:
    chunks = chunk_text(_require_str(arguments, "text"), _require_int(arguments, "size"), unit=_require_str(arguments, "unit", "chars"), overlap=_require_int(arguments, "overlap", 0), boundary=_require_str(arguments, "boundary", "word"), sentence_lookahead=_require_int(arguments, "sentence_lookahead", 200))
    return {"chunks": chunks, "count": len(chunks)}


def _extract_links_tool(arguments: ToolArguments) -> dict[str, Any]:
    links = extract_links(_require_str(arguments, "text"), format=_require_str(arguments, "format", "auto"), schemes=_require_str_list(arguments, "schemes", ("http", "https")), domain_allowlist=_require_str_list(arguments, "domain_allowlist"), domain_denylist=_require_str_list(arguments, "domain_denylist"), deduplicate=_require_bool(arguments, "deduplicate", True))
    return {"links": links, "count": len(links)}


def _extract_emails_tool(arguments: ToolArguments) -> dict[str, Any]:
    emails = extract_emails(_require_str(arguments, "text"), strict_validation=_require_bool(arguments, "strict_validation", False), deobfuscate=_require_bool(arguments, "deobfuscate", False), domain_filter=_require_str_list(arguments, "domain_filter"), deduplicate=_require_bool(arguments, "deduplicate", True))
    return {"emails": emails, "count": len(emails)}


def _strip_markdown_tool(arguments: ToolArguments) -> dict[str, Any]:
    return {"text": strip_markdown(_require_str(arguments, "text"), preserve_links=_require_bool(arguments, "preserve_links", False), preserve_code_language=_require_bool(arguments, "preserve_code_language", False), collapse_blank_lines=_require_bool(arguments, "collapse_blank_lines", True), table_separator=_require_str(arguments, "table_separator", "\t"))}


def _estimate_tool(arguments: ToolArguments) -> dict[str, Any]:
    return estimate_tokens_payload(_require_str(arguments, "text"), model_family=_require_str(arguments, "model_family", "claude"), context_limit=_require_opt_int(arguments, "context_limit"))


def _code_blocks_tool(arguments: ToolArguments) -> dict[str, Any]:
    blocks = extract_code_blocks(_require_str(arguments, "text"), language_filter=_require_str_list(arguments, "language_filter"), include_offsets=_require_bool(arguments, "include_offsets", False), strip_trailing_newline=_require_bool(arguments, "strip_trailing_newline", True))
    return {"blocks": blocks, "count": len(blocks)}


def _template_tool(arguments: ToolArguments) -> dict[str, Any]:
    values = arguments.get("values")
    if not isinstance(values, Mapping):
        raise ValueError("The 'values' argument must be an object.")
    return template_fill(_require_str(arguments, "template"), values, delimiter=_require_str(arguments, "delimiter", "double_brace"), strict=_require_bool(arguments, "strict", False), escape_missing=_require_bool(arguments, "escape_missing", False))


def _tool(key: str, name: str, properties: dict[str, object], description: str, required: Sequence[str]) -> ToolDefinition:
    return ToolDefinition(key=key, name=name, description=description, input_schema={"type": "object", "properties": properties, "required": list(required), "additionalProperties": False})


def _render_match(match: re.Match[str], group: int | None) -> Any:
    if group is not None:
        return match.group(group)
    return list(match.groups()) if match.groups() else match.group(0)


def _compile_flags(flags: Sequence[str]) -> re.RegexFlag:
    compiled = re.RegexFlag(0)
    for flag in flags:
        if flag.upper() not in _FLAGS:
            raise ValueError(f"Unsupported regex flag '{flag}'.")
        compiled |= _FLAGS[flag.upper()]
    return compiled


def _detect_format(text: str) -> str:
    if "<a " in text.lower():
        return "html"
    return "markdown" if "](" in text or "<http" in text.lower() else "plaintext"


def _require_str(arguments: ToolArguments, key: str, default: str | None = None) -> str:
    if key not in arguments:
        if default is None:
            raise ValueError(f"The '{key}' argument is required.")
        return default
    value = arguments[key]
    if not isinstance(value, str):
        raise ValueError(f"The '{key}' argument must be a string.")
    return value


def _require_int(arguments: ToolArguments, key: str, default: int | None = None) -> int:
    if key not in arguments:
        if default is None:
            raise ValueError(f"The '{key}' argument is required.")
        return default
    value = arguments[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"The '{key}' argument must be an integer.")
    return value


def _require_opt_int(arguments: ToolArguments, key: str) -> int | None:
    if key not in arguments or arguments[key] is None:
        return None
    return _require_int(arguments, key)


def _require_bool(arguments: ToolArguments, key: str, default: bool) -> bool:
    value = arguments.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"The '{key}' argument must be a boolean.")
    return value


def _require_str_list(arguments: ToolArguments, key: str, default: Sequence[str] = ()) -> list[str]:
    if key not in arguments:
        return list(default)
    value = arguments[key]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"The '{key}' argument must be an array of strings.")
    return list(value)


__all__ = ["chunk_text", "create_text_tools", "estimate_tokens", "estimate_tokens_payload", "extract_code_blocks", "extract_emails", "extract_links", "normalize_text", "regex_extract", "strip_markdown", "template_fill", "truncate_text"]
