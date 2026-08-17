import sys
import json
sys.path.append('')
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
# from FZXFunction import *
from CleanText import LLMDataCleaner
cleaner = LLMDataCleaner()
new_json=[]

def load_json_jsonl(file_path):
    data = []
    if file_path.endswith("jsonl"):
        print("文件是JSONL格式")
        return load_jsonl(file_path)
    else:
        print("文件是JSON格式")
        return load_json(file_path)

def load_jsonl(file_path):
    data = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            data.append(json.loads(line.strip()))  # 解析每行JSON对象
    return data

def load_json(file_path):
   if os.path.exists(file_path):
         with open(file_path, 'r', encoding='utf-8') as f:
             json_data=json.load(f)
   else:
        save_json(file_path,[])
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump([], f)  # 写入空列表
        json_data=json.load(f)
   return json_data
def save_json(file_path,json_data):
   os.makedirs(os.path.dirname(file_path), exist_ok=True)
   with open(file_path, 'w', encoding='utf-8') as f:
       json.dump(json_data, f, indent=4, ensure_ascii=False)


# 读取数据
folder_path="data1/"
folder_path=os.path.join(current_dir,folder_path)
for root, dirs, files in os.walk(folder_path):
    for file in files:
        if file.endswith('.jsonl'):#读取json文件
            file_path = os.path.join(root, file)
            # print(file)
            json_data=load_json_jsonl(file_path)
            for item in json_data:
                new_json.append([
                    {
                        "role": "user",
                        "content": cleaner.clean_text(item["question"])
                    },
                    {
                        "role": "assistant",
                        "content": cleaner.clean_text(item["answer"])
                    }
                ])
    break
save_json(os.path.join(current_dir,"data2/sftdata.json"),new_json)

        


