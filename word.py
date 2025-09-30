import requests


API_KEY = "sk-ivzhfeuskbuoejhmcppuazjfhjzbwbjvcyowgpesojxelkpf"
url = "https://api.siliconflow.cn/v1/chat/completions"
def get_words(text: str) -> list[str]:
    prompt = f"请作为日语词汇专家，从文本中提取所有【N2及以上】难度的词汇原型，直接用空格分隔输出，不要包含其他任何文本，如果没有则返回空字符串。文本：{text}"
    payload = {
        "model": "Qwen/QwQ-32B",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    words = response.json()['choices'][0]['message']['content'].split(' ')
    words = [word.strip() for word in words if word]
    return words


# https://github.com/RabbearSu/Japanese-Words