import os
import glob
from bs4 import BeautifulSoup
from shared.text_norm import normalize_text
from shared.config import DATA_DIR, SOURCE_NAME
from shared.db import upsert_document
from shared.logging import get_logger

log = get_logger("parse_clean")


def _get_text(el):
    return el.get_text(" ", strip=True) if el else ""


def run():
    raw = os.path.join(DATA_DIR, "raw")
    cnt = 0
    for fp in glob.glob(os.path.join(raw, "**", "*.htm*"), recursive=True):
        try:
            html = open(fp, "r", encoding="utf-8", errors="ignore").read()
            soup = BeautifulSoup(html, "lxml")
            chu_de = normalize_text(_get_text(soup.select_one("h1, .chu-de, .chude")))
            de_muc = normalize_text(_get_text(soup.select_one("h2, .de-muc, .demuc")))

            for di in soup.select(".dieu, .dieu-item, .article, h3"):
                so_dieu = normalize_text(
                    _get_text(di.select_one(".so-dieu, .title, h3")) or di.text
                )
                tieu_de = normalize_text(_get_text(di.select_one(".ten-dieu, .subtitle, h4")))
                body = []
                for p in di.find_all_next(["p", "li"], limit=40):
                    if p.find("h3"):
                        break
                    body.append(_get_text(p))
                body = normalize_text("\n".join(body))
                if len(body) < 5:
                    continue
                doc_id = f"chu_de={chu_de}|de_muc={de_muc}|dieu={so_dieu}"
                doc = {
                    "id": doc_id,
                    "chu_de": chu_de,
                    "de_muc": de_muc,
                    "so_dieu": so_dieu,
                    "tieu_de_dieu": tieu_de,
                    "noi_dung": body,
                    "nguon": SOURCE_NAME,
                    "path_goc": fp,
                }
                upsert_document(doc)
                cnt += 1
        except Exception as e:
            log.error("parse_error", file=fp, error=str(e))
    log.info("parse_clean_done", docs=cnt)
    return {"docs": cnt}
