import json
import os
import re
import shutil
import sys

import amulet
import amulet_nbt as n
from tqdm import tqdm

# Config

cfg_lang = dict()
cfg_settings = dict()
cfg_dupe = dict()

# REG

OLD_SPAWNER_FORMAT = False  # If this is false, uses 1.18+ nbt paths for spawners

REG_COMPONENT = re.compile(r'"text" *: *"((?:[^"\\]|\\\\"|\\.)*)"')
REG_COMPONENT_PLAIN = re.compile(r'"((?:[^"\\]|\\\\"|\\.)*)"')
REG_COMPONENT_ESCAPED = re.compile(r'\\"text\\" *: *\\"((?:[^"\\]|\\\\.)*)\\"')
REG_DATAPACK_CONTENTS = re.compile(r'"contents":"((?:[^"\\]|\\\\"|\\.)*)"')
REG_BOSSBAR_SET_NAME = re.compile(r'bossbar set ([^ ]+) name "(.*)"')
REG_BOSSBAR_ADD = re.compile(r'bossbar add ([^ ]+) "(.*)"')
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
def sub_replace(pattern: re.Pattern, string: str, repl, dupe=False, search_all=True):
    match = pattern.search(string) if search_all else pattern.match(string)
    if match is None:
        return string
    span = match.span()
    ls = list(string)
    ls[span[0]:span[1]] = repl(match, dupe=dupe)
    return ''.join(ls)


def get_plain_from_match(match, escaped=False, ord=1):
    plain = match if isinstance(match, str) else match.group(ord)
    if escaped:
        plain = re.sub(pattern=r'\\\\', string=plain, repl=r'\\')
    plain = re.sub(pattern=r'\\\\([^\\])', string=plain, repl=r'\\\1')
    plain = re.sub(pattern=r"\\'", string=plain, repl=r"'")
    return plain


def match_text(match, escaped=False, dupe=False):
    plain = get_plain_from_match(match, escaped)
    rk = get_key()
    if plain not in rev_lang:
        rev_lang[plain] = rk
    if plain == '':
        return f'\\"translate\\":\\"empty\\"' if escaped else f'"translate":"empty"'
    rel_lang[rk] = plain
    print(f'[text] put key: {rk}: {rel_lang[rk]}')
    if dupe:
        return f'\\"translate\\":\\"{rev_lang[plain]}\\"' if escaped else f'"translate":"{rev_lang[plain]}"'
    return f'\\"translate\\":\\"{rk}\\"' if escaped else f'"translate":"{rk}"'


def match_plain_text(match, dupe=False):
    plain = match.string[1:-1]
    rk = get_key()
    if plain not in rev_lang:
        rev_lang[plain] = rk
    if plain == '':
        return f'{{"translate":"empty"}}'
    rel_lang[rk] = plain
    print(f'[plain] put key: {rk}: {rel_lang[rk]}')
    if dupe:
        return f'{{"translate":"{rev_lang[plain]}"}}'
    return f'{{"translate":"{rk}"}}'


def match_contents(match, dupe=False):
    plain = get_plain_from_match(match)
    rk = get_key()
    if plain not in rev_lang:
        rev_lang[plain] = rk
    if plain == '':
        return f'"contents":{{"translate":"empty"}}'
    rel_lang[rk] = plain
    print(f'[contents] put key: {rk}: {rel_lang[rk]}')
    if dupe:
        return f'"contents":{{"translate":"{rev_lang[plain]}"}}'
    return f'"contents":{{"translate":"{rk}"}}'


def match_bossbar(match, dupe=False):
    plain = get_plain_from_match(match, ord=2)
    name = match.group(1)
    rk = get_key()
    if plain not in rev_lang:
        rev_lang[plain] = rk
    if plain == '':
        return f'bossbar set {name} name {{"translate":"empty"}}'
    rel_lang[rk] = plain
    print(f'[bossbar1] put key: {rk}: {rel_lang[rk]}')
    if dupe:
        return f'bossbar set {name} name {{"translate":"{rev_lang[plain]}"}}'
    return f'bossbar set {name} name {{"translate":"{rk}"}}'


