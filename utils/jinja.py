from __future__ import annotations

from jinja2 import Environment, FileSystemLoader

env = Environment(
    loader=FileSystemLoader('templates'), autoescape=True, enable_async=True
)


async def get_template_with_args(prompt, **kwargs):
    template = env.get_template(prompt)
    prompt_str = await template.render_async(**kwargs)
    return prompt_str
