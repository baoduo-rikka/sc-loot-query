# 🚀 星际公民 · 掉落查询

[![GitHub](https://img.shields.io/badge/GitHub-sc--loot--query-blue?logo=github)](https://github.com/baoduo-rikka/sc-loot-query)

基于游戏解包数据的 Star Citizen 物品掉落查询工具，一键启动 Web 可视化界面。

## 📖 简介

你是否在游戏中打到一件装备却不知道它从哪来的？或者想刷某件装备却不清楚哪个区域掉落概率最高？

**星际公民掉落查询** 直接从游戏数据文件（Foundry Records）中提取完整的掉落配置，提供直观的 Web 查询界面，让你快速查找任意物品的掉落来源、概率和容器信息。

**数据版本**: 4.9正式1 (12302499) · 覆盖 **24230 件物品**、**263 个掉落 archetype**

## ✨ 功能特性

### 🔍 掉落查询
- 按 **UUID** 或 **物品英文名** 精确/模糊搜索
- 显示物品标签、可掉落状态
- 列出所有涉及的区域和容器

### 📊 概率分析
- **完整概率公式**: 表权重 × Archetype 组权重 × 槽权重 × 生成率
- **概率范围**: 同一物品在不同容器中的概率跨度（如 `2.6%~40.7%`）
- **单箱概率**: 计算单个容器至少出 1 件的概率
- **单件概率**: 同事件多件物品时的单品选中率
- **V3 固定掉落**: 武器架/弹药箱等 V3 容器的直接放置概率

### 📦 堆叠数量
- 自动提取游戏中的堆叠配置（如 `📦2-4个`）
- 覆盖 61 个 archetype，1719 件 Stackable 物品

### 🏷️ 容器详情
- 展开查看每个容器下的全部掉落物品
- 支持模态框浏览容器内所有物品清单
- 标签组维度组织，清晰展示权重分配

### 🗺️ 区域概览
- **12+ 掉落区域**: 通用、小行星基地、争夺区、配送中心、Hathor 轨道激光等
- **V3 槽位**: 武器架、弹药箱、护甲箱、医疗箱、食物箱、采集箱自动识别
- **事件区域过滤**: 只显示当前物品可掉落的活动区域

### ⚡ 性能优化
- 数据库内嵌在 Python 源码中（base85+gzip 压缩），单文件即开即用
- 名称映射异步加载（`/names.json`），页面秒开
- 轻量级 HTTP 服务器，零外部依赖

## 🚀 快速开始

### 方式一：直接运行（推荐）

```bash
python loot_query.py
```

然后打开浏览器访问 http://127.0.0.1:8080

### 方式二：打包成 EXE

```bash
pip install pyinstaller
pyinstaller --onefile --name "星际公民掉落查询" loot_query.py
```

打包后在 `dist/星际公民掉落查询.exe`，可脱离 Python 环境运行。

## 📋 命令参数

| 参数 | 说明 |
|------|------|
| `--rebuild` | 重新从原文件解包数据库（需要游戏数据目录） |

```bash
python loot_query.py --rebuild   # 重新构建数据库缓存
python loot_query.py             # 使用已有缓存启动
```

## 🔧 系统要求

- **Python 3.8+**（零外部依赖，仅使用标准库）
- 内存：~200MB（含数据库加载）
- 磁盘：`loot_query.py` 约 11MB（含内嵌数据库）

若使用 `--rebuild` 需要完整的游戏 Foundry Records 目录。

## 🏗️ 项目结构

```
星际公民掉落查询/
├── loot_query.py       # 🎯 主程序（内嵌数据库 + Web 服务器 + 前端界面）
├── loot_db.json        # 📦 数据库缓存（自动生成，可删除后 --rebuild）
├── README.md           # 📖 本文件
├── LICENSE             # ⚖️ MIT 许可证
└── .gitignore          # 🙈 Git 忽略规则
```

## 🧠 技术实现

### 数据来源
直接从 Star Citizen 游戏文件的 `libs/foundry/records/` 目录解析：
- `lootgeneration/loottables/` — 掉落表配置
- `lootgeneration/lootarchetypes/` — 掉落 Archetype（物品分组+权重+堆叠）
- `tagdatabase/` — 标签层级树
- `harvestable/slotpresets/` — V3 槽位预设（武器架、洞穴容器等）
- `entities/` — 物品实体定义

### 概率模型
```
单次 roll 选中概率 = 表权重占比 × Archetype 组权重占比 × 槽权重 × 生成率
```

- **表权重占比**: 当前容器在对应掉落表中的权重 / 表总权重
- **Archetype 组权重占比**: 标签组在 Archetype 中的权重 / Archetype 总权重
- **槽权重**: 容器槽位的相对概率（通常为 1.0）
- **生成率**: 槽位的生成概率（V3 容器特有，如 50% 概率生成）

### 前端技术
- 纯 JavaScript（无框架，约 31KB 压缩内联）
- 异步名称映射加载
- 动态标签匹配 + 容器合并算法
- 响应式 CSS 暗色主题

## 📸 截图

| 查询结果页 | 容器详情 |
|:---:|:---:|
| 搜索 MedPen 显示区域概览、概率范围、堆叠数量 | 点击容器查看完整物品清单 |

## ⚠️ 免责声明

- 本工具**仅用于数据研究目的**
- 数据来源于 Star Citizen 游戏客户端解包文件
- 与 Cloud Imperium Games 无关
- 请遵守 Cloud Imperium Games 的 EULA 和相关政策

## 📄 许可证

[MIT License](LICENSE)
