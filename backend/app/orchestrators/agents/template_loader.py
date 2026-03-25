from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class AgentTemplateFile:
    agent_code: str
    display_name: str
    description: str
    source_file: str
    metadata: Dict[str, str]
    body: str


def _slugify(filename: str) -> str:
    return (
        filename.replace(".md", "")
        .replace("engineering-", "")
        .replace("testing-", "")
        .replace("product-", "product_")
        .replace("-", "_")
    )


def parse_front_matter(text: str) -> tuple[Dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text

    _, rest = text.split("---\n", 1)
    front_matter, body = rest.split("\n---\n", 1)
    metadata: Dict[str, str] = {}
    for raw_line in front_matter.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata, body.strip()


def load_agent_templates(agents_dir: Path) -> List[AgentTemplateFile]:
    templates: List[AgentTemplateFile] = []
    for path in sorted(agents_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        metadata, body = parse_front_matter(text)
        templates.append(
            AgentTemplateFile(
                agent_code=_slugify(path.name),
                display_name=metadata.get("name", path.stem),
                description=metadata.get("description", ""),
                source_file=str(path.relative_to(agents_dir.parent)),
                metadata=metadata,
                body=body,
            )
        )
    return templates
