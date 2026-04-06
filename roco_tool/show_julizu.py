import json

data = json.load(open("e:/my_project/roco_tool/data/roco_groups.json", "r", encoding="utf-8"))
for g in data:
    if g["group_id"] == 2:
        print(f"蛋组: {g['group_name']} (总成员={g['member_count']}, 家族数={len(g['families'])})")
        print(f"描述: {g['description']}")
        print()
        for i, f in enumerate(g["families"], 1):
            print(f"家族{i}: 【{f['representative']}】 ({f['member_count']}只)")
            print(f"  进化链: {f['family_chain']}")
            print(f"  成员: {f['chain_members']}")
            print()
        break