def match_bossbar2(match, dupe=False):
    plain = get_plain_from_match(match, ord=2)
    name = match.group(1)
    rk = get_key()
    if plain not in rev_lang:
        rev_lang[plain] = rk
    if plain == '':
        return f'bossbar add {name} {{"translate":"empty"}}'
    rel_lang[rk] = plain
    print(f'[bossbar2] put key: {rk}: {rel_lang[rk]}')
    if dupe:
        return f'bossbar add {name} {{"translate":"{rev_lang[plain]}"}}'
    return f'bossbar add {name} {{"translate":"{rk}"}}'


def match_text_escaped(match, dupe=False):
    return match_text(match, True, dupe)


def replace_component(text, dupe=False):
    text = sub_replace(REG_COMPONENT_PLAIN, str(text), match_plain_text, dupe, False)
    text = sub_replace(REG_COMPONENT, str(text), match_text, dupe)
    return n.TAG_String(sub_replace(REG_COMPONENT_ESCAPED, text, match_text_escaped, dupe))


# handler
def handle_item(item):
    changed = False
    if len(item) == 0:
        return False
    id = str(item['id'])[10:]
    item_counts.setdefault(id, 1)
    translation_cnt = len(rel_lang)

    try:
        set_key(f"item.{id}.{item_counts[id]}.name")
        item['tag']['display']['Name'] = replace_component(item['tag']['display']['Name'], cfg_dupe["items_name"] | cfg_dupe["items_all"])
        changed = True
    except KeyError:
        pass

    try:
        for line in range(len(item['tag']['display']['Lore'])):
            set_key(f"item.{id}.{item_counts[id]}.lore.{line}")
            item['tag']['display']['Lore'][line] = replace_component(item['tag']['display']['Lore'][line], cfg_dupe["items_lore"] | cfg_dupe["items_all"])
        changed = True
    except KeyError:
        pass

    try:
        for page in range(len(item['tag']['pages'])):
            set_key(f"item.{id}.{item_counts[id]}.page.{page}")
            item['tag']['pages'][page] = replace_component(item['tag']['pages'][page], cfg_dupe["items_pages"] | cfg_dupe["items_all"])
        changed = True
    except KeyError:
        pass

    try:
        title = item['tag']['title']
        if "display" not in item['tag']:
            item['tag']['display'] = n.TAG_Compound()
        if "Name" not in item['tag']['display']:
            rk = f"item.{id}.{item_counts[id]}.title.1"
            rel_lang[rk] = title
            print(f'[json] put key: {rk}: {rel_lang[rk]}')
            if title not in rev_lang:
                rev_lang[title] = rk
            if cfg_dupe["items_title"] or cfg_dupe["items_all"]:
                item['tag']['display']['Name'] = n.TAG_String(f'{{"translate":"{rev_lang[title]}","italic":false}}')
            else:
                item['tag']['display']['Name'] = n.TAG_String(f'{{"translate":"{rk}","italic":false}}')
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
        changed |= handle_item(item)

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

    # Display entity
    if "text" in entity:
        set_key(f"entity.{id}.{entity_counts[id]}.text")
        entity['text'] = replace_component(entity['text'], cfg_dupe["show_entity_text"])
        changed = True

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
    return handle_block_entity_base(block_entity, str(block_entity['id'])[10:])  # after "minecraft:"


def handle_block_entity(block_entity):
    return handle_block_entity_base(block_entity.nbt.tag['utags'], block_entity.base_name)


def handle_chunk(chunk):
    for block_entity in chunk.block_entities:
        chunk.changed |= handle_block_entity(block_entity)


def handle_entities(level, coords, dimension, entities):
    changed = False
    for e in entities:
        changed |= handle_entity(e.nbt.tag, e.base_name)
    if changed:
        level.set_native_entites(coords[0], coords[1], dimension, entities)


