from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from genshin_analyzer.db import AccountBase, Base


class Character(Base):
    __tablename__ = "characters"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    rarity: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    element: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    weapon_type: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    character_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    talent_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    constellation_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    stats_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Weapon(Base):
    __tablename__ = "weapons"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    rarity: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    weapon_type: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    weapon_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    stats_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ArtifactSet(Base):
    __tablename__ = "artifact_sets"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    flower_name: Mapped[str | None] = mapped_column(String, nullable=True)
    plume_name: Mapped[str | None] = mapped_column(String, nullable=True)
    sands_name: Mapped[str | None] = mapped_column(String, nullable=True)
    goblet_name: Mapped[str | None] = mapped_column(String, nullable=True)
    circlet_name: Mapped[str | None] = mapped_column(String, nullable=True)
    effect_1pc: Mapped[str | None] = mapped_column(String, nullable=True)
    effect_2pc: Mapped[str | None] = mapped_column(String, nullable=True)
    effect_4pc: Mapped[str | None] = mapped_column(String, nullable=True)


class Account(AccountBase):
    __tablename__ = "accounts"

    uid: Mapped[str] = mapped_column(String, primary_key=True)


class AccountCharacter(AccountBase):
    __tablename__ = "account_characters"
    __table_args__ = (
        UniqueConstraint("uid", "character_name", name="uq_account_characters_uid_character_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(ForeignKey("accounts.uid"), index=True)
    character_name: Mapped[str] = mapped_column(String, index=True)
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ascension: Mapped[int | None] = mapped_column(Integer, nullable=True)
    constellation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    normal_attack_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elemental_skill_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elemental_burst_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    equipped_weapon_id: Mapped[int | None] = mapped_column(
        ForeignKey("account_weapons.id"),
        nullable=True,
    )
    equipped_flower_id: Mapped[int | None] = mapped_column(
        ForeignKey("account_artifacts.id"),
        nullable=True,
    )
    equipped_plume_id: Mapped[int | None] = mapped_column(
        ForeignKey("account_artifacts.id"),
        nullable=True,
    )
    equipped_sands_id: Mapped[int | None] = mapped_column(
        ForeignKey("account_artifacts.id"),
        nullable=True,
    )
    equipped_goblet_id: Mapped[int | None] = mapped_column(
        ForeignKey("account_artifacts.id"),
        nullable=True,
    )
    equipped_circlet_id: Mapped[int | None] = mapped_column(
        ForeignKey("account_artifacts.id"),
        nullable=True,
    )


class AccountWeapon(AccountBase):
    __tablename__ = "account_weapons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(ForeignKey("accounts.uid"), index=True)
    weapon_name: Mapped[str] = mapped_column(String, index=True)
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    refinement_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AccountArtifact(AccountBase):
    __tablename__ = "account_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(ForeignKey("accounts.uid"), index=True)
    set_name: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    piece_name: Mapped[str | None] = mapped_column(String, nullable=True)
    slot: Mapped[str] = mapped_column(String, index=True)
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rarity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    main_stat: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    substats: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String, default="genshin-db-api")
    language: Mapped[str] = mapped_column(String, default="chinese")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    character_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped: Mapped[list[str]] = mapped_column(JSON, default=list)
