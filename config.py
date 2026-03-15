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
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://mwnvyfncdugaprergebm.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im13bnZ5Zm5jZHVnYXByZXJnZWJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM1MjU3MTEsImV4cCI6MjA4OTEwMTcxMX0.doyBxAamz7eV4JFwHTvxXmF1vvL1B9Qv3trFb9cXcPU")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-in-production")
FREE_ANON_LIMIT = int(os.environ.get("FREE_ANON_LIMIT", "50"))
APP_URL = os.environ.get("APP_URL", "https://aca.negociosglobales.digital")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "noreply@negociosglobales.digital")
ADMIN_EMAILS = {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}
