from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from genshin_analyser.character_source import GenshinDbCharacterClient, write_character_cache
from genshin_analyser.config import (
    DEFAULT_ACCOUNT_DB_PATH,
    DEFAULT_ARTIFACT_CACHE_DIR,
    DEFAULT_CACHE_DIR,
    DEFAULT_DB_PATH,
    DEFAULT_WEAPON_CACHE_DIR,
    ensure_data_dirs,
)
from genshin_analyser.db import init_account_db, init_db, make_account_session_factory, make_session_factory
from genshin_analyser.exceptions import CharacterDataError
from genshin_analyser.repository import (
    count_artifact_sets,
    count_account_artifacts,
    count_account_characters,
    count_account_weapons,
    count_accounts,
    count_characters,
    count_weapons,
    create_sync_run,
    find_artifact_set,
    find_character,
    find_weapon,
    finish_sync_run,
    get_artifact_set,
    get_character,
    get_weapon,
    list_artifact_sets,
    list_characters,
    list_weapons,
    upsert_artifact_set,
    upsert_weapon,
    upsert_character,
)


app = typer.Typer(help="本地原神角色和武器资料数据库。")

EXCLUDED_WEAPON_NAMES = {"「一心传」名刀"}

DbPathOption = Annotated[Path, typer.Option("--db-path", help="SQLite 数据库路径。")]
AccountDbPathOption = Annotated[Path, typer.Option("--account-db-path", help="账号 SQLite 数据库路径。")]
CacheDirOption = Annotated[Path, typer.Option("--cache-dir", help="原始 JSON 缓存目录。")]
LanguageOption = Annotated[str, typer.Option("--language", help="数据语言。")]


@app.command("init")
def init_command(db_path: DbPathOption = DEFAULT_DB_PATH) -> None:
    """初始化本地角色数据库。"""
    ensure_data_dirs(db_path=db_path)
    init_db(db_path)
    typer.echo(f"已初始化数据库：{db_path}")


@app.command("init-account")
def init_account_command(account_db_path: AccountDbPathOption = DEFAULT_ACCOUNT_DB_PATH) -> None:
    """初始化独立账号数据库。"""
    ensure_data_dirs(db_path=account_db_path)
    init_account_db(account_db_path)
    typer.echo(f"已初始化账号数据库：{account_db_path}")


@app.command("sync-characters")
def sync_characters(
    db_path: DbPathOption = DEFAULT_DB_PATH,
    cache_dir: CacheDirOption = DEFAULT_CACHE_DIR,
    language: LanguageOption = "chinese",
    limit: Annotated[int | None, typer.Option("--limit", help="仅同步前 N 个角色，用于快速验证。")] = None,
    include_traveler: Annotated[
        bool,
        typer.Option("--include-traveler", help="包含旅行者空/荧。默认暂时排除。"),
    ] = False,
) -> None:
    """同步角色资料、天赋、命座和等级面板。"""
    ensure_data_dirs(db_path=db_path, cache_dir=cache_dir)
    init_db(db_path)
    session_factory = make_session_factory(db_path)
    synced = 0
    skipped: list[str] = []

    with GenshinDbCharacterClient() as client:
        try:
            names = client.list_character_names(language=language)
        except CharacterDataError as exc:
            _abort(str(exc))
        if not include_traveler:
            names = [name for name in names if name not in {"空", "荧"}]
        if limit is not None:
            names = names[:limit]

        with session_factory.begin() as session:
            sync_run = create_sync_run(session, language=language)
            for index, name in enumerate(names, start=1):
                typer.echo(f"[{index}/{len(names)}] 同步角色：{name}")
                try:
                    character_payload = client.fetch_character(name, language=language)
                except CharacterDataError as exc:
                    skipped.append(f"{name}: {exc}")
                    typer.echo(f"  跳过：{exc}")
                    continue

                talent_payload = _optional_payload(
                    lambda: client.fetch_talents(name, language=language),
                    name,
                    "天赋",
                )
                constellation_payload = _optional_payload(
                    lambda: client.fetch_constellations(name, language=language),
                    name,
                    "命座",
                )
                stats_payload = _optional_payload(
                    lambda: client.fetch_stats(name, language=language),
                    name,
                    "等级面板",
                )

                write_character_cache(name, "character", character_payload, cache_dir)
                write_character_cache(name, "talents", talent_payload, cache_dir)
                write_character_cache(name, "constellations", constellation_payload, cache_dir)
                write_character_cache(name, "stats", stats_payload, cache_dir)
                upsert_character(
                    session,
                    character_payload=character_payload,
                    talent_payload=talent_payload,
                    constellation_payload=constellation_payload,
                    stats_payload=stats_payload,
                )
                synced += 1
            finish_sync_run(sync_run, synced, skipped)

    typer.echo(f"完成：已同步 {synced} 个角色到 {db_path}")
    if skipped:
        typer.echo(f"跳过 {len(skipped)} 个角色：")
        for item in skipped[:20]:
            typer.echo(f"- {item}")
        if len(skipped) > 20:
            typer.echo(f"- 另外还有 {len(skipped) - 20} 个。")


