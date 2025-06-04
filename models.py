from peewee import Model, CharField, AutoField, IntegerField, ForeignKeyField, DateTimeField, Check
from database import db_connection
import datetime

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
    #role = ---

class Tours(BaseModel):
    """"Информация о турах"""
    id = AutoField()
    name = CharField(max_length=100, null=False)
    description = CharField(max_length=255, null=True)
    price = IntegerField(null=False)
    days = IntegerField(null=False)
    country = CharField(max_length=255, null=False)

class StatusBooking(BaseModel):
    """Статусы бронирования тура"""
    id = AutoField()
    status_name = CharField(max_length=255, null=False)

class Bookings(BaseModel):
    """"Бронирование туров"""
    booking_id = AutoField()
    user_id = ForeignKeyField(Users, backref='user', on_delete='CASCADE', null=False)
    tour_id = ForeignKeyField(Tours, backref='tour', on_delete='SET NULL', null=True)
    booking_date = DateTimeField(datetime.datetime.now())
    status = ForeignKeyField(StatusBooking, backref='stat', on_delete='SET NULL', null=True)
    number_of_people = IntegerField()

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
    name = CharField(max_length=255, null=False)
    country = CharField(max_length=255, null=False, unique=True)
    description = CharField(max_length=255, null=True)

class TourDestinations(BaseModel):
    """Направления, куда идет тур"""
    id = AutoField()
    tour_id = ForeignKeyField(Tours, backref='tour_dest', on_delete='CASCADE', null=False)
    destinations_id = ForeignKeyField(Destinations, backref='dest_tour', on_delete='CASCADE', null=False)

tables = [Users, Tours, StatusBooking, Bookings, PaymentsMethods, PaymentStatus, Payments, Destinations, TourDestinations]

def initialize_tables():
    '''Creating tables if they does not exists'''
    db_connection.create_tables(tables, safe=True)
    print('Tables is initialized')

# Initialize
try:
    db_connection.connect()
    initialize_tables()
except Exception as e:
    print(f'Error initializing tables: {e}')
finally:
    db_connection.close()