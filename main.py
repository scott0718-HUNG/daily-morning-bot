import os
# 1. 環境變數讀取
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

# ==========================================
# 2. 核心功能函數
# ==========================================

def get_quote_and_prompt():
    """使用 Gemini 產生繁體中文勵志語錄與英文生圖提示詞"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = """
    請幫我構思今天早上的勵志語錄。
    要求：
    1. 句子必須是非常經典、激勵人心、充滿正能量的「繁體中文」語錄。
    2. 必須提供出處與作者姓名。
    3. 根據這句語錄的意境，寫一段用於 AI 產生背景圖片的「英文提示詞 (Prompt)」。背景圖片必須是唯美、真實攝影風格的人物或風景圖。
    
    請務必嚴格以 JSON 格式回傳，格式如下：
    {
        "quote": "勵志語錄內容",
        "author": "《出處書名》- 作者姓名",
        "image_prompt": "english prompt for beautiful realistic landscape or person photography"
    }
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    
    result = response.json()
    text_content = result['candidates'][0]['content']['parts'][0]['text']
    
    return json.loads(text_content)

def generate_image(prompt_text):
    """使用 Gemini Imagen 4 模型產生圖片"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict?key={GEMINI_API_KEY}"
    
    # 強制加入高畫質真實攝影的提示詞前綴
    enhanced_prompt = f"Highly detailed, cinematic lighting, realistic photography, {prompt_text}"
    
    payload = {
        "instances": [{"prompt": enhanced_prompt}],
        "parameters": {"sampleCount": 1}
    }
