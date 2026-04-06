import requests
import json

# 1. 获取蛋组列表
groups = requests.get("https://roco.gptvip.chat/api/egg-groups", timeout=30).json().get("groups", [])
print("=== 所有蛋组 ===")
for g in groups:
    gid = g["group_id"]
    name = g["group_display"]
    count = g.get("member_count", "?")
    print(f"  ID={gid}  {name}  成员数={count}")

# 2. 查巨灵组详细（逐页）
print("\n=== 巨灵组(ID=2) 逐页成员 ===")
all_names = []
for page in range(1, 20):
    r = requests.get("https://roco.gptvip.chat/api/egg-group-members",
                      params={"group_id": 2, "page": page, "page_size": 10}, timeout=30)
    data = r.json()
    cards = data.get("cards", [])
    if not cards:
        break
    for c in cards:
        rep = c.get("representative", {})
        name = rep.get("display_name", "?")
        all_names.append(name)
    total_pages = data.get("total_pages", "?")
    print(f"  第{page}页: {[c.get('representative',{}).get('display_name','?') for c in cards]}  (共{total_pages}页)")

print(f"\n巨灵组 API 总成员: {len(all_names)}")

# 3. 对比我们已抓的JSON
local = json.load(open("e:/my_project/roco_tool/data/roco_all_pets.json", "r", encoding="utf-8"))
local_names = set(p["name"] for p in local)
api_names = set(all_names)

missing = api_names - local_names
extra = local_names - api_names

print(f"\n本地JSON总精灵数: {len(local)}")
print(f"巨灵组API成员在本地缺失: {missing if missing else '无'}")
print(f"本地有但巨灵组API没有: 不关心(可能属于其他组)")