@app.command("sync-weapons")
def sync_weapons(
    db_path: DbPathOption = DEFAULT_DB_PATH,
    cache_dir: CacheDirOption = DEFAULT_WEAPON_CACHE_DIR,
    language: LanguageOption = "chinese",
    limit: Annotated[int | None, typer.Option("--limit", help="仅同步前 N 个武器，用于快速验证。")] = None,
) -> None:
    """同步武器资料和等级面板。"""
    ensure_data_dirs(db_path=db_path, cache_dir=cache_dir)
    init_db(db_path)
    session_factory = make_session_factory(db_path)
    synced = 0
    skipped: list[str] = []

    with GenshinDbCharacterClient() as client:
        try:
            weapon_results = client.list_weapon_payloads(language=language)
        except CharacterDataError as exc:
            _abort(str(exc))
        weapon_results = [
            weapon for weapon in weapon_results
            if str(weapon.get("name") or "") not in EXCLUDED_WEAPON_NAMES
        ]
        if limit is not None:
            weapon_results = weapon_results[:limit]

        with session_factory.begin() as session:
            for index, weapon_result in enumerate(weapon_results, start=1):
                name = str(weapon_result.get("name") or weapon_result.get("id") or "")
                typer.echo(f"[{index}/{len(weapon_results)}] 同步武器：{name}")
                try:
                    weapon_payload = {
                        "query": name,
                        "folder": "weapons",
                        "match": name,
                        "matchfolder": "weapons",
                        "matchtype": "verboseCategories",
                        "result": weapon_result,
                    }
                except CharacterDataError as exc:
                    skipped.append(f"{name}: {exc}")
                    typer.echo(f"  跳过：{exc}")
                    continue

                stats_payload = _optional_payload(
                    lambda: client.fetch_weapon_stats(name, language=language),
                    name,
                    "等级面板",
                )

                write_character_cache(name, "weapon", weapon_payload, cache_dir)
                write_character_cache(name, "stats", stats_payload, cache_dir)
                upsert_weapon(
                    session,
                    weapon_payload=weapon_payload,
                    stats_payload=stats_payload,
                )
                synced += 1

    typer.echo(f"完成：已同步 {synced} 把武器到 {db_path}")
    if skipped:
        typer.echo(f"跳过 {len(skipped)} 把武器：")
        for item in skipped[:20]:
            typer.echo(f"- {item}")
        if len(skipped) > 20:
            typer.echo(f"- 另外还有 {len(skipped) - 20} 把。")


@app.command("sync-artifacts")
def sync_artifacts(
    db_path: DbPathOption = DEFAULT_DB_PATH,
    cache_dir: CacheDirOption = DEFAULT_ARTIFACT_CACHE_DIR,
    language: LanguageOption = "chinese",
    limit: Annotated[int | None, typer.Option("--limit", help="仅同步前 N 个圣遗物套装，用于快速验证。")] = None,
) -> None:
    """同步圣遗物套装名称、部位名称和套装效果。"""
    ensure_data_dirs(db_path=db_path, cache_dir=cache_dir)
    init_db(db_path)
    session_factory = make_session_factory(db_path)
    synced = 0

    with GenshinDbCharacterClient() as client:
        try:
            artifact_results = client.list_artifact_payloads(language=language)
        except CharacterDataError as exc:
            _abort(str(exc))
        if limit is not None:
            artifact_results = artifact_results[:limit]

        with session_factory.begin() as session:
            for index, artifact_payload in enumerate(artifact_results, start=1):
                name = str(artifact_payload.get("name") or artifact_payload.get("id") or "")
                typer.echo(f"[{index}/{len(artifact_results)}] 同步圣遗物套装：{name}")
                write_character_cache(name, "artifact", artifact_payload, cache_dir)
                upsert_artifact_set(session, artifact_payload=artifact_payload)
                synced += 1

    typer.echo(f"完成：已同步 {synced} 个圣遗物套装到 {db_path}")


