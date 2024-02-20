## 存档翻译提取器 (WTEM) 1.3
World Translation Extractor Modified

Forked by [WorldTranslationExtractor](https://github.com/5uso/AmuletScripts/blob/main/WorldTranslationExtractor.py)

### 信息
该版本修改了部分内容。
依赖 `amulet-map-editor` 以及 `tqdm`.

安装: `pip install amulet-map-editor`, `pip install tqdm`

### 更改

1. 允许保留重复项。
2. 允许备份世界。
3. 支持 1.19+ 的告示牌、雕纹书架、饰纹陶罐(1.19+)、命令方块、蜂窝以及蜂巢。
4. 将输出转为标准的JSON语言文件。
5. 加入配置文件。
6. 支持展示实体。

## 原Readme

下划线加粗字体说明改内容是新增的。

这里是原版的 `README.md`:

扫描整个存档，搜索Json文本中的`"text"`组件，并替换为`"translate"`组件，生成一个与资源包一起使用的lang文件。在`1.16.5`和`1.19.3`上进行了测试。

会在以下搜索Json文本:
- 方块
  - 刷怪笼: SpawnData (下一个生成的实体), SpawnPotentials (要生成实体的列表)
  - 容器: items (物品), 容器名称 (`"chest"`, `"furnace"`, `"shulker_box"`, `"barrel"`, `"smoker"`, `"blast_furnace"`, `"trapped_chest"`, `"hopper"`, `"dispenser"`, `"dropper"`, `"brewing_stand"`, `"campfire"`, <u>**`"chiseled_bookshelf"`**</u>, <u>**`"decorated_pot"`**</u>)
  - 告示牌: text1-4 (一至四行文本), <u>**front_text, back_text (正反面文本)**</u>
  - 讲台: Book (成书)
  - 唱片机: RecordItem (唱片)
  - <u>**蜂窝与蜂巢: Bees (蜜蜂)**
  - **命令方块: Command (命令)**</u>

- 实体
  - Name (名称)
  - Items (背包)
  - ArmorItems (盔甲)
  - HandItems (手持物品)
  - Inventory (物品栏)
  - Villager offers (村民交易)
  - Passengers (乘骑实体)
  - <u>**Text Display (文本展示实体)**</u>
  - <u>**Item Display (物品展示实体)**</u>

- 物品
  - Name (名称)
  - Lore
  - Book pages (书页)
  - Book title (书本标题): 以防没有，会添加customname
  - BlockEntityTag (方块实体标签)
  - EntityTag (实体标签)

- 记分板: objective names (记分项名称), team names and affixes (队伍名称以及前后缀)

- Boss栏: names (名称)

- 数据包: functions (函数), json files (Json文件)

- 结构: blocks (方块), entities (实体)

用法: `python WorldTranslationExtractor.py <world>` (会修改存档，在工作目录下输出 `default_lang.json` )
