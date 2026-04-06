import requests
import json
import os
import threading
import re
from queue import Queue
from urllib.parse import urljoin

# 配置
BASE_URL = "https://roco.gptvip.chat"
API_GROUPS = f"{BASE_URL}/api/egg-groups"
API_MEMBERS = f"{BASE_URL}/api/egg-group-members"
DATA_DIR = "e:/my_project/roco_tool/data"
IMAGES_DIR = os.path.join(DATA_DIR, "images")
AVATARS_DIR = os.path.join(IMAGES_DIR, "avatars")
FULL_BODY_DIR = os.path.join(IMAGES_DIR, "full_body")
JSON_OUTPUT = os.path.join(DATA_DIR, "roco_all_pets.json")
GROUPS_OUTPUT = os.path.join(DATA_DIR, "roco_groups.json")

os.makedirs(AVATARS_DIR, exist_ok=True)
os.makedirs(FULL_BODY_DIR, exist_ok=True)

all_pets = {}       # name -> pet_data (去重)
all_groups = {}     # group_id -> group_info
download_queue = Queue()

def safe_filename(name):
    """移除文件名不安全字符"""
    return re.sub(r'[\\/:*?"<>|]', '_', name)

def fetch_all_data():
    """获取所有蛋组及其完整成员"""
    print("[1] 正在获取蛋组列表...")
    try:
        resp = requests.get(API_GROUPS, timeout=30)
        resp.raise_for_status()
        groups = resp.json().get("groups", [])
    except Exception as e:
        print(f"获取蛋组列表失败: {e}")
        return

    print(f"    共 {len(groups)} 个蛋组")
    for g in groups:
        gid = g["group_id"]
        gname = g["group_display"]
        member_count = g.get("member_count", 0)
        folded_count = g.get("folded_count", 0)
        total_display = member_count  # 包含折叠的总成员数
        all_groups[gid] = {
            "group_id": gid,
            "group_name": gname,
            "description": g.get("description", ""),
            "member_count": member_count,
            "folded_count": folded_count,
            "families": [],
            "pet_names": []
        }
        print(f"    {gname}(ID={gid}): 成员={member_count}, 折叠={folded_count}")

    print(f"\n[2] 正在逐组抓取成员详情...")
    for g in groups:
        gid = g["group_id"]
        gname = g["group_display"]
        print(f"\n  --- 抓取【{gname}】---")

        page = 1
        seen_family_keys = set()
        group_pet_count = 0

        while True:
            try:
                params = {"group_id": gid, "page": page, "page_size": 50}
                resp = requests.get(API_MEMBERS, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                print(f"    第{page}页请求失败: {e}")
                break

            cards = data.get("cards", [])
            total_pages = data.get("total_pages", 1)

            if not cards:
                break

            # 防止死循环：检查是否有新数据
            new_cards = False
            for card in cards:
                family_key = card.get("family_key", "")
                if family_key in seen_family_keys:
                    continue
                seen_family_keys.add(family_key)
                new_cards = True

                rep = card.get("representative", {})
                family_chain = card.get("family_chain", "")
                family_member_count = card.get("member_count", 1)

                # 解析进化链中的所有精灵名称
                chain_names = parse_chain_names(family_chain)

                # 记录代表精灵（有头像和全身图的）
                rep_name = rep.get("display_name", "")
                if rep_name and rep_name not in all_pets:
                    avatar_url = rep.get("avatar_url", "")
                    body_url = rep.get("body_url", "")

                    pet_data = {
                        "name": rep_name,
                        "base_id": rep.get("base_id"),
                        "type": rep.get("type_name", ""),
                        "class": rep.get("class_name", ""),
                        "family_chain": family_chain,
                        "family_member_count": family_member_count,
                        "hatch_status": rep.get("hatch_status_text", ""),
                        "egg_group": gname,
                        "egg_group_id": gid,
                        "avatar_url": avatar_url,
                        "body_url": body_url,
                        "local_avatar": f"images/avatars/{safe_filename(rep_name)}.png",
                        "local_body": f"images/full_body/{safe_filename(rep_name)}.png",
                        "chain_members": chain_names
                    }
                    all_pets[rep_name] = pet_data
                    group_pet_count += 1

                    # 加入下载队列
                    if avatar_url:
                        download_queue.put((avatar_url, os.path.join(AVATARS_DIR, f"{safe_filename(rep_name)}.png")))
                    if body_url:
                        download_queue.put((body_url, os.path.join(FULL_BODY_DIR, f"{safe_filename(rep_name)}.png")))

                # 记录当前组的家族和精灵名
                all_groups[gid]["families"].append({
                    "family_chain": family_chain,
                    "representative": rep_name,
                    "member_count": family_member_count,
                    "chain_members": chain_names
                })
                for cn in chain_names:
                    if cn not in all_groups[gid]["pet_names"]:
                        all_groups[gid]["pet_names"].append(cn)

            if not new_cards:
                break

            if page >= total_pages:
                break

            page += 1

        print(f"    {gname}: 抓取了 {len(seen_family_keys)} 个家族, {group_pet_count} 个代表精灵, 链上成员 {len(all_groups[gid]['pet_names'])} 个")


def parse_chain_names(chain_str):
    """从进化链字符串中提取所有精灵名称"""
    if not chain_str:
        return []
    # 进化链格式: "乌达（极昼的样子） → 迷你乌（极昼的样子） → 乌拉塔（极昼的样子）"
    # 或 "书魔虫 → 书卷守护 → 古卷执政官, 古卷匣魔像"
    names = []
    # 先按逗号分割（处理分支进化）
    branches = chain_str.replace("，", ",").split(",")
    for branch in branches:
        # 再按箭头分割
        parts = branch.strip().split("→")
        for part in parts:
            part = part.strip()
            # 去掉括号中的描述（如 "极昼的样子"）
            name = re.sub(r'[（(].*?[）)]', '', part).strip()
            if name and name not in names:
                names.append(name)
    return names


def download_worker():
    while not download_queue.empty():
        try:
            url, save_path = download_queue.get(timeout=1)
        except:
            break

        if os.path.exists(save_path):
            download_queue.task_done()
            continue

        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200 and len(resp.content) > 100:
                with open(save_path, "wb") as f:
                    f.write(resp.content)
            else:
                print(f"    下载失败: {os.path.basename(save_path)} ({resp.status_code})")
        except Exception as e:
            print(f"    下载异常: {os.path.basename(save_path)} ({e})")
        finally:
            download_queue.task_done()


def main():
    fetch_all_data()

    print(f"\n[3] 数据汇总:")
    print(f"    蛋组数量: {len(all_groups)}")
    print(f"    代表精灵(去重): {len(all_pets)}")
    total_chain = sum(len(g["pet_names"]) for g in all_groups.values())
    print(f"    链上精灵总数(含进化前): {total_chain}")
    print(f"    待下载图片: {download_queue.qsize()}")

    # 多线程下载
    print(f"\n[4] 开始下载图片 ({download_queue.qsize()} 张)...")
    threads = []
    for _ in range(8):
        t = threading.Thread(target=download_worker)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

    # 保存精灵JSON
    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(list(all_pets.values()), f, ensure_ascii=False, indent=2)
    print(f"\n[5] 精灵数据已保存至 {JSON_OUTPUT}")

    # 保存蛋组JSON（含完整成员列表）
    with open(GROUPS_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(list(all_groups.values()), f, ensure_ascii=False, indent=2)
    print(f"    蛋组数据已保存至 {GROUPS_OUTPUT}")

    # 打印各组统计
    print(f"\n[6] 各蛋组统计:")
    for gid, ginfo in all_groups.items():
        print(f"    {ginfo['group_name']}: {len(ginfo['families'])}个家族, {len(ginfo['pet_names'])}个精灵(含进化)")

    # 统计下载结果
    avatar_count = len([f for f in os.listdir(AVATARS_DIR) if f.endswith('.png')])
    body_count = len([f for f in os.listdir(FULL_BODY_DIR) if f.endswith('.png')])
    print(f"\n[7] 图片统计:")
    print(f"    头像: {avatar_count} 张")
    print(f"    全身图: {body_count} 张")
    print(f"\n全部完成!")


if __name__ == "__main__":
    main()
