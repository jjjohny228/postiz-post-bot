import os
from typing import Final
from dotenv import load_dotenv


load_dotenv()


class Config:
    TOKEN: Final = os.getenv('BOT_TOKEN', 'Enter bot token to the .env!')
    ADMIN_IDS: Final = tuple(int(i) for i in str(os.getenv('BOT_ADMIN_IDS')).split(','))
    POSTIZ_API_KEY: Final = os.getenv('POSTIZ_API_KEY', 'Enter postiz api to the .env!')

    DEBUG: Final = bool(os.getenv('DEBUG'))