@app.command("stats")
def stats_command(db_path: DbPathOption = DEFAULT_DB_PATH) -> None:
    """查看静态资料库统计。"""
    init_db(db_path)
    session_factory = make_session_factory(db_path)
    with session_factory() as session:
        typer.echo(f"角色数量：{count_characters(session)}")
        typer.echo(f"武器数量：{count_weapons(session)}")
        typer.echo(f"圣遗物套装数量：{count_artifact_sets(session)}")


@app.command("account-stats")
def account_stats_command(account_db_path: AccountDbPathOption = DEFAULT_ACCOUNT_DB_PATH) -> None:
    """查看独立账号数据库统计。"""
    init_account_db(account_db_path)
    session_factory = make_account_session_factory(account_db_path)
    with session_factory() as session:
        typer.echo(f"账号数量：{count_accounts(session)}")
        typer.echo(f"账号角色数量：{count_account_characters(session)}")
        typer.echo(f"账号武器数量：{count_account_weapons(session)}")
        typer.echo(f"账号圣遗物数量：{count_account_artifacts(session)}")


@app.command("list-characters")
def list_characters_command(
    db_path: DbPathOption = DEFAULT_DB_PATH,
    limit: Annotated[int | None, typer.Option("--limit", help="最多显示多少个角色。")] = None,
) -> None:
    """按图鉴列表形式展示角色。"""
    init_db(db_path)
    session_factory = make_session_factory(db_path)
    with session_factory() as session:
        characters = list_characters(session, limit=limit)
        if not characters:
            _abort("数据库中还没有角色。请先运行 sync-characters。")
        for character in characters:
            typer.echo(
                f"{character.name} | {character.element or '-'} | "
                f"{character.weapon_type or '-'} | {character.rarity or '-'}"
            )


@app.command("show-character")
def show_character_command(
    name: Annotated[str, typer.Argument(help="角色名称，例如：胡桃。")],
    db_path: DbPathOption = DEFAULT_DB_PATH,
    raw: Annotated[bool, typer.Option("--raw", help="输出完整 JSON。")] = False,
) -> None:
    """查看单个角色详情。"""
    init_db(db_path)
    session_factory = make_session_factory(db_path)
    with session_factory() as session:
        matches = find_character(session, name)
        if not matches:
            _abort(f"未找到角色：{name}")
        character = get_character(session, name) or matches[0]
        if raw:
            typer.echo(json.dumps(_character_payload(character), ensure_ascii=False, indent=2))
            return
        typer.echo(f"名称：{character.name}")
        typer.echo(f"星级：{character.rarity or '-'}")
        typer.echo(f"元素：{character.element or '-'}")
        typer.echo(f"武器：{character.weapon_type or '-'}")


@app.command("list-weapons")
def list_weapons_command(
    db_path: DbPathOption = DEFAULT_DB_PATH,
    limit: Annotated[int | None, typer.Option("--limit", help="最多显示多少把武器。")] = None,
) -> None:
    """按列表形式展示武器。"""
    init_db(db_path)
    session_factory = make_session_factory(db_path)
    with session_factory() as session:
        weapons = list_weapons(session, limit=limit)
        if not weapons:
            _abort("数据库中还没有武器。请先运行 sync-weapons。")
        for weapon in weapons:
            typer.echo(
                f"{weapon.name} | {weapon.weapon_type or '-'} | {weapon.rarity or '-'}"
            )


@app.command("show-weapon")
def show_weapon_command(
    name: Annotated[str, typer.Argument(help="武器名称，例如：护摩之杖。")],
    db_path: DbPathOption = DEFAULT_DB_PATH,
    raw: Annotated[bool, typer.Option("--raw", help="输出完整 JSON。")] = False,
) -> None:
    """查看单把武器详情。"""
    init_db(db_path)
    session_factory = make_session_factory(db_path)
    with session_factory() as session:
        matches = find_weapon(session, name)
        if not matches:
            _abort(f"未找到武器：{name}")
        weapon = get_weapon(session, name) or matches[0]
        if raw:
            typer.echo(json.dumps(_weapon_payload(weapon), ensure_ascii=False, indent=2))
            return
        data = weapon.weapon_data.get("result", {})
        typer.echo(f"名称：{weapon.name}")
        typer.echo(f"星级：{weapon.rarity or '-'}")
        typer.echo(f"类型：{weapon.weapon_type or '-'}")
        typer.echo(f"副属性：{data.get('mainStatText') or '-'}")
        typer.echo(f"特效：{data.get('effectName') or '-'}")


