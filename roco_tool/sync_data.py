import requests
import json
import os
import threading
from queue import Queue
from urllib.parse import urljoin

# 配置信息
BASE_URL = "https://roco.gptvip.chat"
API_GROUPS = f"{BASE_URL}/api/egg-groups"
API_MEMBERS = f"{BASE_URL}/api/egg-group-members"
DATA_DIR = "e:/my_project/roco_tool/data"
IMAGES_DIR = os.path.join(DATA_DIR, "images")
AVATARS_DIR = os.path.join(IMAGES_DIR, "avatars")
FULL_BODY_DIR = os.path.join(IMAGES_DIR, "full_body")
JSON_OUTPUT = os.path.join(DATA_DIR, "roco_all_pets.json")

# 确保文件夹存在
os.makedirs(AVATARS_DIR, exist_ok=True)
os.makedirs(FULL_BODY_DIR, exist_ok=True)

# 用于存储所有精灵数据，去重用
all_pets = {}
download_queue = Queue()

def fetch_data():
    print("正在获取蛋组列表...")
    try:
        groups_resp = requests.get(API_GROUPS, timeout=30)
        groups_resp.raise_for_status()
        groups = groups_resp.json().get("groups", [])
        print(f"共发现 {len(groups)} 个蛋组")
    except Exception as e:
        print(f"获取蛋组列表失败: {e}")
        return

    for group in groups:
        group_id = group["group_id"]
        group_name = group["group_display"]
        print(f"正在抓取【{group_name}】的数据...")
        
        page = 1
        while True:
            try:
                params = {"group_id": group_id, "page": page, "page_size": 100}
                members_resp = requests.get(API_MEMBERS, params=params, timeout=30)
                members_resp.raise_for_status()
                data = members_resp.json()
                cards = data.get("cards", [])
                
                if not cards:
                    break
                
                for card in cards:
                    pet = card.get("representative", {})
                    name = pet.get("display_name")
                    if not name: continue
                    
                    # 使用精灵名称作为唯一标识（如果API提供ID更好，但这里以名称区分）
                    if name not in all_pets:
                        avatar_url = pet.get("avatar_url")
                        body_url = pet.get("body_url")
                        
                        # 补全 URL
                        if avatar_url and avatar_url.startswith("/"): avatar_url = urljoin(BASE_URL, avatar_url)
                        if body_url and body_url.startswith("/"): body_url = urljoin(BASE_URL, body_url)
                        
                        pet_data = {
                            "name": name,
                            "type": pet.get("type_name"),
                            "family_chain": card.get("family_chain"),
                            "hatch_status": pet.get("hatch_status_text"),
                            "avatar_url": avatar_url,
                            "body_url": body_url,
                            "local_avatar": f"images/avatars/{name}.png",
                            "local_body": f"images/full_body/{name}.png"
                        }
                        all_pets[name] = pet_data
                        
                        # 加入下载队列
                        if avatar_url:
                            download_queue.put((avatar_url, os.path.join(AVATARS_DIR, f"{name}.png")))
                        if body_url:
                            download_queue.put((body_url, os.path.join(FULL_BODY_DIR, f"{name}.png")))
                
                page += 1
                # 如果总页数已知，可以提前结束
                if page > data.get("total_pages", 1):
                    break
                    
            except Exception as e:
                print(f"抓取组 {group_name} 第 {page} 页失败: {e}")
                break

def download_worker():
    while not download_queue.empty():
        url, save_path = download_queue.get()
        if os.path.exists(save_path):
            download_queue.task_done()
            continue
            
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                # print(f"已下载: {os.path.basename(save_path)}")
            else:
                print(f"下载失败 {url}: {resp.status_code}")
        except Exception as e:
            print(f"下载异常 {url}: {e}")
        finally:
            download_queue.task_done()

def main():
    fetch_data()
    print(f"数据抓取完成，共 {len(all_pets)} 个独立精灵。")
    print(f"待下载图片总数: {download_queue.qsize()}")
    
    # 启动多线程下载
    threads = []
    num_threads = 10
    for _ in range(num_threads):
        t = threading.Thread(target=download_worker)
        t.start()
        threads.append(t)
    
    for t in threads:
        t.join()
        
    # 保存 JSON
    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(list(all_pets.values()), f, ensure_ascii=False, indent=4)
        
    print(f"全部完成！数据已保存至 {JSON_OUTPUT}")
    print(f"图片存储在 {IMAGES_DIR}")

if __name__ == "__main__":
    main()
