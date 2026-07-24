#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
星际公民 模拟开箱工具 v1.0
================================
基于 loot_query.py 的数据库，模拟打开容器掉落物品。

使用: python simulate_open.py
      然后访问 http://127.0.0.1:8081

依赖: loot_db.json（由 loot_query.py 生成）
"""

import json
import os
import random
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote, parse_qs
from collections import defaultdict

# 加载数据库
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "loot_db.json")
with open(DB_PATH, "r", encoding="utf-8") as f:
    DB = json.load(f)

# 构建辅助索引: tag → [item_uuid, ...]
tag_to_items = defaultdict(list)
for uid, it in DB.get("items", {}).items():
    for t in it.get("t", []):
        tag_to_items[t].append(uid)

# 物品名称简化
def item_name(full):
    cn = full.replace("EntityClassDefinition.", "")
    return cn.replace("_", " ").replace("  ", " ").strip()

# 区域中文名
REGION_NAMES = {
    "generic": "通用(各处)", "asddelving": "ASD", "contestedzones": "争夺区",
    "asteroidbases": "小行星基地", "orbageddon": "Hathor轨道激光",
    "stormbreaker": "法罗数据中心+拉撒路研究所", "kaboos": "QV碎岩站",
    "dcdelving": "配送中心", "battaglia": "巴塔利亚",
    "distributioncentres_highsecurtiy": "配送中心·高安",
    "distributioncentres_lowsecurity": "配送中心·低安",
    "distributioncentres_mediumsecurity": "配送中心·中安",
    "loot_generic": "Loot Generic", "loot_military": "Loot Military",
    "rockcracker": "QV岩碎站", "rockcracker_sandbox": "QV碎岩站（独家）",
    "soo": "SoO", "tsg": "TSG", "welcometonyx": "QV空间站",
    "cave_hurston_poor": "洞穴·赫斯顿贫瘠", "cave_hurston_medium": "洞穴·赫斯顿中等",
    "cave_hurston_rich": "洞穴·赫斯顿富饶", "cave_daymar_poor": "洞穴·戴玛贫瘠",
    "cave_daymar_medium": "洞穴·戴玛中等", "cave_daymar_rich": "洞穴·戴玛富饶",
    "cave_aberdeen_poor": "洞穴·亚伯丁贫瘠", "cave_aberdeen_medium": "洞穴·亚伯丁中等",
    "cave_aberdeen_rich": "洞穴·亚伯丁富饶", "cave_prison": "洞穴·监狱",
    "cave_prisonescape": "洞穴·越狱", "cave_sand_medium": "沙洞·中等",
}

def region_name(r):
    if r in REGION_NAMES:
        return REGION_NAMES[r]
    for k, v in REGION_NAMES.items():
        if r.startswith(k):
            return v + "·" + r[len(k)+1:]
    return r.replace("_", " ").title()

def rname(r):
    return region_name(r)


# ──────────────────────────────────────────────
# 模拟开箱核心逻辑
# ──────────────────────────────────────────────

def weighted_choice(items, weights):
    """从 items 中按 weights 权重随机选一个"""
    total = sum(weights)
    if total <= 0:
        return None
    r = random.random() * total
    running = 0
    for item, w in zip(items, weights):
        running += w
        if r <= running:
            return item
    return items[-1]


def expand_tags(tags_list):
    """展开标签：将 'A → B → C' 拆分为 'A', 'A → B', 'A → B → C'"""
    result = set()
    for t in tags_list:
        parts = t.split(" → ")
        for i in range(1, len(parts) + 1):
            result.add(" → ".join(parts[:i]))
    return result


def match_items(tags_group):
    """找到匹配一组标签的所有物品 UUID"""
    result = None
    for tg in tags_group:
        items = tag_to_items.get(tg, [])
        if not items:
            return []
        if result is None:
            result = set(items)
        else:
            result &= set(items)
    return list(result) if result else []


def simulate_box(region_key):
    """模拟打开指定区域的一个箱子，返回掉落物品列表"""
    drops = []
    
    # 找到该区域的所有 slots
    slots = [s for s in DB.get("slots", []) if s["r"] == region_key]
    if not slots:
        return drops
    
    for slot in slots:
        for c in slot["c"]:
            if isinstance(c, str):
                continue
            
            cn = c["n"] if isinstance(c, dict) else c
            cw = c.get("w", 1.0) if isinstance(c, dict) else 1.0
            cchance = c.get("chance", 1.0) if isinstance(c, dict) else 1.0
            
            # Roll 容器激活
            if random.random() > cchance:
                continue
            
            # V3 物品：直接固定掉落
            if isinstance(cn, str) and cn.startswith("__v3__"):
                uid = cn.replace("__v3__", "")
                it = DB.get("items", {}).get(uid, {})
                if it:
                    drops.append({
                        "name": item_name(it.get("n", uid)),
                        "uid": uid,
                        "qty": 1,
                        "source": "V3固定",
                        "is_v3": True,
                    })
                continue
            
            # 非 V3：查找 loot table
            table = None
            for t in DB.get("tables", []):
                if t["n"] == cn:
                    table = t
                    break
            if not table:
                continue
            
            arch_names = table.get("a", [])
            arch_weights = table.get("aw", []) or [1.0] * len(arch_names)
            
            # Roll archetype
            selected_arch_name = weighted_choice(arch_names, arch_weights)
            if not selected_arch_name:
                continue
            
            # 查找 archetype
            arch = None
            for a in DB.get("arches", []):
                if a["n"] == selected_arch_name:
                    arch = a
                    break
            if not arch:
                continue
            
            # Roll 标签组
            groups = arch.get("g", [])
            gw = arch.get("gw", []) or [1.0] * len(groups)
            gs = arch.get("gs", []) or [None] * len(groups)
            
            selected_gi = None
            for gi in range(len(groups)):
                # Weighted choice
                pass
            
            # 按权重选组
            total_gw = sum(gw)
            r = random.random() * total_gw
            running = 0
            for gi in range(len(groups)):
                running += gw[gi] if gi < len(gw) else 1.0
                if r <= running:
                    selected_gi = gi
                    break
            
            if selected_gi is None:
                continue
            
            group_tags = groups[selected_gi]
            stack_info = gs[selected_gi] if selected_gi < len(gs) else None
            
            # 找匹配物品
            matched = match_items(group_tags)
            if not matched:
                continue
            
            # 随机选一个物品
            selected_uid = random.choice(matched)
            selected_item = DB.get("items", {}).get(selected_uid, {})
            
            # 堆叠数量
            qty = 1
            if stack_info:
                qty = random.randint(stack_info["min"], stack_info["max"])
            
            drops.append({
                "name": item_name(selected_item.get("n", selected_uid)),
                "uid": selected_uid,
                "qty": qty,
                "source": group_tags,
                "is_v3": False,
            })
    
    return drops


def simulate_batch(region_key, count):
    """模拟多次开箱，返回统计结果"""
    all_drops = []
    item_stats = defaultdict(lambda: {"count": 0, "total_qty": 0, "boxes": 0})
    
    for _ in range(count):
        drops = simulate_box(region_key)
        seen = set()
        for d in drops:
            uid = d["uid"]
            item_stats[uid]["count"] += 1
            item_stats[uid]["total_qty"] += d.get("qty", 1)
            item_stats[uid]["name"] = d["name"]
            if uid not in seen:
                item_stats[uid]["boxes"] += 1
                seen.add(uid)
        all_drops.append(drops)
    
    return {
        "total_boxes": count,
        "item_stats": dict(item_stats),
        "last_drops": all_drops[-1] if all_drops else [],
    }


# ──────────────────────────────────────────────
# Web 服务器
# ──────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>星际公民 · 模拟开箱</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0a0e1a;color:#c0d0e0;font-family:-apple-system,'Segoe UI',sans-serif;min-height:100vh}
.header{background:linear-gradient(135deg,#0f1a2e,#1a2744);padding:20px 30px;border-bottom:1px solid #2a3f6a}
.header h1{font-size:22px;color:#e0e8f0}
.header .sub{font-size:13px;color:#8899bb;margin-top:4px}
.container{max-width:1000px;margin:0 auto;padding:20px}
.controls{background:#0f1a2e;border:1px solid #1a2a4a;border-radius:12px;padding:20px;margin-bottom:20px;display:flex;flex-wrap:wrap;gap:12px;align-items:end}
.controls label{font-size:13px;color:#8899bb;display:block;margin-bottom:4px}
.controls select,.controls button,.controls input{background:#111b2e;border:1px solid #2a3f6a;color:#c0d0e0;padding:8px 14px;border-radius:8px;font-size:14px}
.controls select{min-width:250px}
.controls button{background:#1a3a6a;cursor:pointer;transition:all .2s}
.controls button:hover{background:#2a5a9a}
.controls button.primary{background:#2a6a3a;border-color:#3a8a5a}
.controls button.primary:hover{background:#3a8a5a}
.controls .btn-group{display:flex;gap:8px;flex-wrap:wrap}
.result-card{background:#0f1a2e;border:1px solid #1a2a4a;border-radius:12px;padding:20px;margin-bottom:16px}
.result-card h3{color:#8899bb;font-size:14px;margin-bottom:12px;font-weight:600}
.drop-item{display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:#0a1220;border:1px solid #152040;border-radius:8px;margin-bottom:6px}
.drop-item .name{font-size:14px;color:#e0e8f0}
.drop-item .qty{font-size:13px;color:#88aa99;font-weight:600}
.drop-item .tag{font-size:11px;color:#667;margin-left:8px}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:8px}
.stat-card{background:#0a1220;border:1px solid #152040;border-radius:8px;padding:12px}
.stat-card .s-name{font-size:13px;color:#c0d0e0}
.stat-card .s-val{font-size:20px;color:#88aa99;font-weight:600;margin-top:4px}
.stat-card .s-sub{font-size:11px;color:#667;margin-top:2px}
.no-drop{color:#667;font-size:14px;text-align:center;padding:30px}
.loading{text-align:center;padding:30px;color:#8899bb}
.v3-tag{background:#1a2744;color:#7eb8ff;font-size:10px;padding:2px 6px;border-radius:4px;margin-left:6px}
</style>
</head>
<body>
<div class="header"><h1>📦 星际公民 · 模拟开箱</h1><div class="sub">基于 loot_query 掉落数据库 · 随机模拟容器掉落</div></div>
<div class="container">
<div class="controls">
<div><label for="region">选择区域</label><select id="region"></select></div>
<div><label>操作</label><div class="btn-group">
<button class="primary" onclick="sim(1)">🎲 开 1 箱</button>
<button onclick="sim(10)">📦 开 10 箱</button>
<button onclick="sim(100)">📦 开 100 箱</button>
<button onclick="sim(1000)">📦 开 1000 箱</button>
</div></div>
</div>
<div id="result"><div class="no-drop">选择区域后点击"开箱"按钮开始模拟</div></div>
</div>
<script>
const REGION_NAMES={generic:"通用(各处)",asddelving:"ASD",contestedzones:"争夺区",asteroidbases:"小行星基地",orbageddon:"Hathor轨道激光",stormbreaker:"法罗数据中心+拉撒路研究所",kaboos:"QV碎岩站",dcdelving:"配送中心",battaglia:"巴塔利亚",distributioncentres_highsecurtiy:"配送中心·高安",distributioncentres_lowsecurity:"配送中心·低安",distributioncentres_mediumsecurity:"配送中心·中安",loot_generic:"Loot Generic",loot_military:"Loot Military",rockcracker:"QV岩碎站",soo:"SoO",tsg:"TSG",welcometonyx:"QV空间站"};
const REGIONS=[];

async function init(){const r=await fetch("/regions");const data=await r.json();const sel=document.getElementById("region");for(const ri of data){const opt=document.createElement("option");opt.value=ri;opt.textContent=REGION_NAMES[ri]||ri.replace(/_/g," ").replace(/\b\w/g,l=>l.toUpperCase());sel.appendChild(opt)}}
async function sim(n){const region=document.getElementById("region").value;if(!region)return;const res=document.getElementById("result");res.innerHTML='<div class="loading">⏳ 模拟中...</div>';try{const r=await fetch("/sim?region="+encodeURIComponent(region)+"&n="+n);const data=await r.json();render(data,n,region)}catch(e){res.innerHTML='<div class="no-drop">❌ 请求失败: '+e.message+'</div>'}}
function render(data,n,region){const res=document.getElementById("result");const rn=REGION_NAMES[region]||region;let h='<div class="result-card"><h3>📊 '+rn+' · 模拟 '+n+' 箱</h3>';
if(n===1){h+='<div style="margin-bottom:12px;color:#88aa99;font-size:13px">本次掉落</div>';const dr=data.last_drops;if(!dr||dr.length===0){h+='<div class="no-drop">😞 空箱，什么都没有</div>'}else{for(const d of dr){h+='<div class="drop-item"><span class="name">'+esc(d.name)+(d.is_v3?'<span class="v3-tag">V3</span>':'')+'</span><span class="qty">×'+d.qty+'</span></div>'}}}else{const stats=data.item_stats;const entries=Object.entries(stats).sort((a,b)=>b[1].count-a[1].count);h+='<div style="color:#667;font-size:12px;margin-bottom:10px">共 '+entries.length+' 种物品掉落</div><div class="stats-grid">';for(const[uid,s]of entries){const pct=((s.count/n)*100).toFixed(1);const avg=((s.total_qty||s.count)/n).toFixed(2);h+='<div class="stat-card"><div class="s-name">'+esc(s.name)+'</div><div class="s-val">'+pct+'%</div><div class="s-sub">出现 '+s.count+' 次 · 均 '+avg+' 个/箱</div></div>'}h+='</div>';if(data.last_drops&&data.last_drops.length>0){h+='<div style="margin-top:16px;color:#8899bb;font-size:13px;font-weight:600">最后一箱掉落</div>';for(const d of data.last_drops){h+='<div class="drop-item"><span class="name">'+esc(d.name)+(d.is_v3?'<span class="v3-tag">V3</span>':'')+'</span><span class="qty">×'+d.qty+'</span></div>'}}}h+='</div>';res.innerHTML=h}
function esc(s){const d=document.createElement("div");d.textContent=s;return d.innerHTML}
init();
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))
        
        elif path == "/regions":
            regions = sorted(set(s["r"] for s in DB.get("slots", [])), key=lambda r: (r != "generic", r))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(regions).encode("utf-8"))
        
        elif path == "/sim":
            region = params.get("region", [""])[0]
            n_str = params.get("n", ["1"])[0]
            try:
                n = int(n_str)
            except:
                n = 1
            
            if not region:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Missing region"}).encode("utf-8"))
                return
            
            result = simulate_batch(region, n)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # 安静运行


def main():
    port = 8081
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"📦 模拟开箱服务启动: http://127.0.0.1:{port}")
    webbrowser.open(f"http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == "__main__":
    main()
