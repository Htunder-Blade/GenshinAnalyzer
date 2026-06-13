# Genshin Artifact 5-Star Domain PMF

This package contains a machine-readable probability model for Genshin Impact 5-star artifact generation and enhancement.

## Main file
- `genshin_artifact_5star_domain_pmf.json`

## CSV exports
- `set_pmf.csv`
- `slot_pmf.csv`
- `main_stat_pmf_by_slot.csv`
- `initial_substat_count_pmf.csv`
- `minor_affix_type_weights.csv`
- `minor_affix_roll_values_5star.csv`

## Localization helpers
- `stat_name_mapping_zh_en.json`

## Important modeling notes
- Scope: 5-star artifacts from artifact domains.
- Two domain sets are modeled as 50/50.
- Slots are modeled as uniform 20% each.
- Initial substat count is modeled as 3-line 80%, 4-line 20%. Keep this configurable.
- Minor affix type PMF is dynamic: remove the main stat if identical and remove existing minor affixes, then normalize fixed weights.
- Minor affix value tiers are uniform across 70/80/90/100% tiers.
- When four substats exist, the upgrade target slot is uniform 25% each.

## Stat naming
The JSON uses uppercase snake_case names, e.g. `CRIT_RATE`, `CRIT_DMG`, `ENERGY_RECHARGE`.
Use `stat_name_mapping_zh_en.json` when converting artifact stat names between English identifiers and Simplified Chinese display/input names.
