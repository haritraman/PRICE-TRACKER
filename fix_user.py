import json

with open("users.json", "r") as f:
    users = json.load(f)

for user in users:
    if "chat_id" not in users[user]:
        users[user]["chat_id"] = ""

with open("users.json", "w") as f:
    json.dump(users, f, indent=4)

print("Missing chat_id fields added successfully!")
