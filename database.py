from peewee import MySQLDatabase
from pymysql import MySQLError
import pymysql

# Defines
DB_HOST     = 'localhost'
DB_PORT     = 3306
DB_USERNAME = 'root'
DB_PASSWORD = 'root'
DB_NAME     = 'tourist_ag'

def init_database():
    '''Creating database if it does not exists'''
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USERNAME, 
            password=DB_PASSWORD 
        )

        with connection.cursor() as cursor:
            cursor.execute(f'CREATE DATABASE IF NOT EXISTS {DB_NAME}')

        print(f'Database {DB_NAME} is initialized!')
    except MySQLError as e:
        print(f"Error creating database: {e}")
    finally:
        connection.close()

# Initialize
init_database()

# Creating connection
db_connection = MySQLDatabase(
    DB_NAME, 
    user=DB_USERNAME, 
    password=DB_PASSWORD, 
    host=DB_HOST, 
    port=DB_PORT
)