import requests
import json

# 看看巨灵组原始 API 返回的完整结构
r = requests.get("https://roco.gptvip.chat/api/egg-group-members",
                  params={"group_id": 2, "page": 1, "page_size": 10}, timeout=30)
data = r.json()

# 打印所有顶层 key
print("=== 顶层 Keys ===")
for k, v in data.items():
    if isinstance(v, list):
        print(f"  {k}: list, len={len(v)}")
    else:
        print(f"  {k}: {v}")

# 看看 cards 里第一个条目的完整结构
if data.get("cards"):
    print("\n=== 第一个 card 的完整结构 ===")
    print(json.dumps(data["cards"][0], ensure_ascii=False, indent=2))

# 关键：看看是否有 total_count 或 members 字段
print("\n=== 原始完整返回(最外层) ===")
for k in data:
    if k != "cards":
        print(f"  {k} = {data[k]}")
