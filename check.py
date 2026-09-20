import json
import os

file_path = r'C:\Users\saide\.gemini\antigravity\brain\09093916-3698-4ada-b690-870fbf4adca1\.user_uploaded\media_1788116656046.txt'
if os.path.exists(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        print("Type:", data.get("type"))
        features = data.get("features", [])
        print("Features count:", len(features))
        if features:
            print("First feature properties:", features[0].get("properties"))
else:
    print("File not found.")
