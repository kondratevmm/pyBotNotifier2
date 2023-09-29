import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN_MIPT')
INVEST_TOKEN = os.getenv('INVEST_TOKEN_READ')