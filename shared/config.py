"""Legacy re-exports — new code should import from shared.settings directly."""
from shared.settings import settings

DATA_DIR = settings.data_dir
INDEX_DIR = settings.index_dir
ZIP_URL = settings.bopd_zip_url
EMBEDDER_BACKEND = settings.embedder_backend
EMBEDDER_MODEL = settings.embedder_model
DEFAULT_ALPHA = settings.default_alpha
DEFAULT_BETA = settings.default_beta
SOURCE_NAME = settings.source_name
