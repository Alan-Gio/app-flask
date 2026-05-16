from dotenv import load_dotenv
import os

load_dotenv()

class ConfigVar:
    # --- Configuración de Base de Datos ---
    SECRET_KEY = os.getenv("SECRET_KEY")
    MYSQL_HOST = os.getenv("MYSQL_HOST")
    MYSQL_USER = os.getenv("MYSQL_USER")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_DB = os.getenv("MYSQL_DATABASE")
    MYSQL_UNIX_SOCKET = os.getenv("MYSQL_UNIX_SOCKET")
    
    # --- Configuración de Flask-Mail ---
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")