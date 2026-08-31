import logging
import os
from dataclasses import dataclass

from environs import Env


logger = logging.getLogger(__name__)


@dataclass
class BotSettings:
    token: str
    admin_ids: list[int]
    master_user_id: int


@dataclass
class DatabaseSettings:
    name: str
    host: str
    port: int
    user: str
    password: str


@dataclass
class RedisSettings:
    host: str
    port: int
    db: int
    username: str
    password: str


@dataclass
class ProxySettings:
    type: str
    login: str
    password: str
    ip: str
    port: str

    @property
    def url(self) -> str:
        auth = f"{self.login}:{self.password}@" if self.login and self.password else ""
        return f"{self.type}://{auth}{self.ip}:{self.port}"


@dataclass
class LogSettings:
    level: str
    format: str


@dataclass
class Config:
    bot: BotSettings
    db: DatabaseSettings
    redis: RedisSettings
    log: LogSettings
    proxy: ProxySettings | None


def load_config(path: str | None = None) -> Config:
    env = Env()

    if path:
        if not os.path.exists(path):
            logger.warning(".env file not found at '%s', skipping...", path)
        else:
            logger.info("Loading .env from '%s'", path)

    env.read_env(path)

    token = env("BOT_TOKEN")

    if not token:
        raise ValueError("BOT_TOKEN must not be empty")

    raw_ids = env.list("ADMIN_IDS", default=[])

    try:
        admin_ids = [int(x) for x in raw_ids]
    except ValueError as e:
        raise ValueError(f"ADMIN_IDS must be integers, got: {raw_ids}") from e

    try:
        master_user_id = env.int("MASTER_USER_ID")
    except Exception as e:
        raise ValueError("MASTER_USER_ID must be an integer Telegram user id") from e

    proxy_ip = env.str("PROXY_IP", default='').strip()

    proxy = None
    if proxy_ip:
        proxy = ProxySettings(
            type=env.str("PROXY_TYPE", default='http'),
            ip=proxy_ip,
            port=env.str("PROXY_PORT"),
            login=env.str("PROXY_LOGIN", default=''),
            password=env.str("PROXY_PASSWORD", default=''),
        )

    db = DatabaseSettings(
        name=env("POSTGRES_DB"),
        host=env("POSTGRES_HOST"),
        port=env.int("POSTGRES_PORT"),
        user=env("POSTGRES_USER"),
        password=env("POSTGRES_PASSWORD"),
    )

    redis = RedisSettings(
        host=env("REDIS_HOST"),
        port=env.int("REDIS_PORT"),
        db=env.int("REDIS_DATABASE"),
        password=env("REDIS_PASSWORD", default=""),
        username=env("REDIS_USERNAME", default=""),
    )

    logg_settings = LogSettings(
        level=env("LOG_LEVEL"),
        format=env("LOG_FORMAT"),
    )

    logger.info("Configuration loaded successfully")

    return Config(
        bot=BotSettings(
            token=token,
            admin_ids=admin_ids,
            master_user_id=master_user_id
        ),
        db=db,
        redis=redis,
        log=logg_settings,
        proxy=proxy,
    )
