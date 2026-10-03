from pathlib import Path

from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

jinja_environment = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(
        enabled_extensions=("html", "xml"),
        default_for_string=True,
        default=True,
    ),
    undefined=StrictUndefined,
)

templates = Jinja2Templates(env=jinja_environment)

