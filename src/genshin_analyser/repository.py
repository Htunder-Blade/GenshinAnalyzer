from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from genshin_analyser.models import (
    Account,
    AccountArtifact,
    AccountCharacter,
    AccountWeapon,
    ArtifactSet,
    Character,
    SyncRun,
    Weapon,
)
from genshin_analyser.time import utc_now


CHARACTER_INTRO_KEYS = {
    "affiliation",
    "associationType",
    "birthday",
    "birthdaymmdd",
    "bodyType",
    "cv",
    "description",
    "gender",
    "region",
    "title",
    "url",
    "version",
}
DROP_ANYWHERE_KEYS = {
    "images",
}
WEAPON_INTRO_KEYS = {
    "description",
    "descriptionRaw",
    "story",
    "version",
}


def upsert_character(
    session: Session,
    *,
    character_payload: dict[str, Any],
    talent_payload: dict[str, Any],
    constellation_payload: dict[str, Any],
    stats_payload: dict[str, Any],
) -> Character:
    data = character_payload["result"]
    name = str(data.get("name") or character_payload.get("match") or character_payload.get("query"))
    character = session.scalar(select(Character).where(Character.name == name))
    if character is None:
        character = Character(name=name)
        session.add(character)

    character.rarity = _optional_str(data.get("rarity"))
    character.element = _optional_str(data.get("elementText") or data.get("element"))
    character.weapon_type = _optional_str(data.get("weaponText") or data.get("weapontype"))
    character.character_data = _slim_payload(character_payload, drop_result_keys=CHARACTER_INTRO_KEYS)
    character.talent_data = _slim_payload(talent_payload)
    character.constellation_data = _slim_payload(constellation_payload)
    character.stats_data = stats_payload
    session.flush()
    return character


def upsert_weapon(
    session: Session,
    *,
    weapon_payload: dict[str, Any],
    stats_payload: dict[str, Any],
) -> Weapon:
    data = weapon_payload["result"]
    name = str(data.get("name") or weapon_payload.get("match") or weapon_payload.get("query"))
    weapon = session.scalar(select(Weapon).where(Weapon.name == name))
    if weapon is None:
        weapon = Weapon(name=name)
        session.add(weapon)

    weapon.name = name
    weapon.rarity = _optional_str(data.get("rarity"))
    weapon.weapon_type = _optional_str(data.get("weaponText") or data.get("weaponType"))
    weapon.weapon_data = _slim_payload(weapon_payload, drop_result_keys=WEAPON_INTRO_KEYS)
    weapon.stats_data = stats_payload
    session.flush()
    return weapon


def upsert_artifact_set(
    session: Session,
    *,
    artifact_payload: dict[str, Any],
) -> ArtifactSet:
    name = str(artifact_payload["name"])
    artifact_set = session.scalar(select(ArtifactSet).where(ArtifactSet.name == name))
    if artifact_set is None:
        artifact_set = ArtifactSet(name=name)
        session.add(artifact_set)

    artifact_set.flower_name = _piece_name(artifact_payload, "flower")
    artifact_set.plume_name = _piece_name(artifact_payload, "plume")
    artifact_set.sands_name = _piece_name(artifact_payload, "sands")
    artifact_set.goblet_name = _piece_name(artifact_payload, "goblet")
    artifact_set.circlet_name = _piece_name(artifact_payload, "circlet")
    artifact_set.effect_1pc = _optional_str(artifact_payload.get("effect1Pc"))
    artifact_set.effect_2pc = _optional_str(artifact_payload.get("effect2Pc"))
    artifact_set.effect_4pc = _optional_str(artifact_payload.get("effect4Pc"))
    session.flush()
    return artifact_set


def create_sync_run(session: Session, language: str) -> SyncRun:
    sync_run = SyncRun(
        source="genshin-db-api",
        language=language,
        started_at=utc_now(),
        character_count=0,
        skipped=[],
    )
    session.add(sync_run)
    session.flush()
    return sync_run


def finish_sync_run(sync_run: SyncRun, count: int, skipped: list[str]) -> None:
    sync_run.finished_at = utc_now()
    sync_run.character_count = count
    sync_run.skipped = skipped


