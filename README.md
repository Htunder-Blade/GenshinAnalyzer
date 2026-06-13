# GenshinAnalyzer

`GenshinAnalyzer` 当前阶段先做一件事：在本地建立一个服务于练度和伤害计算的原神资料数据库。

这个阶段参考 HoYoLAB Wiki 的图鉴模式组织数据：先有列表，再能进入单个条目详情。角色表只保留 `name`、`rarity`、`element`、`weapon_type`、`character_data`、`talent_data`、`constellation_data`、`stats_data`。武器表只保留 `name`、`rarity`、`weapon_type`、`weapon_data`、`stats_data`。圣遗物套装表只保留 `name`、`flower_name`、`plume_name`、`sands_name`、`goblet_name`、`circlet_name`、`effect_1pc`、`effect_2pc`、`effect_4pc`。

项目同时预留一个区别于静态资料库的独立账号库文件。`accounts` 只记录账号 `uid`；`account_characters` 记录该 uid 下的角色名称、角色等级、突破、命座、普攻/战技/爆发等级，并引用已装备武器和五件圣遗物；`account_weapons` 记录账号武器背包中的武器名称、等级和精炼等级；`account_artifacts` 记录圣遗物背包中的套装名称、部位、部件名称、等级、星级、主词条和副词条。伤害计算时，账号库负责“这个 uid 实际拥有什么”，静态资料库负责按名称映射角色、武器和圣遗物套装面板/效果。

## 项目语言约定

除代码、文件名、路径名、命令、第三方库名称、API 字段名等必须保留原文的内容外，项目内文档、说明、注释、Notebook 展示文本尽量使用中文。

## 数据来源

- HoYoLAB Wiki：作为本地资料库的组织方式参考。
- `genshin-db-api`：作为当前可程序化下载的开源角色、武器和圣遗物资料来源。

## 安装

```powershell
python -m pip install -e ".[dev]"
```

## GitHub 协作初始化流程

这个仓库适合先作为私有仓库协作。仓库只保存源码、Notebook、文档和可维护的数据定义；本地生成的 SQLite 数据库、账号数据和原始下载缓存不进入 Git 历史。

朋友首次 clone 后，在项目根目录执行：

```powershell
python -m pip install -e ".[dev]"
genshin-analyzer init
genshin-analyzer sync-characters
genshin-analyzer sync-weapons
genshin-analyzer sync-artifacts
genshin-analyzer init-account
```

完成后可用下面两个命令确认本地数据库已经生成：

```powershell
genshin-analyzer stats
genshin-analyzer account-stats
```

也可以打开 Notebook 做展示层验证：

```powershell
jupyter notebook notebooks/character_database_view.ipynb
jupyter notebook notebooks/weapon_database_view.ipynb
jupyter notebook notebooks/artifact_database_view.ipynb
```

## 使用

初始化数据库：

```powershell
genshin-analyzer init
```

初始化独立账号数据库：

```powershell
genshin-analyzer init-account
```

同步全部角色资料：

```powershell
genshin-analyzer sync-characters
```

同步全部武器资料：

```powershell
genshin-analyzer sync-weapons
```

同步全部圣遗物套装资料：

```powershell
genshin-analyzer sync-artifacts
```

快速验证时只同步前几个角色：

```powershell
genshin-analyzer sync-characters --limit 5
genshin-analyzer sync-weapons --limit 5
genshin-analyzer sync-artifacts --limit 5
```

查看数据库统计：

```powershell
genshin-analyzer stats
```

查看账号数据库统计：

```powershell
genshin-analyzer account-stats
```

打开账号录入 Notebook，手动录入 UID、角色、武器和圣遗物测试数据：

```powershell
jupyter notebook notebooks/account_data_entry.ipynb
```

打开角色 Notebook 查看统计和检索界面：

```powershell
jupyter notebook notebooks/character_database_view.ipynb
```

打开武器 Notebook 验证武器数据库：

```powershell
jupyter notebook notebooks/weapon_database_view.ipynb
```

打开圣遗物 Notebook 验证圣遗物套装数据库：

```powershell
jupyter notebook notebooks/artifact_database_view.ipynb
```

查看角色图鉴列表：

```powershell
genshin-analyzer list-characters
```

查看武器列表：

```powershell
genshin-analyzer list-weapons
```

查看圣遗物套装列表：

```powershell
genshin-analyzer list-artifacts
```

查看单个角色详情：

```powershell
genshin-analyzer show-character 胡桃
```

查看单把武器详情：

```powershell
genshin-analyzer show-weapon 护摩之杖
```

查看单套圣遗物详情：

```powershell
genshin-analyzer show-artifact 绝缘之旗印
```

输出单个角色的瘦身 JSON：

```powershell
genshin-analyzer show-character 胡桃 --raw
```

输出单把武器的瘦身 JSON：

```powershell
genshin-analyzer show-weapon 护摩之杖 --raw
```

输出单套圣遗物的瘦身 JSON：

```powershell
genshin-analyzer show-artifact 绝缘之旗印 --raw
```

## 默认数据位置

- 静态资料 SQLite 数据库：`data/genshin.sqlite3`
- 账号 SQLite 数据库：`account_data/cache/account.sqlite3`
- 原始 JSON 缓存：`data/cache/characters/{角色名}/`
- 原始武器 JSON 缓存：`data/cache/weapons/{武器名}/`
- 原始圣遗物 JSON 缓存：`data/cache/artifacts/{套装名}/`

这些路径都是本地生成内容，默认被 `.gitignore` 排除。`data/genshin.sqlite3` 可以通过同步命令重建；`account_data/cache/account.sqlite3` 属于个人账号库，默认不上传、不共享。上传到 GitHub 前，应在 Git 客户端中确认待提交列表不包含 `data/`、`account_data/`、`*.sqlite3` 或 `__pycache__/`。

如果未来需要分发生成好的完整数据库，优先使用 GitHub Release、网盘或 Git LFS；不要直接把完整 SQLite 文件提交到主仓库。

## 当前边界

- 当前只做角色、武器和圣遗物套装数据库。
- 当前账号库只建立空表结构，不录入具体 uid、角色、武器或圣遗物数据。
- 当前跳过三把重名的「一心传」名刀，保证武器名称可以作为主键。
- 当前圣遗物数据库只关注套装名称、各部位名称和套装效果。
- 当前不抓取 HoYoLAB 页面本身，而是用 HoYoLAB Wiki 的图鉴组织方式来设计本地库。
- 当前同步的字段取决于 `genshin-db-api` 可提供的数据。
