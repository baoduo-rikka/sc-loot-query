# 🚀 星际公民 · 掉落查询

[![GitHub](https://img.shields.io/badge/GitHub-sc--loot--query-blue?logo=github)](https://github.com/baoduo-rikka/sc-loot-query)

基于游戏解包数据的 Star Citizen 物品掉落查询工具，一键启动 Web 可视化界面。

## ⚠️ 免责声明

本工具**仅用于数据研究目的**，不保证数据的实时性、准确性或与游戏实际体验的一致性。

- **数据版本**：当前基于游戏版本 **4.10** 的静态解包文件（Foundry Records）。后续游戏更新可能导致数据失效，请以游戏内实际情况为准。
- **概率计算**：所有掉落概率均依据游戏文件结构推导，**并非官方公布数据**，可能与游戏内部实际随机逻辑存在偏差。

## 📖 简介

你是否在游戏中打到一件装备却不知道它从哪来的？或者想刷某件装备却不清楚哪个区域概率最高？

**星际公民掉落查询** 直接从游戏数据文件（Foundry Records）中提取完整的掉落配置，提供直观的 Web 查询界面，让你快速查找任意物品的掉落来源、概率和容器信息。

**数据版本**: 4.10

## ✨ 功能特性

### 🔍 掉落查询
- 按 **UUID** 或 **物品英文名** 精确/模糊搜索
- 显示物品标签、可掉落状态、阵营/事件徽章
- 列出所有涉及的区域和容器

### 📊 概率分析
- **单件概率**：同池物品数修正（prob ÷ poolSize）
- **概率范围**：同一物品在不同容器中的概率跨度
- **单箱概率**：单个容器至少出 1 件的概率
- **堆叠数量**：自动提取游戏中的堆叠配置（如 `📦2-4个`）
- **V3 固定掉落**：武器架/弹药箱等 V3 容器的直接放置概率

### 🏷️ 容器详情
- 展开查看每个容器下的全部掉落物品
- 模态框浏览容器内所有物品清单
- 标签组维度组织，清晰展示权重分配

### 🗺️ 区域概览
- **12+ 掉落区域**：通用、小行星基地、争夺区、配送中心、Hathor 轨道激光等
- **V3 槽位**：武器架、弹药箱、护甲箱、医疗箱、食物箱、采集箱自动识别
- **阵营/事件徽章**：标识物品的阵营和事件关联（仅信息展示，不限制区域）

## 🏗️ 项目结构

```
星际公民掉落查询/
├── loot_query.py       # 🎯 主程序（内嵌数据库 + Web 服务器 + 前端界面）
├── loot_db.json        # 📦 数据库缓存（自动生成，可删除后 --rebuild）
├── README.md           # 📖 本文件
├── LICENSE             # ⚖️ MIT 许可证
└── .gitignore          # 🙈 Git 忽略规则
```

## 🧠 三层掉落模型

工具基于游戏文件的真实结构，建立三层查找链：

```
区域（Region）
  └─ 摆了哪些容器（Container）
       └─ 每个容器引用哪些 Archetype
            └─ Archetype 组匹配哪些物品（通过标签）
```

### 第一层：区域 → 容器

每个区域配置了一组容器。一个区可以有多种容器叠加：

| 区域 | 容器举例 |
|------|---------|
| generic | 中/大型武器箱、护甲箱、医疗箱... |
| orbageddon | 中/大型武器箱 + C·通用001（平台专属） |
| stormbreaker | 中/大型武器箱（与 generic 完全相同） |

**同类型容器在哪个区概率都一样。**区域只是"摆了哪些容器"的集合。

### 第二层：容器 → Archetype

每个容器引用一个掉落表，掉落表引用若干 Archetype（物品分组），每个 Archetype 定义一组必匹配标签。

```
LootTable_Container_Weapons_Medium_Common
  └─ Archetype: Container_Medium_WeaponAttachments
       └─ 要求: Common + Weapon → FPS → Attachment
```

**容器只管"装不装这类东西"，不管事件/阵营。**

### 第三层：Archetype → 物品

物品的标签与 Archetype 要求的标签做交集匹配。满足即为候选，按权重抽选。

```
物品: arma_barrel_comp_s3_03
标签: Common, S3, Barrel, Event→StormBreaker, ...

Archetype 要求: Common + S3 + Barrel  ← 匹配！
（Event→StormBreaker 在传统容器中不参与匹配，不作为排除条件）
```

### V3 容器的额外过滤

传统容器（`lootgeneration_slotpreset_*.json`）的 `poolFilter` 均为 `null`，无任何过滤。

只有 **V3 容器**（`v3slotpreset_*.json`，NPC 尸体、武器架、货架等）才挂载 `poolFilter`：

```
v3poolfilter_generic:
  ├─ nofactions      → 排除 AI → Faction 标签物品
  └─ nospecialevents → 排除 Event 标签物品
```

**阵营/事件标签只在 V3 容器这一层才生效**，传统箱子不受影响。

### 概率公式

```
单件概率 = 表权重占比 × Archetype 组权重占比 ÷ 同池物品数
```

- **组概率**：选中这个 Archetype 标签组的概率
- **单件概率**：组概率 ÷ 池中物品数（这才是这件物品的实际概率）
- **单箱概率**：1 − (1 − 单件概率)^N（容器多次 roll 后至少出 1 件的概率）

## 🔄 4.10 更新

- 切换至 **4.10PTU** 数据（24,229 件物品，220 张掉落表）
- 概率修正：组概率 → 单件概率（除以同池物品数）
- 移除过度严格的 Event 区域过滤（Event 标签仅信息展示）
- 阵营检测：⚔️ 阵营物品徽章
- 数据库增加 `chance` / `fullness` / `limit` 字段

### 新增物品 UUID

| 类别 | 物品 | UUID |
|------|------|------|
| 🔫 步枪 | HDGW Arlington | `cc95ae76` |
| 🔫 步枪 | Arlington 变体 ×3 | `47403176` `54885d55` `7a90fcaf` |
| 🔫 手枪 | HDGW SalvoFrag | `3b6d199f` |
| 🔫 手枪 | SalvoFrag 雕刻 ×2 | `7c15996f` `31c196fd` |
| 🔫 弹匣 | Arlington / SalvoFrag | `94b9bfce` `aa9edf82` |
| 🔭 瞄准镜 | HDGW TSCO x4 S2 | `9a1d74cd` |
| 🛡️ 超重甲 | CDS Combat SuperHeavy ×15 | (详见 commit) |
| 🛡️ 阵营 | QRT NineTails ×5 / KAP ×1 | (详见 commit) |

## 📄 许可证

[MIT License](LICENSE)
