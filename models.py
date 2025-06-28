from peewee import Model, CharField, AutoField, IntegerField, ForeignKeyField, DateTimeField, Check, DateField
from database import db_connection
import datetime
from dotenv import load_dotenv
import os
import hashlib

load_dotenv()

ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
ADMIN_PHONE = os.getenv('ADMIN_PHONE')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')


class BaseModel(Model):
    class Meta:
        database = db_connection

class Users(BaseModel):
    """Информация о пользователях"""
    id = AutoField()
    email = CharField(max_length=100, unique=True, null=False)
    password = CharField(max_length=128, unique=False, null=False)
    full_name = CharField(max_length=100, null=False)
    number_phone = CharField(max_length=13, null=False, unique=True)
    token = CharField(null=True, unique=True)
    token_expires_at = DateTimeField(null=True)
    role = CharField(max_length=20, default='Пользователь')
    
class PasswordChangeRequest(BaseModel):
    """"Запросы на смену пароля"""
    id = AutoField()
    user = ForeignKeyField(Users, backref='user_change', on_delete='CASCADE', null=False)
    code = CharField(max_length=10)
    created_at = DateTimeField(default=datetime.datetime.now())
    expires_at = DateTimeField()
    

class Tours(BaseModel):
    """"Информация о турах"""
    id = AutoField()
    name = CharField(max_length=100, null=False, unique=True)
    description = CharField(max_length=255, null=True)
    price = IntegerField(null=False)
    days = IntegerField(null=False)
    country = CharField(max_length=255, null=False)
    image_filename = CharField(max_length=255, null=True)

class StatusBooking(BaseModel):
    """Статусы бронирования тура"""
    id = AutoField()
    status_name = CharField(max_length=255, null=False)

class Bookings(BaseModel):
    """"Бронирование туров"""
    booking_id = AutoField()
    user_id = ForeignKeyField(Users, backref='user', on_delete='CASCADE', null=False)
    email = CharField(max_length=100, unique=True, null=False)
    birthday = DateField(null=False)
    tour_id = ForeignKeyField(Tours, backref='tour', on_delete='SET NULL', null=True)
    booking_date = DateTimeField(null=False)
    status = ForeignKeyField(StatusBooking, backref='stat', on_delete='SET NULL', null=True)
    number_of_people = IntegerField()
    booking_number = CharField(max_length=20, unique=True, null=False)

class PaymentsMethods(BaseModel):
    """"Способы оплаты"""
    id = AutoField()
    method_name = CharField(max_length=255, null=False, unique=True)
    
class PaymentStatus(BaseModel):
    """Статусы оплаты"""
    id = AutoField()
    status_payment = CharField(max_length=255, null=False)

class Payments(BaseModel):
    """"Информация об оплате туров"""
    id = AutoField()
    booking_id = ForeignKeyField(Bookings, backref='booking', on_delete='SET NULL', null=True)
    payment_date = DateTimeField(datetime.datetime.now())
    amount = IntegerField()
    method = ForeignKeyField(PaymentsMethods, backref='payment_method', on_delete='SET NULL', null=True)
    payment_status = ForeignKeyField(PaymentStatus, backref='status_pay', on_delete='SET NULL', null=True)

class Destinations(BaseModel):
    """Направления для туров"""
    id = AutoField()
    name = CharField(max_length=255, null=False, unique=True)
    country = CharField(max_length=255, null=False)
    description = CharField(max_length=255, null=True)

class TourDestinations(BaseModel):
    """Направления, куда идет тур"""
    id = AutoField()
    tour_id = ForeignKeyField(Tours, backref='tour_dest', on_delete='CASCADE', null=False)
    destinations_id = ForeignKeyField(Destinations, backref='dest_tour', on_delete='CASCADE', null=False)

tables = [Users, Tours, StatusBooking, Bookings, PaymentsMethods, PaymentStatus, Payments, Destinations, TourDestinations, PasswordChangeRequest]



def initialize_tables():
    db_connection.create_tables(tables, safe=True)
    print('Tables is initialized')
    
def create_admin():
    try:
        admin_email=ADMIN_EMAIL
        if not Users.select().where(Users.email==admin_email).exists():
            Users.create(
                email=ADMIN_EMAIL,
                password=hashlib.sha512(ADMIN_PASSWORD.encode('utf-8')).hexdigest(),
                full_name='Администратор',
                number_phone=ADMIN_PHONE,
                role='Администратор'
                )
            print('Администратор успешно создан.')
        else:
            print('Администратор уже существует.')
            
    except Exception as e:
        print(f'Ошибка, не удалось создать администратора: {e}')

def create_tours():
    try:
        if Tours.select().count() > 4:
            print('Тестовые туры уже созданы.')
            return
        
        tours = [
            {
                "name": "Отдых в Сочи",
                "description": "Прекрасный отдых на черноморском побережье",
                "price": 25000,
                "days": 7,
                "country": "Россия",
                "image_filename": "tour1.jpg"
            },
            {
                "name": "Горный Алтай",
                "description": "Приключения в горах Алтая",
                "price": 18000,
                "days": 5,
                "country": "Россия",
                "image_filename": "tour2.jpg"
            },
            {
                "name": "Турция, Анталия",
                "description": "Все включено на берегу Средиземного моря",
                "price": 35000,
                "days": 10,
                "country": "Турция",
                "image_filename": "tour3.jpg"
            },
            {
                "name": "Египет, Хургада",
                "description": "Погружение в мир коралловых рифов",
                "price": 40000,
                "days": 8,
                "country": "Египет",
                "image_filename": "tour4.jpg"
            },
            {
                "name": "Италия, Рим",
                "description": "Экскурсионный тур по историческим местам",
                "price": 55000,
                "days": 6,
                "country": "Италия",
                "image_filename": "tour5.jpg"
            }
        ]
        
        for tour_data in tours:
            Tours.create(**tour_data) 
        print('Туры успешно созданы.')
    except Exception as e:
        print(f'Ошибка при создании туров: {e}')
def create_status():
    try:
        if StatusBooking.select().count() > 2:
            print('Тестовые записи статус созданы.')
            return
        status_booking = [
            {
                "status_name": "В обработке"
            },
            {
                "status_name": "Успешно"
            },
            {
                "status_name": "Отказано"
            },
        ]
        for status in status_booking:
            StatusBooking.create(**status)
    except Exception as e:
        print(f'Ошибка при создании статусов заявок: {e}')
        
        
try:
    db_connection.connect()
    initialize_tables()
    create_admin()
    create_tours()
    create_status()
except Exception as e:
    print(f'Error initializing tables: {e}')
finally:
    db_connection.close()