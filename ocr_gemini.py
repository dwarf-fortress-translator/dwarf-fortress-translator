"""
OCR through Google Gemini API (OpenAI-compatible endpoint)
"""

import base64
import io
import logging
import cv2
from PIL import Image
import requests

log = logging.getLogger("ocr_translator")


class GeminiOCR:
    
    
    def __init__(self, api_keys=None, prompt=None):
        self.api_keys = api_keys or []
        self.current_key_index = 0
        self.prompt = prompt or self._default_prompt()
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    
    def _default_prompt(self):
        return 
    
    def set_prompt(self, prompt, target_lang="ru"):
        
        self.prompt = prompt
    
    def add_api_key(self, key):
        
        if key not in self.api_keys:
            self.api_keys.append(key)
            log.info(f"API key added. Total keys: {len(self.api_keys)}")
    
    def remove_api_key(self, key):
        
        if key in self.api_keys:
            self.api_keys.remove(key)
            log.info(f"API key removed. Total keys: {len(self.api_keys)}")
    
    def _get_next_key(self):
        
        if not self.api_keys:
            raise ValueError("No API keys available")
        key = self.api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return key
    
    def _compress_image(self, image_array, max_size_kb=100):
        
        if len(image_array.shape) == 3:
            rgb = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
        else:
            rgb = image_array
        
        pil_img = Image.fromarray(rgb)
        
        buffer = io.BytesIO()
        quality = 85
        
        while True:
            buffer.seek(0)
            buffer.truncate()
            pil_img.save(buffer, format='JPEG', quality=quality, optimize=True)
            size_kb = len(buffer.getvalue()) / 1024
            
            if size_kb <= max_size_kb or quality <= 30:
                break
            
            quality -= 10
        
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        log.debug(f"Image compressed: {size_kb:.1f}KB")
        return img_base64
    
    def extract_text(self, image_array, target_lang="en") -> str:
        
        try:
            img_base64 = self._compress_image(image_array)

            if target_lang != "en":
                prompt = f"{self.prompt}\n\nTranslate to {target_lang}."
            else:
                prompt = self.prompt
            
            data = {
                "model": "gemini-2.5-flash",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 4096
            }
            
            for attempt in range(len(self.api_keys) * 2):
                try:
                    key = self._get_next_key()
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {key}"
                    }
                    
                    response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
                    
                    if response.status_code == 200:
                        result = response.json()
                        text = result['choices'][0]['message']['content']
                        log.debug(f"Gemini extracted {len(text)} chars")
                        return text.strip()
                    else:
                        log.warning(f"API error: {response.status_code}")
                        
                except Exception as e:
                    log.warning(f"API key failed: {e}")
                    continue
            
            raise Exception("All API keys failed")
            
        except Exception as e:
            log.exception(f"Gemini OCR failed: {e}")
            return ""