import os
import time
import requests
from telethon.sync import TelegramClient

# --- НАСТРОЙКИ ---
API_ID = 1234567 
API_HASH = 'your_hash'
GRIZZLY_KEY = 'YOUR_GRIZZLY_API_KEY'
PASSWORD_2FA = "MyPrivateCloud777" # Чтобы никто не зашел в акк

# Страны в Grizzly: usa (США), can (Канада)
COUNTRY_MAP = {
    "USA": "usa",
    "Canada": "can",
    "Vietnam": "vnm" # Самые дешевые
}

class GrizzlyReg:
    def __init__(self, country_code):
        self.api_url = "https://api.grizzlysms.com/stori/v1/guest"
        self.country = country_code

    def get_number(self):
        url = f"{self.api_url}/getNumber/service/tg/country/{self.country}?api_key={GRIZZLY_KEY}"
        res = requests.get(url).json()
        if 'activationId' in res:
            return res['activationId'], res['phoneNumber']
        return None, None

    def get_code(self, act_id):
        url = f"{self.api_url}/getStatus/id/{act_id}?api_key={GRIZZLY_KEY}"
        for _ in range(25):
            res = requests.get(url).text
            if "STATUS_OK" in res:
                return res.split(":")[1]
            time.sleep(12)
        return None

    def start_registration(self):
        act_id, phone = self.get_number()
        if not phone: return print("Баланс 0 или нет номеров.")
        
        client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH)
        client.connect()
        try:
            client.send_code_request(phone)
            code = self.get_code(act_id)
            if code:
                client.sign_up(code, first_name="User")
                client.edit_2fa(new_password=PASSWORD_2FA)
                print(f"Готово: {phone}")
                return f"{phone}.session"
        except Exception as e: print(e)
        finally: client.disconnect()
