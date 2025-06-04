from fastapi import FastAPI, HTTPException, Request
import hashlib
from database import db_connection
import re
from models import Users, Tours, StatusBooking, Bookings, PaymentsMethods, PaymentStatus, Payments, Destinations, TourDestinations


app = FastAPI()

def hash_password(password: str) -> str:
    return hashlib.sha512(password.encode('utf-8')).hexdigest()

EMAIL_REGEX = r'^[A-Za-zА-Яа-яЁё0-9._%+-]+@[A-Za-zА-Яа-яЁё-]+\.[A-Za-zА-Яа-яЁё-]{2,10}$'
PHONE_REGEX = r'^[0-9+()\-#]{10,15}$'

@app.post('/users/register/')
async def create_user(email: str, password: str, full_name: str, number_phone: str):
    if not re.fullmatch(EMAIL_REGEX, email) or not re.fullmatch(PHONE_REGEX, number_phone):
        raise HTTPException(400, 'Неверный формат данных email/номера телефона.')
    try:
        existing_user = Users.select().where((Users.email==email) | (Users.number_phone==number_phone)).first()
        if existing_user:
            raise HTTPException(403, 'Пользователь с таким email/номером телефона уже существует.')
            
        hashed_password = hash_password(password=password)
        with db_connection.atomic():
            Users.create(
                email=email,
                password=hashed_password,
                full_name=full_name,
                number_phone=number_phone
            )
        return {'message': 'Вы успешно зарегистрировались!'}
    except Exception as e:
        raise HTTPException(500, f'Произошла ошибка при регистрации: {e}')
            
    
    