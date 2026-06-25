from shared.db import configure, migrate
from .download import run as dl
from .parse_clean import run as parse
from .chunk import run as chunk
from .embed_index import run as build


def refresh_pipeline():
    configure()
    migrate()
    a = dl()
    b = parse()
    c = chunk()
    d = build()
    return {"download": a, "parse": b, "chunk": c, "index": d}
