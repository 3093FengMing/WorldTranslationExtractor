import os
import re
import shutil
import sys

import json
import logging
import time
from imp import reload

import amulet
import amulet_nbt as n
from tqdm import tqdm

# Logger

FORMATTER = logging.Formatter("%(asctime)s - %(name)s - %(funcName)s[line:%(lineno)d] - %(levelname)s: %(message)s")

file_handler = logging.FileHandler(f'{time.strftime("%Y_%m_%d %H-%M-%S")}.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(FORMATTER)
file_handler.encoding = "utf-8"

LOGGER = logging.getLogger("WTEM")

# Config

cfg_settings = dict()
cfg_lang = dict()
cfg_dupe = dict()
cfg_default = dict()

# REG

OLD_SPAWNER_FORMAT = False  # If this is false, uses 1.18+ nbt paths for spawners

REG_COMPONENT = re.compile(r'"text" *: *"((?:[^"\\]|\\\\"|\\.)*)"')
REG_COMPONENT_PLAIN = re.compile(r'"((?:[^"\\]|\\\\"|\\.)*)"')
REG_COMPONENT_ESCAPED = re.compile(r'\\"text\\" *: *\\"((?:[^"\\]|\\\\.)*)\\"')
REG_DATAPACK_CONTENTS = re.compile(r'"contents":"((?:[^"\\]|\\\\"|\\.)*)"')
REG_BOSSBAR_SET_NAME = re.compile(r'bossbar set ([^ ]+) name "(.*)"')
REG_BOSSBAR_ADD = re.compile(r'bossbar add ([^ ]+) "(.*)"')
REG_MARCO_COMMAND = re.compile(r'\$\(.+\)')
CONTAINERS = ["chest", "furnace", "shulker_box", "barrel", "smoker", "blast_furnace", "trapped_chest", "hopper",
              "dispenser", "dropper", "brewing_stand", "campfire", "chiseled_bookshelf"]

rev_lang = dict()  # Keep duplicates (reversed)
rel_lang = dict()  # Normal language file format

item_counts = dict()
block_counts = dict()
entity_counts = dict()

key = "no_key"
key_cnt = 0


# keys
def set_key(k):
    global key, key_cnt
    key = k
    key_cnt = 0


def get_key():
    global key_cnt
    key_cnt += 1
    return f"{key}.{key_cnt}"


# match & replace
def sub_replace(pattern: re.Pattern, string: str, repl, dupe=False, search_all=True, is_marco=False):
    if search_all:
        ls = list(string)
        loop_count = 0
        last_match = None
        match = pattern.search(string)
        # can delete the 2 lines below
        if match is None:
            return string
        while match is not None:
            # prevent endless loop
            if cfg_settings['components_max'] != -1 and last_match is not None and last_match.string == match.string:
                loop_count += 1
                if loop_count >= cfg_settings['components_max']:
                    LOGGER.error(f"TOO MANY COMPONENTS HERE: {string}")
            span = match.span()
            ls[span[0]:span[1]] = repl(match, dupe=dupe, is_marco=is_marco)
            match = pattern.search(''.join(ls))
            last_match = match
        return ''.join(ls)
    else:
        match = pattern.match(string)
        return string if match is None else repl(match, dupe=dupe)


def marcos_extract(string: str):
    marcos = list()
    ls = list(string)
    loop_count = 0
    last_match = None
    match = REG_MARCO_COMMAND.search(string)
    if match is None:
        return string
    while match is not None:
        # prevent endless loop
        if cfg_settings['marco_max'] != -1 and last_match is not None and last_match.string == match.string:
            loop_count += 1
            if loop_count >= cfg_settings['marco_max']:
                LOGGER.error(f"TOO MANY MARCOS HERE: {string}")
        span = match.span()
        marcos.append(''.join(ls[span[0]:span[1]]))
        ls[span[0]:span[1]] = "[extracted]"
        match = REG_MARCO_COMMAND.search(''.join(ls))
        last_match = match
    return marcos


def get_plain_from_match(match, escaped=False, ord=1):
    plain = match if isinstance(match, str) else match.group(ord)
    if escaped:
        plain = re.sub(pattern=r'\\\\', string=plain, repl=r'\\')
    plain = re.sub(pattern=r'\\\\([^\\])', string=plain, repl=r'\\\1')
    plain = re.sub(pattern=r"\\'", string=plain, repl=r"'")
    return plain


def match_text(match, escaped=False, dupe=False, is_marco=False):
    plain = get_plain_from_match(match, escaped)
    rk = get_key()
    if is_marco:
        crk = rk
        for m in marcos_extract(plain):
            crk = crk + "." + m
        rk = crk
    if plain not in rev_lang:
        rev_lang[plain] = rk
    if plain in cfg_default:
        LOGGER.info(f'[text default] {cfg_default[plain]}: {plain}')
        return f'\\"translate\\":\\"{cfg_default[plain]}\\"' if escaped else f'"translate":"{cfg_default[plain]}"'
    rel_lang[rk] = plain
    if dupe:
        LOGGER.info(f'[text dupeIf] put key: {rk}: {rel_lang[rk]}')
        return f'\\"translate\\":\\"{rk}\\"' if escaped else f'"translate":"{rk}"'
    LOGGER.info(f'[text dupeElse] put key: {rev_lang[plain]}: {plain}')
    return f'\\"translate\\":\\"{rev_lang[plain]}\\"' if escaped else f'"translate":"{rev_lang[plain]}"'


def match_plain_text(match, dupe=False):
    plain = match.string[1:-1]
    rk = get_key()
    if plain not in rev_lang:
        rev_lang[plain] = rk
    if plain in cfg_default:
        LOGGER.info(f'[plain default] {cfg_default[plain]}: {plain}')
        return f'{{"translate":"{cfg_default[plain]}"}}'
    rel_lang[rk] = plain
    if dupe:
        LOGGER.info(f'[plain dupeIf] put key: {rk}: {rel_lang[rk]}')
        return f'{{"translate":"{rk}"}}'
    LOGGER.info(f'[plain dupeElse] put key: {rev_lang[plain]}: {plain}')
    return f'{{"translate":"{rev_lang[plain]}"}}'


def match_contents(match, dupe=False):
    plain = get_plain_from_match(match)
    rk = get_key()
    if plain not in rev_lang:
        rev_lang[plain] = rk
    if plain in cfg_default:
        LOGGER.info(f'[contents default] {cfg_default[plain]}: {plain}')
        return f'"contents":{{{cfg_default[plain]}}}'
    rel_lang[rk] = plain
    if dupe:
        LOGGER.info(f'[contents dupeIf] put key: {rk}: {rel_lang[rk]}')
        return f'"contents":{{"translate":"{rk}"}}'
    LOGGER.info(f'[contents dupeElse] put key: {rev_lang[plain]}: {plain}')
    return f'"contents":{{"translate":"{rev_lang[plain]}"}}'


def match_bossbar(match, dupe=False, is_marco=False):
    plain = get_plain_from_match(match, ord=2)
    name = match.group(1)
    rk = get_key()
    if is_marco:
        crk = rk
        for m in marcos_extract(plain):
            crk = crk + "." + m
        rk = crk
    if plain not in rev_lang:
        rev_lang[plain] = rk
    if plain in cfg_default:
        LOGGER.info(f'[bossbar set default] {cfg_default[plain]}: {plain}')
        return f'bossbar set {name} name {{{cfg_default[plain]}}}'
    rel_lang[rk] = plain
    if dupe:
        LOGGER.info(f'[bossbar set dupeIf] put key: {rk}: {rel_lang[rk]}')
        return f'bossbar set {name} name {{"translate":"{rk}"}}'
    LOGGER.info(f'[bossbar set dupeElse] put key: {rev_lang[plain]}: {plain}')
    return f'bossbar set {name} name {{"translate":"{rev_lang[plain]}"}}'


def match_bossbar2(match, dupe=False, is_marco=False):
    plain = get_plain_from_match(match, ord=2)
    name = match.group(1)
    rk = get_key()
    if is_marco:
        crk = rk
        for m in marcos_extract(plain):
            crk = crk + "." + m
        rk = crk
    if plain not in rev_lang:
        rev_lang[plain] = rk
    if plain in cfg_default:
        LOGGER.info(f'[bossbar add default] {cfg_default[plain]}: {plain}')
        return f'bossbar add {name} name {{{cfg_default[plain]}}}'
    rel_lang[rk] = plain
    if dupe:
        LOGGER.info(f'[bossbar add dupeIf] put key: {rk}: {rel_lang[rk]}')
        return f'bossbar add {name} {{"translate":"{rk}"}}'
    LOGGER.info(f'[bossbar add dupeElse] put key: {rev_lang[plain]}: {plain}')
    return f'bossbar add {name} {{"translate":"{rev_lang[plain]}"}}'


def match_text_escaped(match, dupe=False, is_marco=False):
    return match_text(match, True, dupe, is_marco)


def replace_component(text, dupe=False):
    text = sub_replace(REG_COMPONENT_PLAIN, str(text), match_plain_text, dupe, False)
    text = sub_replace(REG_COMPONENT, str(text), match_text, dupe)
    return n.TAG_String(sub_replace(REG_COMPONENT_ESCAPED, text, match_text_escaped, dupe))


# handler
def handle_item(item, dupe=False):
    changed = False
    if len(item) == 0:
        return False
    id = str(item['id'])[10:]
    item_counts.setdefault(id, 1)
    translation_cnt = len(rel_lang)

    try:
        set_key(f"item.{id}.{item_counts[id]}.name")
        item['tag']['display']['Name'] = replace_component(item['tag']['display']['Name'],
                                                           dupe | cfg_dupe["items_name"] | cfg_dupe["items_all"])
        changed = True
    except KeyError:
        pass

    try:
        for line in range(len(item['tag']['display']['Lore'])):
            set_key(f"item.{id}.{item_counts[id]}.lore.{line}")
            item['tag']['display']['Lore'][line] = replace_component(item['tag']['display']['Lore'][line],
                                                                     dupe | cfg_dupe["items_lore"] | cfg_dupe[
                                                                         "items_all"])
        changed = True
    except KeyError:
        pass

    try:
        for page in range(len(item['tag']['pages'])):
            set_key(f"item.{id}.{item_counts[id]}.page.{page}")
            item['tag']['pages'][page] = replace_component(item['tag']['pages'][page],
                                                           dupe | cfg_dupe["items_pages"] | cfg_dupe["items_all"])
        changed = True
    except KeyError:
        pass

    try:
        title = str(item['tag']['title'])
        if "display" not in item['tag']:
            item['tag']['display'] = n.TAG_Compound()
        if "Name" not in item['tag']['display']:
            # TODO remember to sync it when `match_text` changed
            # NOT use default keys
            rk = f"item.{id}.{item_counts[id]}.title.1"
            rel_lang[rk] = title
            if title not in rev_lang:
                rev_lang[title] = rk
            if dupe or cfg_dupe["items_title"] or cfg_dupe["items_all"]:
                LOGGER.info(f'[json book title dupeIf] put key: {rk}: {rel_lang[rk]}')
                item['tag']['display']['Name'] = n.TAG_String(f'{{"translate":"{rk}","italic":false}}')
            else:
                LOGGER.info(f'[json book title dupeElse] put key: {rev_lang[title]}: {title}')
                item['tag']['display']['Name'] = n.TAG_String(f'{{"translate":"{rev_lang[title]}","italic":false}}')
            changed = True
    except KeyError:
        pass

    if translation_cnt != len(rel_lang):
        item_counts[id] += 1

    try:
        changed |= handle_block_entity_nbt(item['tag']['BlockEntityTag'])
    except KeyError:
        pass

    try:
        changed |= handle_entity(item['tag']['EntityTag'], None)
    except KeyError:
        pass

    return changed


def handle_container(container, type):
    changed = False
    block_counts.setdefault(type, 1)
    translation_cnt = len(rel_lang)

    try:
        set_key(f"block.{type}.{block_counts[type]}.name")
        container['CustomName'] = replace_component(container['CustomName'], cfg_dupe["containers_name"])
        changed = True
    except KeyError:
        pass

    if translation_cnt != len(rel_lang):
        block_counts[type] += 1

    for item in container['Items']:
        changed |= handle_item(item, cfg_dupe["items_in_same"])

    return changed


def handle_item_entity_block(block, nbt_path):
    try:
        if isinstance(nbt_path, str):
            return handle_item(block[nbt_path])
        elif isinstance(nbt_path, list):
            last_path = ""
            last_tag = None
            for path in nbt_path:
                if last_path == "":
                    last_path = path
                    last_tag = block[last_path]
                else:
                    last_tag = block[last_path][path]
                    last_path = path
            return handle_item(last_tag)
    except KeyError:
        pass
    return False


def handle_command_block(command_block):
    block_counts.setdefault("command_block", 1)
    translation_cnt = len(rel_lang)
    set_key(f"block.command_block.{block_counts['command_block']}.command")

    command = str(command_block['Command'])
    txt = sub_replace(REG_COMPONENT, command, match_text, cfg_dupe["command_blocks"])
    txt = sub_replace(REG_COMPONENT_ESCAPED, txt, match_text_escaped, cfg_dupe["command_blocks"])
    # txt = sub_replace(REG_COMPONENT_PLAIN, txt, match_text, cfg_dupe["command_blocks"], False)
    txt = sub_replace(REG_DATAPACK_CONTENTS, txt, match_contents, cfg_dupe["command_blocks"])
    txt = sub_replace(REG_BOSSBAR_SET_NAME, txt, match_bossbar, cfg_dupe["command_blocks"])
    result_command = sub_replace(REG_BOSSBAR_ADD, txt, match_bossbar2, cfg_dupe["command_blocks"])
    command_block['Command'] = n.TAG_String(result_command)

    if translation_cnt != len(rel_lang):
        block_counts["command_block"] += 1

    return True


def handle_sign(sign):
    block_counts.setdefault("sign", 1)
    translation_cnt = len(rel_lang)

    if 'Text1' in sign.keys():
        set_key(f"block.sign.{block_counts['sign']}.text1")
        sign['Text1'] = replace_component(sign['Text1'], cfg_dupe["signs"])
        set_key(f"block.sign.{block_counts['sign']}.text2")
        sign['Text2'] = replace_component(sign['Text2'], cfg_dupe["signs"])
        set_key(f"block.sign.{block_counts['sign']}.text3")
        sign['Text3'] = replace_component(sign['Text3'], cfg_dupe["signs"])
        set_key(f"block.sign.{block_counts['sign']}.text4")
        sign['Text4'] = replace_component(sign['Text4'], cfg_dupe["signs"])
    else:
        # for 1.19+
        if 'front_text' in sign.keys():
            for i in range(len(sign['front_text']['messages'])):
                set_key(f"block.sign.{block_counts['sign']}.front_text{i + 1}")
                sign['front_text']['messages'][i] = replace_component(sign['front_text']['messages'][i],
                                                                      cfg_dupe["signs"])
        if 'back_text' in sign.keys():
            for i in range(len(sign['back_text']['messages'])):
                set_key(f"block.sign.{block_counts['sign']}.back_text{i + 1}")
                sign['back_text']['messages'][i] = replace_component(sign['back_text']['messages'][i],
                                                                     cfg_dupe["signs"])

    if translation_cnt != len(rel_lang):
        block_counts["sign"] += 1

    return True


def handle_spawner(spawner):
    changed = False
    try:
        if OLD_SPAWNER_FORMAT:
            changed = handle_entity(spawner['SpawnData'], None)
            for p in spawner['SpawnPotentials']:
                changed |= handle_entity(p['Entity'], None)
        else:
            changed = handle_entity(spawner['SpawnData']['entity'], None)
            for p in spawner['SpawnPotentials']:
                changed |= handle_entity(p['data']['entity'], None)
    except KeyError:
        pass
    return changed


def handle_beehive(beehive):
    changed = False
    try:
        for bee in beehive['Bees']:
            changed |= handle_entity(bee['EntityData'], None)
    except KeyError:
        pass
    return changed


def handle_entity(entity, type):
    changed = False
    id = type if type is not None else (str(entity['id'])[10:] if "id" in entity else "unknown")
    entity_counts.setdefault(id, 1)
    translation_cnt = len(rel_lang)

    if "CustomName" in entity:
        set_key(f"entity.{id}.{entity_counts[id]}.name")
        entity['CustomName'] = replace_component(entity['CustomName'], cfg_dupe["entities_name"])
        changed = True

    # Display entity
    if "text" in entity:
        set_key(f"entity.{id}.{entity_counts[id]}.text")
        entity['text'] = replace_component(entity['text'], cfg_dupe["show_entity_text"])
        changed = True

    if translation_cnt != len(rel_lang):
        entity_counts[id] += 1

    # Entity
    if "Items" in entity:
        for i in entity['Items']:
            changed |= handle_item(i)

    if "ArmorItems" in entity:
        for i in entity['ArmorItems']:
            changed |= handle_item(i)

    if "HandItems" in entity:
        for i in entity['HandItems']:
            changed |= handle_item(i)

    if "Item" in entity:
        changed |= handle_item(entity['Item'])

    if "Inventory" in entity:
        for i in entity['Inventory']:
            changed |= handle_item(i)

    # Villager
    if "Offers" in entity and "Recipes" in entity["Offers"]:
        for t in entity['Offers']['Recipes']:
            changed |= handle_item(t['buy'])
            changed |= handle_item(t['buyB'])
            changed |= handle_item(t['sell'])

    # Can be ridden
    if "Passengers" in entity:
        for p in entity['Passengers']:
            changed |= handle_entity(p, None)

    if "item" in entity:
        changed |= handle_item(entity['item'])

    return changed


def handle_block_entity_base(block_entity, name):
    if name == "spawner":
        return handle_spawner(block_entity)
    elif name in CONTAINERS:
        return handle_container(block_entity, name)
    elif name == "sign":
        return handle_sign(block_entity)
    elif name == "lectern":
        return handle_item_entity_block(block_entity, "Book")
    elif name == "jukebox":
        return handle_item_entity_block(block_entity, "RecordItem")
    elif name == "decorated_pot":
        return handle_item_entity_block(block_entity, "item")
    elif name == "command_block":
        return handle_command_block(block_entity)
    elif name == "beehive" or name == "bee_nest":
        return handle_beehive(block_entity)
    return False


def handle_block_entity_nbt(block_entity):
    id = str(block_entity['id'])
    changed = handle_block_entity_base(block_entity, id[10:])  # after "minecraft:"
    if changed:
        LOGGER.info(
            f"[block entity handler] {id[10:]}: ({str(block_entity['x'])},{str(block_entity['y'])},{str(block_entity['z'])})")
        LOGGER.info('---------')
    return changed


def handle_block_entity(block_entity):
    nbt = block_entity.nbt.tag['utags']
    changed = handle_block_entity_base(nbt, block_entity.base_name)
    if changed:
        LOGGER.info(
            f"[block entity handler] {block_entity.base_name}: ({block_entity.x},{block_entity.y},{block_entity.z})")
        LOGGER.info('---------')
    return changed


def handle_chunk(chunk):
    for block_entity in chunk.block_entities:
        chunk.changed |= handle_block_entity(block_entity)


def handle_entities(level, coords, dimension, entities):
    changed = False
    for e in entities:
        changed |= handle_entity(e.nbt.tag, e.base_name)
        if changed:
            LOGGER.info(f"[entity handler] {e.base_name}: ({e.x},{e.y},{e.z})")
            LOGGER.info('---------')
    if changed:
        level.set_native_entites(coords[0], coords[1], dimension, entities)


# scanner
def scan_world(level):
    for dimension in level.dimensions:
        chunk_coords = sorted(level.all_chunk_coords(dimension))
        if len(chunk_coords) < 1:
            continue
        LOGGER.info(f"维度/Dimension {dimension}: ")
        try:
            count = 0
            for coords in tqdm(chunk_coords, unit="区块", desc="扫描区块中/Scanning chunks", colour="green"):
                try:
                    chunk = level.get_chunk(coords[0], coords[1], dimension)
                    entities = level.get_native_entities(coords[0], coords[1], dimension)[0]
                except Exception:
                    pass
                else:
                    handle_chunk(chunk)
                    handle_entities(level, coords, dimension, entities)
                    count += 1
                    if count < 5000:
                        continue
                    count = 0
                    LOGGER.info("\n保存中......")
                    level.save()
                    level.unload()
            level.save()
        except KeyboardInterrupt:
            LOGGER.error(
                "中断！最后5000区块切片数据将不会保存！/Interrupted. Changes to last 5000 chunk slice won't be saved.")
            level.close()
            exit(0)
        level.unload()
    level.close()


def scan_scores(path):
    try:
        scores = n.load(path)
        for s in scores.tag['data']['Objectives']:
            set_key(f"score.{s['Name']}.name")
            s['DisplayName'] = replace_component(s['DisplayName'], cfg_dupe["scores_name"] | cfg_dupe["scores_all"])
        for t in scores.tag['data']['Teams']:
            set_key(f"score.{t['Name']}.name")
            t['DisplayName'] = replace_component(t['DisplayName'],
                                                 cfg_dupe["scores_teams_name"] | cfg_dupe["scores_all"])
            set_key(f"score.{t['Name']}.prefix")
            t['MemberNamePrefix'] = replace_component(t['MemberNamePrefix'],
                                                      cfg_dupe["scores_teams_prefix"] | cfg_dupe["scores_all"])
            set_key(f"score.{t['Name']}.suffix")
            t['MemberNameSuffix'] = replace_component(t['MemberNameSuffix'],
                                                      cfg_dupe["scores_teams_suffix"] | cfg_dupe["scores_all"])
        scores.save_to(path)
    except Exception as e:
        LOGGER.error("无法访问计分板数据：/No scoreboard data could be accessed: ", e)


def scan_level(path):
    try:
        level = n.load(path)
        for b in level.tag['Data']['CustomBossEvents']:
            set_key(f"bossbar.{b}.name")
            level.tag['Data']['CustomBossEvents'][b]['Name'] = replace_component(
                level.tag['Data']['CustomBossEvents'][b]['Name'], cfg_dupe["bossbar"])
        level.save_to(path)
    except Exception as e:
        LOGGER.error("无法访问Bossbar数据：/No bossbar data could be accessed: ", e)


def scan_structure(path):
    try:
        structure = n.load(path)
        for b in structure.tag['blocks']:
            try:
                handle_block_entity_nbt(b['nbt'])
            except KeyError:
                pass
        for e in structure.tag['entities']:
            try:
                handle_entity(e['nbt'], None)
            except KeyError:
                pass
        structure.save_to(path)
    except Exception as e:
        LOGGER.error("无法打开结构文件/Couldn't open structure file '" + path + "':", e)


def scan_file(path, start):
    if path.endswith(".nbt"):
        scan_structure(path)
        return
    if not path.endswith(".mcfunction") and not path.endswith(".json"):
        return
    try:
        k = path[start:]
        k = k[k.find("\\data\\") + 6:]
        k = k.replace("\\", ".")
        k = k[:-11] if k.endswith(".mcfunction") else k[:-5]
        set_key(k)
        with open(path, 'r', encoding="utf-8") as f:
            lines = f.readlines()
            for i in range(len(lines)):
                if lines[i].startswith('#'):  # comment
                    continue
                is_macro = False
                if lines[i].startswith('$'):  # marco command
                    is_macro = True
                txt = sub_replace(REG_COMPONENT, lines[i], match_text, cfg_dupe["datapacks"], is_marco=is_macro)
                txt = sub_replace(REG_COMPONENT_ESCAPED, txt, match_text_escaped, cfg_dupe["datapacks"],
                                  is_marco=is_macro)
                # txt = sub_replace(REG_COMPONENT_PLAIN, txt, match_text, cfg_dupe["datapacks"], False)
                txt = sub_replace(REG_DATAPACK_CONTENTS, txt, match_contents, cfg_dupe["datapacks"])
                txt = sub_replace(REG_BOSSBAR_SET_NAME, txt, match_bossbar, cfg_dupe["datapacks"], is_marco=is_macro)
                lines[i] = sub_replace(REG_BOSSBAR_ADD, txt, match_bossbar2, cfg_dupe["datapacks"], is_marco=is_macro)
        with open(path, 'w', encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        LOGGER.error("无法替换数据包文件/Couldn't replace datapack file '" + path + "':", e)


def scan_datapacks(path):
    for root, _, files in os.walk(path):
        for f in files:
            scan_file(os.path.join(root, f), len(path) + 1)


# main
def gen_lang(path):
    obj = json.dumps(rel_lang, indent=cfg_lang["indent"], ensure_ascii=cfg_lang["ensure_ascii"],
                     sort_keys=cfg_lang["sort_keys"])
    with open(path, 'w', encoding="utf-8") as f:
        f.write(obj)


def backup_saves(path, source):
    if not os.path.exists(path):
        os.makedirs(path)
    if os.path.exists(source):
        shutil.rmtree(path)

    shutil.copytree(source, path)


def init_logger():
    LOGGER.handlers.clear()
    LOGGER.addHandler(file_handler)


def main():
    init_logger()

    print("+===========[Chinese]===========+")
    print("{0}\t{1:<20}\t{2:^1}".format("|", "存档翻译提取器(魔改) 1.7", "|"))
    print("{0}\t{1:<20}\t{2:^9}".format("|", "原作者Suso", "|"))
    print("{0}\t{1:<20}\t{2:^9}".format("|", "魔改作者FengMing3093", "|"))
    print("{0}\t{1:<20}\t{2:^9}".format("|", "使用Amulet核心", "|"))
    print("+===============================+")

    try:
        with open("config.json", "r", encoding="utf-8") as file_cfg:
            global cfg_settings, cfg_lang, cfg_dupe, cfg_default
            config = json.loads(file_cfg.read())
            cfg_settings = config["settings"]
            cfg_lang = cfg_settings["lang"]
            cfg_dupe = cfg_settings["keep_duplicate_keys"]
            cfg_default = cfg_settings["default_keys"]
    except Exception as e:
        LOGGER.error("在打开config.json时发生一个错误: /An error occurred while opening the file config.json: ", e)
        exit(1)

    if len(sys.argv) < 2:
        LOGGER.error(f"用法: python {sys.argv[0]} <存档>/Usage: python {sys.argv[0]} <world>")
        exit(0)

    if cfg_settings["backup"]:
        LOGGER.info(f"备份中: /Backup: {os.path.abspath('.')}\\backup")
        backup_saves(os.path.abspath('./backup/'), sys.argv[1])

    for k in cfg_default:
        rev_lang[k] = cfg_default[k]
        rel_lang[cfg_default[k]] = k
    # rev_lang[""] = "empty"
    # rel_lang["empty"] = ""

    LOGGER.info("\n扫描区块.../Scanning chunks...")
    try:
        level = amulet.load_level(sys.argv[1])
        if level.level_wrapper.version < 2826:
            global OLD_SPAWNER_FORMAT
            OLD_SPAWNER_FORMAT = True
            LOGGER.info("使用旧版刷怪笼格式/Using old spawner format.")
        scan_world(level)
    except Exception as e:
        LOGGER.error("加载存档时出错: /Error loading world: ", e)
        exit(1)

    LOGGER.info("\n扫描杂项NBT/Scanning misc NBT...")
    scan_scores(sys.argv[1] + "/data/scoreboard.dat")
    scan_level(sys.argv[1] + "/level.dat")

    LOGGER.info("\n扫描数据包文件/Scanning datapack files...")
    scan_datapacks(sys.argv[1] + "/datapacks")
    scan_datapacks(sys.argv[1] + "/generated")

    LOGGER.info("\n生成语言文件/Generating default lang file...")
    gen_lang('default_lang.json')

    LOGGER.info("完工！/Done!")


if __name__ == '__main__':
    # reload(sys)
    # sys.setdefaultencoding('utf8')
    main()
