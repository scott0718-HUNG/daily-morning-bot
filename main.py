import os
import json
import base64
import datetime
import requests
import textwrap
import urllib.request
import urllib.parse # 新增：用於處理網址編碼
import time # 新增：用於處理 API 重試的等待時間
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# 1. 環境變數讀取
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

# ==========================================
# 2. 核心功能函數
# ==========================================

def get_quote():
    """使用 Gemini 產生繁體中文勵志語錄"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    # 簡化任務：只需要生成語錄，不再需要生圖提示詞
    prompt = """
    請幫我構思今天早上的勵志語錄。
    要求：
    1. 句子必須是非常經典、激勵人心、充滿正能量的「繁體中文」語錄。
    2. 必須提供出處與作者姓名。
    
    請務必嚴格以 JSON 格式回傳，格式如下：
    {
        "quote": "勵志語錄內容",
        "author": "《出處書名》- 作者姓名"
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

def get_daily_background():
    """獲取微軟 Bing 每日精選高品質風景圖作為背景"""
    print("正在獲取微軟 Bing 每日精選風景圖...")
    try:
        # 微軟 Bing 每日桌布 API (免 Key、極度穩定、每日更新)
        url = "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=zh-TW"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # 取得高畫質圖片網址
        image_url = "https://www.bing.com" + data['images'][0]['url']
        
        # 下載圖片
        img_response = requests.get(image_url, timeout=15)
        img_response.raise_for_status()
        
        return base64.b64encode(img_response.content).decode('utf-8')
        
    except Exception as e:
        print(f"⚠️ Bing 圖片獲取失敗 ({e})，啟用 Picsum 隨機圖備用方案...")
        # 備用方案：Lorem Picsum 隨機高品質相片 (加入時間亂數確保每次不同)
        random_seed = int(time.time())
        backup_url = f"https://picsum.photos/seed/{random_seed}/1080/1080"
        img_response = requests.get(backup_url, timeout=15)
        img_response.raise_for_status()
        return base64.b64encode(img_response.content).decode('utf-8')

def get_font(size):
    """動態下載 Google Noto Sans TC 開源字型以支援繁體中文"""
    font_path = "NotoSansTC-Bold.ttf"
    if not os.path.exists(font_path):
        print("正在下載中文字型...")
        url = "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Bold.otf"
        urllib.request.urlretrieve(url, font_path)
    return ImageFont.truetype(font_path, size)

def process_image(base64_img, quote, author):
    """使用 Pillow 在圖片上壓印日期、語錄與作者"""
    # 將 base64 轉換為圖片物件
    image_data = base64.b64decode(base64_img)
    img = Image.open(BytesIO(image_data)).convert("RGBA")
    
    # 建立一個與原圖大小相同的黑色半透明遮罩，讓白色文字更清晰
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 80)) # 80 是透明度
    img = Image.alpha_composite(img, overlay).convert("RGB")
    
    draw = ImageDraw.Draw(img)
    width, height = img.size
    
    # 載入字型
    font_date = get_font(int(height * 0.05))
    font_quote = get_font(int(height * 0.12))
    font_author = get_font(int(height * 0.05))
    
    # 1. 繪製左上角日期
    today_str = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y年%m月%d日")
    padding = int(width * 0.05)
    
    # 文字陰影處理函數 (讓字在各種背景都清楚)
    def draw_text_with_shadow(xy, text, font, text_color="white", shadow_color="black"):
        x, y = xy
        # 繪製黑色描邊/陰影
        offset = 2
        draw.text((x-offset, y-offset), text, font=font, fill=shadow_color)
        draw.text((x+offset, y-offset), text, font=font, fill=shadow_color)
        draw.text((x-offset, y+offset), text, font=font, fill=shadow_color)
        draw.text((x+offset, y+offset), text, font=font, fill=shadow_color)
        # 繪製主文字
        draw.text((x, y), text, font=font, fill=text_color)

    draw_text_with_shadow((padding, padding), today_str, font_date)
    
    # 2. 處理語錄自動換行
    # 計算每行大約可以容納幾個中文字
    avg_char_width = font_quote.getbbox("繁")[2]
    max_chars_per_line = int((width - padding * 2) / avg_char_width)
    wrapped_quote = textwrap.fill(quote, width=max_chars_per_line)
    
    # 3. 繪製語錄 (置中於圖片中下方)
    # 計算文字總高度
    bbox = draw.textbbox((0, 0), wrapped_quote, font=font_quote)
    text_height = bbox[3] - bbox[1]
    
    quote_y = height * 0.50 # 放在圖片 65% 高度的位置
    
    # 逐行繪製置中文字
    lines = wrapped_quote.split('\n')
    current_y = quote_y
    for line in lines:
        line_bbox = draw.textbbox((0, 0), line, font=font_quote)
        line_width = line_bbox[2] - line_bbox[0]
        line_x = (width - line_width) / 2
        draw_text_with_shadow((line_x, current_y), line, font_quote)
        current_y += (line_bbox[3] - line_bbox[1]) + 10 # 行距
        
    # 4. 繪製作者與出處 (語錄下方)
    author_bbox = draw.textbbox((0, 0), author, font=font_author)
    author_width = author_bbox[2] - author_bbox[0]
    author_x = (width - author_width) / 2
    author_y = current_y + 20
    draw_text_with_shadow((author_x, author_y), author, font_author, text_color="#f0f0f0")
    
    # 轉換回 byte array 準備上傳
    output_buffer = BytesIO()
    img.save(output_buffer, format="JPEG", quality=90)
    return base64.b64encode(output_buffer.getvalue()).decode('utf-8')