def count_characters(session: Session) -> int:
    return int(session.scalar(select(func.count(Character.name))) or 0)


def count_weapons(session: Session) -> int:
    return int(session.scalar(select(func.count(Weapon.name))) or 0)


def count_artifact_sets(session: Session) -> int:
    return int(session.scalar(select(func.count(ArtifactSet.name))) or 0)


def count_accounts(session: Session) -> int:
    return int(session.scalar(select(func.count(Account.uid))) or 0)


def count_account_characters(session: Session, uid: str | None = None) -> int:
    statement = select(func.count(AccountCharacter.id))
    if uid is not None:
        statement = statement.where(AccountCharacter.uid == uid)
    return int(session.scalar(statement) or 0)


def count_account_weapons(session: Session, uid: str | None = None) -> int:
    statement = select(func.count(AccountWeapon.id))
    if uid is not None:
        statement = statement.where(AccountWeapon.uid == uid)
    return int(session.scalar(statement) or 0)


def count_account_artifacts(session: Session, uid: str | None = None) -> int:
    statement = select(func.count(AccountArtifact.id))
    if uid is not None:
        statement = statement.where(AccountArtifact.uid == uid)
    return int(session.scalar(statement) or 0)


def list_characters(session: Session, limit: int | None = None) -> list[Character]:
    statement = select(Character).order_by(Character.element, Character.name)
    if limit is not None:
        statement = statement.limit(limit)
    return list(session.scalars(statement))


def list_weapons(session: Session, limit: int | None = None) -> list[Weapon]:
    statement = select(Weapon).order_by(Weapon.weapon_type, Weapon.rarity.desc(), Weapon.name)
    if limit is not None:
        statement = statement.limit(limit)
    return list(session.scalars(statement))


def list_artifact_sets(session: Session, limit: int | None = None) -> list[ArtifactSet]:
    statement = select(ArtifactSet).order_by(ArtifactSet.name)
    if limit is not None:
        statement = statement.limit(limit)
    return list(session.scalars(statement))


def find_character(session: Session, keyword: str) -> list[Character]:
    return list(
        session.scalars(
            select(Character)
            .where(Character.name.contains(keyword))
            .order_by(Character.name)
        )
    )


def find_weapon(session: Session, keyword: str) -> list[Weapon]:
    return list(
        session.scalars(
            select(Weapon)
            .where(Weapon.name.contains(keyword))
            .order_by(Weapon.name)
        )
    )


def find_artifact_set(session: Session, keyword: str) -> list[ArtifactSet]:
    return list(
        session.scalars(
            select(ArtifactSet)
            .where(ArtifactSet.name.contains(keyword))
            .order_by(ArtifactSet.name)
        )
    )


def get_character(session: Session, name: str) -> Character | None:
    return session.scalar(select(Character).where(Character.name == name))


def get_weapon(session: Session, name: str) -> Weapon | None:
    return session.scalar(select(Weapon).where(Weapon.name == name))


def get_artifact_set(session: Session, name: str) -> ArtifactSet | None:
    return session.scalar(select(ArtifactSet).where(ArtifactSet.name == name))


def _optional_str(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _piece_name(payload: dict[str, Any], key: str) -> str | None:
    piece = payload.get(key)
    if not isinstance(piece, dict):
        return None
    return _optional_str(piece.get("name"))


def _slim_payload(
    payload: dict[str, Any],
    *,
    drop_result_keys: set[str] | None = None,
) -> dict[str, Any]:
    slimmed: dict[str, Any] = {"result": _drop_unneeded_data(payload.get("result", {}))}
    if drop_result_keys and isinstance(slimmed["result"], dict):
        for key in drop_result_keys:
            slimmed["result"].pop(key, None)
    if "error" in payload:
        slimmed["error"] = payload["error"]
    return slimmed


def _drop_unneeded_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _drop_unneeded_data(item)
            for key, item in value.items()
            if key not in DROP_ANYWHERE_KEYS
        }
    if isinstance(value, list):
        return [_drop_unneeded_data(item) for item in value]
    return value
