import requests
from typing import Optional, Dict, Any, List
import os
import json


def get_temp_dir():
    return os.path.join(os.path.dirname(__file__), 'temp')


class Note:
    def __init__(self, word: str, sentence: str, sentence_audio: str, sentence_text: str, screen_shot: str) -> None:
        self.word = word
        self.sentence = sentence
        self.sentence_audio = sentence_audio
        self.sentence_text = sentence_text
        self.screen_shot = screen_shot

    def to_fields_dict(self) -> Dict[str, Dict[str, str]]:
        return {
            "Word": {"value": self.word},
            "Sentence": {"value": self.sentence},
            "SentenceAudio": {"value": self.sentence_audio},
            "SentenceText": {"value": self.sentence_text},
            "ScreenShot": {"value": self.screen_shot},
        }

ANKI_CONNECT_URL = 'http://127.0.0.1:8765'
def anki_connect_invoke(action: str, **params) -> Any:
    request_data = {
        "action": action,
        "version": 5,
        "params": params
    }
    
    try:
        response = requests.post(
            ANKI_CONNECT_URL, 
            data=json.dumps(request_data)
        ).json()
        
        print(f"✅ AnkiConnect 调用成功: {action}")
        print(f"响应内容: {response}")
        
        if response.get('error'):
            raise Exception(f"AnkiConnect API Error for '{action}': {response['error']}")
            
        return response['result']
        
    except requests.exceptions.ConnectionError:
        print(f"❌ 错误：无法连接到 AnkiConnect ({ANKI_CONNECT_URL})。请确保 Anki 桌面版正在运行且插件已安装。")
        raise
    except Exception as e:
        print(f"❌ AnkiConnect 调用失败: {e}")
        raise


def exists_note(deck: str, note: Note) -> Optional[int]:
    unique_field = 'Word' 
    field_value = note.word    
    query = f'deck:"{deck}" {unique_field}:"{field_value}"'
    
    try:
        note_ids: List[int] = anki_connect_invoke(
            action='findNotes',
            query=query
        )
        
        if note_ids:
            print(f"✅ 找到重复笔记，ID: {note_ids[0]}")
            return note_ids[0]
        else:
            return None
            
    except Exception:
        print("查询现有笔记失败。")
        return None

def store_media(file_path: str) -> Optional[str]:
    file_name = os.path.basename(file_path)
    try:
        exsits = anki_connect_invoke(action='retrieveMediaFile', filename=file_name)
        if exsits:
            print(f"⏩ 媒体文件 '{file_name}' 可能已存在于 Anki 媒体库中，跳过上传。")
            return file_name
    except Exception as e:
        pass 

    try:
        with open(file_path, 'rb') as f:
            import base64
            media_data_base64 = base64.b64encode(f.read()).decode('utf-8')

        media_id: Optional[str] = anki_connect_invoke(
            action='storeMediaFile',
            filename=file_name,
            data=media_data_base64 
        )
        
        if not media_id:
            print(f"❌ 存储媒体文件失败 (AnkiConnect Error): {media_id}")
            return None
        else:       
            print(f"✅ 成功存储媒体文件: {file_name}")
            return file_name
    except FileNotFoundError:
        print(f"❌ 存储媒体文件失败：本地文件不存在于路径 '{file_path}'。")
        return None
    except Exception as e:
        print(f"❌ 存储媒体文件失败：发生未知错误: {e}")
        return None

def add_note(deck: str, model: str, note: 'Note', tags: List[str]) -> Optional[int]:
    existing_id = exists_note(deck, note)
    if existing_id is not None:
        print(f"⏩ 跳过添加：笔记已存在 (ID: {existing_id})。")
        return existing_id

    try:
        note_fields = note.to_fields_dict() 
        media_ids = {}

        for field_name, field_value in note_fields.items():            
            if field_name.endswith('Audio'):
                media_ids[field_name] = field_value
                new_field_value = f"[sound:{field_value}]"
            elif field_name.endswith('ScreenShot'):
                media_ids[field_name] = field_value
                new_field_value = f"<img src='{field_value}'>" # HTML img 标签是更常用的图像引用方式
            field_value['value'] = new_field_value #type: ignore

        new_note_id: Optional[int] = anki_connect_invoke(
            action='addNote',
            note={
                "deckName": deck,
                "modelName": model,
                "fields": {k: v.get('value') if isinstance(v, dict) else v for k, v in note_fields.items()},
                "options": {
                    "allowDuplicate": False
                },
                "tags": tags
            }
        )
                
        if new_note_id is not None:
            print(f"🚀 成功添加笔记，ID: {new_note_id}")
            return new_note_id
        else:
            print("❌ 添加笔记返回了 None，可能是 AnkiConnect 内部问题。")
            return None
            
    except Exception as e:
        print(f"❌ 添加笔记失败：发生错误: {e}")
        return None