# scanner
def scan_world(level):
    for dimension in level.dimensions:
        chunk_coords = sorted(level.all_chunk_coords(dimension))
        if len(chunk_coords) < 1:
            continue
        print(f"维度/Dimension {dimension}: ")
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
                    print("\n保存中......")
                    level.save()
                    level.unload()
            level.save()
        except KeyboardInterrupt:
            print("中断！最后5000区块切片数据将不会保存！/Interrupted. Changes to last 5000 chunk slice won't be saved.")
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
            t['DisplayName'] = replace_component(t['DisplayName'], cfg_dupe["scores_teams_name"] | cfg_dupe["scores_all"])
            set_key(f"score.{t['Name']}.prefix")
            t['MemberNamePrefix'] = replace_component(t['MemberNamePrefix'], cfg_dupe["scores_teams_prefix"] | cfg_dupe["scores_all"])
            set_key(f"score.{t['Name']}.suffix")
            t['MemberNameSuffix'] = replace_component(t['MemberNameSuffix'], cfg_dupe["scores_teams_suffix"] | cfg_dupe["scores_all"])
        scores.save_to(path)
    except Exception as e:
        print("无法访问计分板数据：/No scoreboard data could be accessed: ", e)


def scan_level(path):
    try:
        level = n.load(path)
        for b in level.tag['Data']['CustomBossEvents']:
            set_key(f"bossbar.{b}.name")
            level.tag['Data']['CustomBossEvents'][b]['Name'] = replace_component(level.tag['Data']['CustomBossEvents'][b]['Name'], cfg_dupe["bossbar"])
        level.save_to(path)
    except Exception as e:
        print("无法访问Bossbar数据：/No bossbar data could be accessed: ", e)


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
        print("无法打开结构文件/Couldn't open structure file '" + path + "':", e)


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
            line = f.readlines()
            for i in range(len(line)):
                if line[i].startswith('#'):
                    continue
                txt = sub_replace(REG_COMPONENT, line[i], match_text, cfg_dupe["datapacks"])
                txt = sub_replace(REG_COMPONENT_ESCAPED, txt, match_text_escaped, cfg_dupe["datapacks"])
                txt = sub_replace(REG_DATAPACK_CONTENTS, txt, match_contents, cfg_dupe["datapacks"])
                txt = sub_replace(REG_BOSSBAR_SET_NAME, txt, match_bossbar, cfg_dupe["datapacks"])
                line[i] = sub_replace(REG_BOSSBAR_ADD, txt, match_bossbar2, cfg_dupe["datapacks"])
        with open(path, 'w', encoding="utf-8") as f:
            f.writelines(line)
    except Exception as e:
        print("无法替换数据包文件/Couldn't replace datapack file '" + path + "':", e)


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


def main():
    print('''
+==================================+
| [Chinese] 存档翻译提取器(魔改)   |
| 原作者Suso                       |
| 魔改作者FengMing3093             |
| 使用Amulet核心                   |
+==================================+
''')
    try:
        with open("config.json", "r", encoding="utf-8") as file_cfg:
            global cfg_settings, cfg_dupe, cfg_lang
            config = json.loads(file_cfg.read())
            cfg_settings = config["settings"]
            cfg_dupe = cfg_settings["keep_duplicate_keys"]
            cfg_lang = cfg_settings["lang"]
    except Exception as e:
        print("在打开config.json时发生一个错误: /An error occurred while opening the file config.json: ", e)

    if len(sys.argv) < 2:
        print(f"用法: python {sys.argv[0]} <存档>/Usage: python {sys.argv[0]} <world>")
        exit(0)

    if cfg_settings["backup"]:
        print(f"备份中: /Backup: {os.path.abspath('.')}\\backup")
        backup_saves(os.path.abspath('./backup/'), sys.argv[1])

    rev_lang[""] = "empty"
    rel_lang["empty"] = ""

    print("\n扫描区块.../Scanning chunks...")
    # try:
    level = amulet.load_level(sys.argv[1])
    if level.level_wrapper.version < 2826:
        global OLD_SPAWNER_FORMAT
        OLD_SPAWNER_FORMAT = True
        print("使用旧版刷怪笼格式/Using old spawner format.")
    scan_world(level)
    # except Exception as e:
    #     print("加载存档时出错: /Error loading world: ", e)
    #     exit(1)

    print("\n扫描杂项NBT/Scanning misc NBT...")
    scan_scores(sys.argv[1] + "/data/scoreboard.dat")
    scan_level(sys.argv[1] + "/level.dat")

    print("\n扫描数据包文件/Scanning datapack files...")
    scan_datapacks(sys.argv[1] + "/datapacks")
    scan_datapacks(sys.argv[1] + "/generated")

    print("\n生成语言文件/Generating default lang file...")
    gen_lang('default_lang.json')

    print("完工！/Done!")


if __name__ == '__main__':
    main()
