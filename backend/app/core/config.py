from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load root .env if present (works both locally and inside containers)
ROOT_DIR = Path(__file__).resolve().parents[3]
ROOT_ENV = ROOT_DIR / ".env"
if ROOT_ENV.exists():
    load_dotenv(ROOT_ENV, override=False)
else:
    load_dotenv(override=False)


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://challenge_user:challenge_pass@localhost:5434/challenge_db"
    JWT_SECRET: str = "changeme_secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 4320  # 3 kun

    # Security & Network
    ALLOWED_ORIGINS: str = ""
    TRUSTED_PROXY_CIDRS: str = "172.28.1.10/32,127.0.0.1/32"
    DEV_MODE: bool = False

    # Runner (Sandbox)
    RUNNER_URL: str = "http://runner:8080"
    RUNNER_TIMEOUT_SECS: float = 5.0
    RUNNER_SHARED_SECRET: str = ""

    # Legacy SMTP (kept optional for backward compatibility)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "noreply@challenge.uz"
    FRONTEND_URL: str = "http://localhost:5173"

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_BOT_USERNAME: str = ""
    ADMIN_TELEGRAM_IDS: str = ""

    # Challenge & Registration
    MAX_PARTICIPANTS: int = 30
    CHALLENGE_START_DATE: str = "2027-02-01"
    REGISTRATION_CLOSE_DATE: str = "2027-01-25"
    CONFIRM_WINDOW_START: str = "2027-01-28"
    CONFIRM_WINDOW_END: str = "2027-01-31"
    FINAL_DATE: str = "2027-03-05"
    RULES_VERSION: int = 1
    SITE_URL: str = "http://localhost"

    # OTP
    OTP_TTL_MINUTES: int = 15
    OTP_MAX_PER_HOUR: int = 3

    # Timezone
    TIMEZONE: str = "Asia/Tashkent"

    model_config = SettingsConfigDict(
        env_file=str(ROOT_ENV) if ROOT_ENV.exists() else ".env",
        env_file_encoding="utf-8",
        extra="allow",
    )

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.TIMEZONE)

    def now_local(self) -> datetime:
        return datetime.now(self.tz)

    def today_local(self) -> date:
        return self.now_local().date()

    @property
    def admin_telegram_id_set(self) -> set[int]:
        ids: set[int] = set()
        for part in self.ADMIN_TELEGRAM_IDS.split(","):
            part = part.strip()
            if part and part.lstrip("-").isdigit():
                ids.add(int(part))
        return ids

    @property
    def challenge_start(self) -> date:
        return date.fromisoformat(self.CHALLENGE_START_DATE)

    @property
    def registration_close(self) -> date:
        return date.fromisoformat(self.REGISTRATION_CLOSE_DATE)

    @property
    def confirm_window_start_date(self) -> date:
        return date.fromisoformat(self.CONFIRM_WINDOW_START)

    @property
    def confirm_window_end_date(self) -> date:
        return date.fromisoformat(self.CONFIRM_WINDOW_END)

    @property
    def final_date_val(self) -> date:
        return date.fromisoformat(self.FINAL_DATE)

    @property
    def allowed_origins_list(self) -> list[str]:
        origins = [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]
        if not origins:
            origins = [self.SITE_URL.rstrip("/")]
        if self.DEV_MODE:
            for dev_origin in ("http://localhost:5173", "http://localhost:3000"):
                if dev_origin not in origins:
                    origins.append(dev_origin)
        return origins

    @property
    def trusted_proxy_cidrs_list(self) -> list[str]:
        return [c.strip() for c in self.TRUSTED_PROXY_CIDRS.split(",") if c.strip()]


settings = Settings()
