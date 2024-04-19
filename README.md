## World Translation Extractor Modified (WTEM) 2.5
Forked by [WorldTranslationExtractor](https://github.com/5uso/AmuletScripts/blob/main/WorldTranslationExtractor.py)

### Information
This version changes some things.
Needs `amulet-map-editor` and `tqdm`.

Install: `pip install amulet-map-editor`, `pip install tqdm`

### Changes

1. Allow to keep duplicate keys.
2. Allow to backup the world.
3. Support signs on 1.19+, chiseled bookshelves, decorated pots (1.19+), 
command blocks, beehive and bee nest.
4. Convert to standard JSON format to generate language file.
5. Add config.
6. Support display entities.
7. Support marco commands in datapacks.

### Tip

1. WTEM cannot change the target selector `name=` and the container's `Lock` tag, but it will be recorded for later reference and correction.

## Original Readme

The underlined and bold text means that this feature is newly added.

Here is the original `README.md`:

Scans a full world searching for json `"text"` components and replaces them with `"translation"` components, generating a lang file to be used with a resourcepack. Tested in `1.16.5` and `1.19.3`.

Finds json components in:
- Blocks
  - Spawners: SpawnData, SpawnPotentials
  - Containers: items, container name (`"chest"`, `"furnace"`, `"shulker_box"`, `"barrel"`, `"smoker"`, `"blast_furnace"`, `"trapped_chest"`, `"hopper"`, `"dispenser"`, `"dropper"`, `"brewing_stand"`, `"campfire"`, <u>**`"chiseled_bookshelf"`**</u>, <u>**`"decorated_pot"`**</u>)
  - Signs: text1-4, <u>**front_text, back_text**</u>
  - Lecterns: Book
  - Jukeboxes: RecordItem
  - <u>**Beehives & Bee nests: Bees**
  - **Command block: Command**</u>

- Entities
  - Name
  - Items
  - ArmorItems
  - HandItems
  - Inventory
  - Villager offers
  - Passengers
  - <u>**Text Display**</u>
  - <u>**Item Display**</u>

- Items
  - Name
  - Lore
  - Book pages
  - Book title: adds a customname in case it doesn't already have one
  - BlockEntityTag
  - EntityTag

- Scoreboard: objective names, team names and affixes

- Bossbars: names

- Datapacks: functions, json files

- Structures: blocks, entities

Usage: `python WorldTranslationExtractor.py <world>` (Modifies world, outputs `default_lang.json` in the working directory)
