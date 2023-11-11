## World Translation Extractor
Forked by [WorldTranslationExtractor](https://github.com/5uso/AmuletScripts/blob/main/WorldTranslationExtractor.py)

### Information
This version changes some things.
Needs `amulet-map-editor` and `tqdm`.

Install: `pip install amulet-map-editor`, `pip install tqdm`

### Changes

1. Keep duplicate keys.
2. Backup the world.
3. Modify `handle_sign` function to be available on 1.19+.
4. Supports command in the command blocks.
5. Convert to standard JSON format to generate language file.

Here is the original `README.md`:

## Original Readme

Scans a full world searching for json `"text"` components and replaces them with `"translation"` components, generating a lang file to be used with a resourcepack. Tested in `1.16.5` and `1.19.3`.

Finds json components in:
- Blocks
  - Spawners: SpawnData, SpawnPotentials
  - Containers: items, container name (`"chest"`, `"furnace"`, `"shulker_box"`, `"barrel"`, `"smoker"`, `"blast_furnace"`, `"trapped_chest"`, `"hopper"`, `"dispenser"`, `"dropper"`, `"brewing_stand"`, `"campfire"`)
  - Signs: text1-4
  - Lecterns: Book
  - Jukeboxes: RecordItem

- Entities
  - Name
  - Items
  - ArmorItems
  - HandItems
  - Inventory
  - Villager offers
  - Passengers

- Items
  - Name
  - Lore
  - Book pages
  - Book title: adds a customname in case it doesn't already have one
  - BlockEntityTag
  - EntityTag:

- Scoreboard: objective names, team names and affixes

- Bossbars: names

- Datapacks: functions, json files

- Structures: blocks, entities

Usage: `python WorldTranslationExtractor.py <world>` (Modifies world, outputs `default_lang.json` in the working directory)

Dependencies: `pip install amulet-map-editor` `pip install tqdm`