def upload_to_imgbb(base64_img_str):
    """上傳圖片至 ImgBB 並取得公開連結"""
    url = "https://api.imgbb.com/1/upload"
    payload = {
        "key": IMGBB_API_KEY,
        "image": base64_img_str,
        "name": "morning_motivation" # 新增：確保圖片有檔名，降低 LINE 阻擋機率
    }
    response = requests.post(url, data=payload)
    response.raise_for_status()
    return response.json()['data']['url']

def send_line_message(image_url, quote, author):
    """透過 LINE Messaging API 傳送早安圖與純文字"""
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    # 修改：同時傳送「純文字」與「圖片」，作為雙重保險與除錯機制
    payload = {
        "to": LINE_USER_ID,
        "messages": [
            {
                "type": "text",
                "text": f"🌞 早安！\n\n{quote}\n\n— {author}"
            },
            {
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": image_url
            }
        ]
    }
    response = requests.post(url, headers=headers, json=payload)
    
    # 新增：詳細印出 LINE API 回應，捕捉靜默錯誤
    if response.status_code != 200:
        print(f"\n❌ LINE 推播失敗！API 錯誤詳細回應：\n{response.text}\n")
        
    response.raise_for_status()
    print("LINE 訊息推播成功！")

# ==========================================
# 3. 主程式流程
# ==========================================
def main():
    try:
        print("1. 正在生成語錄...")
        data = get_quote() # 修改：使用簡化後的新函式
        print(f"取得語錄：{data['quote']}")
        
        print("2. 正在獲取每日背景圖片...")
        base64_raw_img = get_daily_background() # 修改：直接抓取微軟絕美桌布
        
        print("3. 正在合成圖片與文字...")
        base64_final_img = process_image(base64_raw_img, data['quote'], data['author'])
        
        print("4. 正在上傳圖片至 ImgBB...")
        img_url = upload_to_imgbb(base64_final_img)
        print(f"圖片上傳成功：{img_url}")
        
        print("5. 正在發送 LINE 訊息...")
        send_line_message(img_url, data['quote'], data['author'])
        
        print("✅ 每日早安圖任務執行完成！")
        
    except Exception as e:
        print(f"❌ 發生錯誤：{str(e)}")
        # 在 GitHub Actions 中標記失敗狀態
        exit(1)

if __name__ == "__main__":
    main()
