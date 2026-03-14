"""Configuración del sistema ACA."""
import os

from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "anthropic/claude-sonnet-4"
DECRETO_PDF_PATH = os.environ.get(
    "DECRETO_PDF_PATH",
    os.path.expanduser("~/Downloads/decreto_1881_2021.pdf"),
)
MAX_PDF_PAGES_PER_CHUNK = 18
VISION_MODEL = "google/gemini-2.0-flash-001"
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "bmp"}
ALLOWED_FILE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "bmp", "pdf"}
PERPLEXITY_MODEL = "perplexity/sonar-pro"
DIAN_RESOLUCIONES_URL = "https://www.dian.gov.co/normatividad/Paginas/ResoClasifiAracelaria.aspx"
