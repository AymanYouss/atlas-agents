from __future__ import annotations

from atlas.config import Settings


def test_cors_origins_parsed_and_stripped() -> None:
    s = Settings(ATLAS_CORS_ORIGINS=" http://a.com , http://b.com ,")
    assert s.cors_origin_list == ["http://a.com", "http://b.com"]


def test_sync_database_url_drops_async_driver() -> None:
    s = Settings(ATLAS_DATABASE_URL="postgresql+asyncpg://u:p@h:5432/db")
    assert s.sync_database_url == "postgresql://u:p@h:5432/db"


def test_production_flag() -> None:
    assert Settings(ATLAS_ENV="production").is_production is True
    assert Settings(ATLAS_ENV="development").is_production is False
