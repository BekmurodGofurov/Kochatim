from environs import Env

env = Env()
env.read_env()

BOT_TOKEN = env.str("BOT_TOKEN")
ADMINS = env.str("ADMINS")
DB_URL = env.str("DATABASE_URL")
IP = env.str("IP")
