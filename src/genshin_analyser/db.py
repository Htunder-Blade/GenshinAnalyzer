from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from genshin_analyser.config import DEFAULT_ACCOUNT_DB_PATH, DEFAULT_DB_PATH, ensure_data_dirs


class Base(DeclarativeBase):
    pass


class AccountBase(DeclarativeBase):
    pass


def make_engine(db_path: Path = DEFAULT_DB_PATH):
    ensure_data_dirs(db_path=db_path)
    return create_engine(f"sqlite:///{db_path}", future=True)


def make_session_factory(db_path: Path = DEFAULT_DB_PATH):
    return sessionmaker(bind=make_engine(db_path), autoflush=False, expire_on_commit=False)


def make_account_engine(db_path: Path = DEFAULT_ACCOUNT_DB_PATH):
    ensure_data_dirs(db_path=db_path)
    return create_engine(f"sqlite:///{db_path}", future=True)


def make_account_session_factory(db_path: Path = DEFAULT_ACCOUNT_DB_PATH):
    return sessionmaker(bind=make_account_engine(db_path), autoflush=False, expire_on_commit=False)


def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    from genshin_analyser import models as _models  # noqa: F401

    engine = make_engine(db_path)
    Base.metadata.create_all(engine)
    _migrate_characters_to_slim_schema(engine)
    _migrate_weapons_to_slim_schema(engine)
    _migrate_artifact_sets_to_slim_schema(engine)


def init_account_db(db_path: Path = DEFAULT_ACCOUNT_DB_PATH) -> None:
    from genshin_analyser import models as _models  # noqa: F401

    engine = make_account_engine(db_path)
    AccountBase.metadata.create_all(engine)


SLIM_CHARACTER_COLUMNS = (
    "name",
    "rarity",
    "element",
    "weapon_type",
    "character_data",
    "talent_data",
    "constellation_data",
    "stats_data",
)

SLIM_WEAPON_COLUMNS = (
    "name",
    "rarity",
    "weapon_type",
    "weapon_data",
    "stats_data",
)

SLIM_ARTIFACT_SET_COLUMNS = (
    "name",
    "flower_name",
    "plume_name",
    "sands_name",
    "goblet_name",
    "circlet_name",
    "effect_1pc",
    "effect_2pc",
    "effect_4pc",
)


def _migrate_characters_to_slim_schema(engine) -> None:
    with engine.begin() as connection:
        rows = connection.exec_driver_sql("PRAGMA table_info(characters)").fetchall()
        existing_columns = [row[1] for row in rows]
        if existing_columns == list(SLIM_CHARACTER_COLUMNS):
            return
        if not existing_columns:
            return

        missing = [column for column in SLIM_CHARACTER_COLUMNS if column not in existing_columns]
        if missing:
            missing_text = ", ".join(missing)
            raise RuntimeError(f"characters 表缺少迁移所需字段：{missing_text}")

        connection.exec_driver_sql("DROP TABLE IF EXISTS characters_slim_migration")
        connection.exec_driver_sql(
            """
            CREATE TABLE characters_slim_migration (
                name VARCHAR NOT NULL PRIMARY KEY,
                rarity VARCHAR,
                element VARCHAR,
                weapon_type VARCHAR,
                character_data JSON NOT NULL,
                talent_data JSON NOT NULL,
                constellation_data JSON NOT NULL,
                stats_data JSON NOT NULL
            )
            """
        )
        columns = ", ".join(SLIM_CHARACTER_COLUMNS)
        connection.exec_driver_sql(
            f"""
            INSERT INTO characters_slim_migration ({columns})
            SELECT {columns}
            FROM characters
            """
        )
        connection.exec_driver_sql("DROP TABLE characters")
        connection.exec_driver_sql("ALTER TABLE characters_slim_migration RENAME TO characters")
        connection.exec_driver_sql("CREATE INDEX ix_characters_rarity ON characters (rarity)")
        connection.exec_driver_sql("CREATE INDEX ix_characters_element ON characters (element)")
        connection.exec_driver_sql("CREATE INDEX ix_characters_weapon_type ON characters (weapon_type)")


def _migrate_weapons_to_slim_schema(engine) -> None:
    with engine.begin() as connection:
        rows = connection.exec_driver_sql("PRAGMA table_info(weapons)").fetchall()
        existing_columns = [row[1] for row in rows]
        if existing_columns == list(SLIM_WEAPON_COLUMNS):
            return
        if not existing_columns:
            return

        missing = [column for column in SLIM_WEAPON_COLUMNS if column not in existing_columns]
        if missing:
            missing_text = ", ".join(missing)
            raise RuntimeError(f"weapons 表缺少迁移所需字段：{missing_text}")

        connection.exec_driver_sql("DROP TABLE IF EXISTS weapons_slim_migration")
        connection.exec_driver_sql(
            """
            CREATE TABLE weapons_slim_migration (
                name VARCHAR NOT NULL PRIMARY KEY,
                rarity VARCHAR,
                weapon_type VARCHAR,
                weapon_data JSON NOT NULL,
                stats_data JSON NOT NULL
            )
            """
        )
        columns = ", ".join(SLIM_WEAPON_COLUMNS)
        connection.exec_driver_sql(
            f"""
            INSERT INTO weapons_slim_migration ({columns})
            SELECT {columns}
            FROM weapons
            WHERE name != '「一心传」名刀'
            """
        )
        connection.exec_driver_sql("DROP TABLE weapons")
        connection.exec_driver_sql("ALTER TABLE weapons_slim_migration RENAME TO weapons")
        connection.exec_driver_sql("CREATE INDEX ix_weapons_rarity ON weapons (rarity)")
        connection.exec_driver_sql("CREATE INDEX ix_weapons_weapon_type ON weapons (weapon_type)")


def _migrate_artifact_sets_to_slim_schema(engine) -> None:
    with engine.begin() as connection:
        rows = connection.exec_driver_sql("PRAGMA table_info(artifact_sets)").fetchall()
        existing_columns = [row[1] for row in rows]
        if existing_columns == list(SLIM_ARTIFACT_SET_COLUMNS):
            return
        if not existing_columns:
            return

        missing = [column for column in SLIM_ARTIFACT_SET_COLUMNS if column not in existing_columns]
        if missing:
            missing_text = ", ".join(missing)
            raise RuntimeError(f"artifact_sets 表缺少迁移所需字段：{missing_text}")

        connection.exec_driver_sql("DROP TABLE IF EXISTS artifact_sets_slim_migration")
        connection.exec_driver_sql(
            """
            CREATE TABLE artifact_sets_slim_migration (
                name VARCHAR NOT NULL PRIMARY KEY,
                flower_name VARCHAR,
                plume_name VARCHAR,
                sands_name VARCHAR,
                goblet_name VARCHAR,
                circlet_name VARCHAR,
                effect_1pc VARCHAR,
                effect_2pc VARCHAR,
                effect_4pc VARCHAR
            )
            """
        )
        columns = ", ".join(SLIM_ARTIFACT_SET_COLUMNS)
        connection.exec_driver_sql(
            f"""
            INSERT INTO artifact_sets_slim_migration ({columns})
            SELECT {columns}
            FROM artifact_sets
            """
        )
        connection.exec_driver_sql("DROP TABLE artifact_sets")
        connection.exec_driver_sql("ALTER TABLE artifact_sets_slim_migration RENAME TO artifact_sets")
