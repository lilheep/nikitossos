from peewee import MySQLDatabase
from pymysql import MySQLError
import pymysql

"""Конфигурационные параметры для подключения к базе данных"""
DB_HOST = 'localhost'     # Хост базы данных
DB_PORT = 3306            # Порт базы данных
DB_USERNAME = 'root'      # Имя пользователя БД
DB_PASSWORD = 'root'      # Пароль пользователя БД
DB_NAME = 'tourist_ag'    # Название базы данных

def init_database():
    """Инициализация базы данных - создает БД если она не существует"""
    try:
        # Установка соединения с сервером БД (без указания конкретной базы)
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USERNAME, 
            password=DB_PASSWORD 
        )

        # Создание базы данных если она не существует
        with connection.cursor() as cursor:
            cursor.execute(f'CREATE DATABASE IF NOT EXISTS {DB_NAME}')

        print(f'Database {DB_NAME} is initialized!')
    except MySQLError as e:
        # Обработка ошибок подключения/создания БД
        print(f"Error creating database: {e}")
    finally:
        # Гарантированное закрытие соединения
        connection.close()

"""Инициализация базы данных при запуске приложения"""
init_database()

"""Создание подключения к базе данных с использованием Peewee ORM"""
db_connection = MySQLDatabase(
    DB_NAME, 
    user=DB_USERNAME, 
    password=DB_PASSWORD, 
    host=DB_HOST, 
    port=DB_PORT
)