@app.command("list-artifacts")
def list_artifacts_command(
    db_path: DbPathOption = DEFAULT_DB_PATH,
    limit: Annotated[int | None, typer.Option("--limit", help="最多显示多少个圣遗物套装。")] = None,
) -> None:
    """按列表形式展示圣遗物套装。"""
    init_db(db_path)
    session_factory = make_session_factory(db_path)
    with session_factory() as session:
        artifact_sets = list_artifact_sets(session, limit=limit)
        if not artifact_sets:
            _abort("数据库中还没有圣遗物套装。请先运行 sync-artifacts。")
        for artifact_set in artifact_sets:
            typer.echo(
                f"{artifact_set.name} | "
                f"1件：{artifact_set.effect_1pc or '-'} | "
                f"2件：{artifact_set.effect_2pc or '-'} | "
                f"4件：{artifact_set.effect_4pc or '-'}"
            )


@app.command("show-artifact")
def show_artifact_command(
    name: Annotated[str, typer.Argument(help="圣遗物套装名称，例如：绝缘之旗印。")],
    db_path: DbPathOption = DEFAULT_DB_PATH,
    raw: Annotated[bool, typer.Option("--raw", help="输出完整 JSON。")] = False,
) -> None:
    """查看单个圣遗物套装详情。"""
    init_db(db_path)
    session_factory = make_session_factory(db_path)
    with session_factory() as session:
        matches = find_artifact_set(session, name)
        if not matches:
            _abort(f"未找到圣遗物套装：{name}")
        artifact_set = get_artifact_set(session, name) or matches[0]
        if raw:
            typer.echo(json.dumps(_artifact_set_payload(artifact_set), ensure_ascii=False, indent=2))
            return
        typer.echo(f"名称：{artifact_set.name}")
        typer.echo(f"生之花：{artifact_set.flower_name or '-'}")
        typer.echo(f"死之羽：{artifact_set.plume_name or '-'}")
        typer.echo(f"时之沙：{artifact_set.sands_name or '-'}")
        typer.echo(f"空之杯：{artifact_set.goblet_name or '-'}")
        typer.echo(f"理之冠：{artifact_set.circlet_name or '-'}")
        typer.echo(f"1件效果：{artifact_set.effect_1pc or '-'}")
        typer.echo(f"2件效果：{artifact_set.effect_2pc or '-'}")
        typer.echo(f"4件效果：{artifact_set.effect_4pc or '-'}")


def _character_payload(character) -> dict[str, object]:
    return {
        "name": character.name,
        "rarity": character.rarity,
        "element": character.element,
        "weapon_type": character.weapon_type,
        "character_data": character.character_data,
        "talent_data": character.talent_data,
        "constellation_data": character.constellation_data,
        "stats_data": character.stats_data,
    }


def _weapon_payload(weapon) -> dict[str, object]:
    return {
        "name": weapon.name,
        "rarity": weapon.rarity,
        "weapon_type": weapon.weapon_type,
        "weapon_data": weapon.weapon_data,
        "stats_data": weapon.stats_data,
    }


def _artifact_set_payload(artifact_set) -> dict[str, object]:
    return {
        "name": artifact_set.name,
        "flower_name": artifact_set.flower_name,
        "plume_name": artifact_set.plume_name,
        "sands_name": artifact_set.sands_name,
        "goblet_name": artifact_set.goblet_name,
        "circlet_name": artifact_set.circlet_name,
        "effect_1pc": artifact_set.effect_1pc,
        "effect_2pc": artifact_set.effect_2pc,
        "effect_4pc": artifact_set.effect_4pc,
    }


def _optional_payload(fetcher, name: str, label: str) -> dict[str, object]:
    try:
        return fetcher()
    except CharacterDataError as exc:
        return {
            "query": name,
            "section": label,
            "result": {},
            "error": str(exc),
        }


def _abort(message: str) -> None:
    typer.secho(f"错误：{message}", err=True, fg=typer.colors.RED)
    raise typer.Exit(code=1)
