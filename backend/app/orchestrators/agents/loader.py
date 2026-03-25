from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class AgentMarkdownTemplate:
    agent_code: str
    display_name: str
    description: str
    vibe: str
    tools: list[str]
    source_file: str
    body: str


def slugify_agent_code(path: Path) -> str:
    raw = path.stem.lower()
    return raw.replace(" ", "-").replace("_", "-")


def parse_front_matter(content: str) -> tuple[dict[str, str], str]:
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    raw_meta = parts[1].strip().splitlines()
    body = parts[2].strip()
    meta: dict[str, str] = {}
    for line in raw_meta:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, body


def load_agent_templates(agents_dir: str) -> list[AgentMarkdownTemplate]:
    templates: list[AgentMarkdownTemplate] = []
    for path in sorted(Path(agents_dir).glob("*.md")):
        content = path.read_text(encoding="utf-8")
        meta, body = parse_front_matter(content)
        tools = [
            item.strip()
            for item in meta.get("tools", "").split(",")
            if item.strip()
        ]
        templates.append(
            AgentMarkdownTemplate(
                agent_code=slugify_agent_code(path),
                display_name=meta.get("name", path.stem),
                description=meta.get("description", ""),
                vibe=meta.get("vibe", ""),
                tools=tools,
                source_file=str(path),
                body=body,
            )
        )
    return templates

