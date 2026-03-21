from __future__ import annotations

"""模板与脚手架文本辅助能力。"""

import re
from collections.abc import Mapping


def slugify(value: str) -> str:
    """把任意文本归一化为短横线命名。"""

    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "item"


def render_template(template: str, context: Mapping[str, object]) -> str:
    """按 Python `str.format` 规则渲染模板。"""

    return template.format(**context)


__all__ = ["render_template", "slugify"]
