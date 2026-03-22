"""Shared Resend path-builder helpers."""

from __future__ import annotations

from typing import Mapping
from urllib.parse import quote

from harnessiq.shared.resend_models import PathBuilder


def static_path_builder(path_hint: str) -> PathBuilder:
    parameter_names = tuple(extract_path_parameters(path_hint))

    def build(path_params: Mapping[str, str]) -> str:
        rendered = path_hint
        for parameter_name in parameter_names:
            value = path_params[parameter_name]
            rendered = rendered.replace(f"{{{parameter_name}}}", quote(value, safe=""))
        return rendered

    return build


def extract_path_parameters(path_hint: str) -> list[str]:
    parameters: list[str] = []
    current: list[str] = []
    inside = False
    for character in path_hint:
        if character == "{":
            inside = True
            current = []
            continue
        if character == "}":
            inside = False
            parameters.append("".join(current))
            current = []
            continue
        if inside:
            current.append(character)
    return parameters


def build_contact_collection_path(path_params: Mapping[str, str]) -> str:
    audience_id = path_params.get("audience_id")
    if audience_id:
        return f"/audiences/{quote(audience_id, safe='')}/contacts"
    return "/contacts"


def build_contact_item_path(path_params: Mapping[str, str]) -> str:
    contact_identifier = path_params["contact_identifier"]
    audience_id = path_params.get("audience_id")
    contact = quote(contact_identifier, safe="")
    if audience_id:
        return f"/audiences/{quote(audience_id, safe='')}/contacts/{contact}"
    return f"/contacts/{contact}"


__all__ = [
    "build_contact_collection_path",
    "build_contact_item_path",
    "extract_path_parameters",
    "static_path_builder",
]
