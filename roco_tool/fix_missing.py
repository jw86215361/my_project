import requests
import json
import os
import re
import time

BASE_URL = "https://roco.gptvip.chat"
API_MEMBERS = f"{BASE_URL}/api/egg-group-members"
DATA_DIR = "e:/my_project/roco_tool/data"
GROUPS_FILE = os.path.join(DATA_DIR, "roco_groups.json")
PETS_FILE = os.path.join(DATA_DIR, "roco_all_pets.json")
AVATARS_DIR = os.path.join(DATA_DIR, "images", "avatars")
FULL_BODY_DIR = os.path.join(DATA_DIR, "images", "full_body")

def safe_filename(name):
    return re.sub(r'[\\/:*?"<>|]', '_', name)

def parse_chain_names(chain_str):
    if not chain_str:
        return []
    names = []
    branches = chain_str.replace("\uff0c", ",").split(",")
    for branch in branches:
        parts = branch.strip().split("\u2192")
        for part in parts:
            part = part.strip()
            name = re.sub(r'[\uff08(].*?[\uff09)]', '', part).strip()
            if name and name not in names:
                names.append(name)
    return names

# 加载现有数据
groups = json.load(open(GROUPS_FILE, "r", encoding="utf-8"))
pets = json.load(open(PETS_FILE, "r", encoding="utf-8"))
pet_names_set = set(p["name"] for p in pets)

# 找出空的组
empty_groups = [g for g in groups if len(g["families"]) == 0]
print(f"需要补抓的组: {[g['group_name'] + '(ID=' + str(g['group_id']) + ')' for g in empty_groups]}")

for g in empty_groups:
    gid = g["group_id"]
    gname = g["group_name"]
    print(f"\n--- 补抓【{gname}】(ID={gid}, 应有{g['member_count']}成员) ---")

    for attempt in range(3):
        print(f"  尝试第{attempt+1}次...")
        page = 1
        seen_keys = set()
        families = []
        pet_names_list = []
        new_pets = []

        success = True
        while True:
            try:
                r = requests.get(API_MEMBERS, params={"group_id": gid, "page": page, "page_size": 50}, timeout=60)
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                print(f"  第{page}页失败: {e}")
                success = False
                break

            cards = data.get("cards", [])
            total_pages = data.get("total_pages", 1)
            if not cards:
                break

            new_cards = False
            for card in cards:
                fk = card.get("family_key", "")
                if fk in seen_keys:
                    continue
                seen_keys.add(fk)
                new_cards = True

                rep = card.get("representative", {})
                chain = card.get("family_chain", "")
                chain_names = parse_chain_names(chain)
                rep_name = rep.get("display_name", "")

                families.append({
                    "family_chain": chain,
                    "representative": rep_name,
                    "member_count": card.get("member_count", 1),
                    "chain_members": chain_names
                })
                for cn in chain_names:
                    if cn not in pet_names_list:
                        pet_names_list.append(cn)

                if rep_name and rep_name not in pet_names_set:
                    avatar_url = rep.get("avatar_url", "")
                    body_url = rep.get("body_url", "")
                    new_pets.append({
                        "name": rep_name,
                        "base_id": rep.get("base_id"),
                        "type": rep.get("type_name", ""),
                        "class": rep.get("class_name", ""),
                        "family_chain": chain,
                        "family_member_count": card.get("member_count", 1),
                        "hatch_status": rep.get("hatch_status_text", ""),
                        "egg_group": gname,
                        "egg_group_id": gid,
                        "avatar_url": avatar_url,
                        "body_url": body_url,
                        "local_avatar": f"images/avatars/{safe_filename(rep_name)}.png",
                        "local_body": f"images/full_body/{safe_filename(rep_name)}.png",
                        "chain_members": chain_names
                    })
                    # 下载图片
                    for url, dir in [(avatar_url, AVATARS_DIR), (body_url, FULL_BODY_DIR)]:
                        if url:
                            path = os.path.join(dir, f"{safe_filename(rep_name)}.png")
                            if not os.path.exists(path):
                                try:
                                    img = requests.get(url, timeout=20)
                                    if img.status_code == 200:
                                        with open(path, "wb") as f:
                                            f.write(img.content)
                                except:
                                    pass

            if not new_cards or page >= total_pages:
                break
            page += 1

        if success and len(families) > 0:
            g["families"] = families
            g["pet_names"] = pet_names_list
            pets.extend(new_pets)
            for p in new_pets:
                pet_names_set.add(p["name"])
            print(f"  成功! {len(families)}个家族, {len(pet_names_list)}个精灵, 新增{len(new_pets)}个代表")
            break
        else:
            print(f"  失败，等5秒重试...")
            time.sleep(5)

# 保存
with open(GROUPS_FILE, "w", encoding="utf-8") as f:
    json.dump(groups, f, ensure_ascii=False, indent=2)
with open(PETS_FILE, "w", encoding="utf-8") as f:
    json.dump(pets, f, ensure_ascii=False, indent=2)

print("\n=== 最终统计 ===")
for g in groups:
    print(f"  {g['group_name']}: {len(g['families'])}个家族, {len(g['pet_names'])}个精灵")
total_families = sum(len(g["families"]) for g in groups)
total_pets_chain = sum(len(g["pet_names"]) for g in groups)
print(f"\n  总计: {total_families}个家族, {total_pets_chain}个链上精灵, {len(pets)}个代表精灵")
