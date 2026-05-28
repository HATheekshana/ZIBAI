import os
import json
import urllib.request

# 1. Path to your artifacts folder
TARGET_DIR = r"C:\Users\ASUS\Desktop\PRPJECTS\Card Generate\Testing\artifacts"

# 2. Grab the live mappings directly from the data-mining repo
print("Fetching latest artifact hash maps...")
url = "https://raw.githubusercontent.com/the-genshin-db/genshin-db/main/src/data/excels/relics.json"

try:
    with urllib.request.urlopen(url) as response:
        raw_data = json.loads(response.read().decode())
except Exception as e:
    print(f"Failed to fetch data: {e}")
    exit()

# 3. Build a clean dictionary connecting ID strings to English Names
# Example: "15001" -> "Gladiators_Finale"
id_to_name = {}
for entry in raw_data:
    # Internal game ID (e.g., 15001)
    id_str = str(entry.get("id", ""))
    # English name cleanly formatted (no spaces)
    name_str = entry.get("name", "").replace(" ", "_").replace("'", "")
    
    if id_str and name_str:
        id_to_name[id_str] = name_str

# 4. Scan your directory and rename files automatically
print("\nProcessing files...")
success_count = 0

if os.path.exists(TARGET_DIR):
    for filename in os.listdir(TARGET_DIR):
        # We only care about files starting with UI_RelicIcon
        if filename.startswith("UI_RelicIcon_") and filename.endswith(".png"):
            # Extract the ID out of "UI_RelicIcon_15002_4.png" -> "15002"
            parts = filename.split("_")
            if len(parts) >= 3:
                artifact_id = parts[2]
                
                # If we have this ID mapped to a real name
                if artifact_id in id_to_name:
                    new_name = f"{id_to_name[artifact_id]}.png"
                    
                    old_path = os.path.join(TARGET_DIR, filename)
                    new_path = os.path.join(TARGET_DIR, new_name)
                    
                    try:
                        os.rename(old_path, new_path)
                        print(f"Renamed: {filename} -> {new_name}")
                        success_count += 1
                    except Exception as error:
                        print(f"Skipped {filename}: {error}")
                        
    print(f"\nSuccess! Total renamed files: {success_count}")
else:
    print(f"Error: Directory path not found: {TARGET_DIR}")