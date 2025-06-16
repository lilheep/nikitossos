from fastapi import FastAPI, HTTPException, Request, Query
import hashlib
from database import db_connection
import re
from models import Users, Tours, StatusBooking, Bookings, PaymentsMethods, PaymentStatus, Payments, Destinations, TourDestinations, PasswordChangeRequest
from pydantic import BaseModel
from email_utils import send_email, generation_confirmation_code
from datetime import datetime, timedelta


app = FastAPI()

def hash_password(password: str) -> str:
    return hashlib.sha512(password.encode('utf-8')).hexdigest()

EMAIL_REGEX = r'^[A-Za-zА-Яа-яЁё0-9._%+-]+@[A-Za-zА-Яа-яЁё-]+\.[A-Za-zА-Яа-яЁё-]{2,10}$'
PHONE_REGEX = r'^[0-9+()\-#]{10,15}$'

class AuthRequest(BaseModel):
    email: str | None = None
    number_phone: str | None = None
    password: str

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
            
@app.post('/users/auth/')
async def auth_user(data: AuthRequest):
    email = data.email
    number_phone = data.number_phone
    password = data.password
    
    if not email and not number_phone:
        raise HTTPException(400, 'Введите email, либо номер телефона!')
    if email is not None:
        if not isinstance(email, str) or not re.fullmatch(EMAIL_REGEX, email):
            raise HTTPException(400, 'Неверный формат данных email.')
    if number_phone is not None:
        if not isinstance(number_phone, str) or not re.fullmatch(PHONE_REGEX, number_phone):
            raise HTTPException(400, 'Неверный формат данных номера телефона.')
    try:
        query = None
        if email:
            query = Users.select().where(Users.email==email)
        elif number_phone:
            query = Users.select().where(Users.number_phone==number_phone
                                         )
        existing_user = query.first() if query else None
        if not existing_user:
            raise HTTPException(404, 'Пользователь с таким email/номера телефона не существует.')
        enter_hash_password = hash_password(password)
        if enter_hash_password != existing_user.password:
            raise HTTPException(401, 'Вы ввели неверный пароль! Попробуйте еще раз.')
        
        return {'message': 'Вы успешно авторизовались.'}
    except HTTPException:
        raise
    
    except Exception as e:
        raise HTTPException(500, f'Произошла ошибка при авторизации: {e}')

@app.post('/users/change_password/')
async def request_password_change(email: str):
    user = Users.select().where(Users.email==email).first()
    if not user:
        raise HTTPException(404, 'Пользователь с таким email не найден.')
    code = generation_confirmation_code(6)
    expires = datetime.now() + timedelta(minutes=10)
    PasswordChangeRequest.create(
                                user=user, 
                                code=code,
                                expires_at=expires)
    send_email(
                to_email=email,
                subject='Код подтверждения смены пароля.',
                body=f'Ваш код подтверждения смены пароля: {code}. Он действителен 10 минут.'
               )
    
    return {'message': 'Код подтверждения успешно отправлен.'}

@app.post('/users/confirm_change_password/')
async def confirm_password_change(email: str, code: str, new_password: str):
    user = Users.select().where(Users.email==email).first()
    if not user:
        raise HTTPException(404, 'Пользователь с таким email не найден.')
    request = PasswordChangeRequest.select().where((PasswordChangeRequest.user==user)
                                                   & (PasswordChangeRequest.code==code)).order_by(PasswordChangeRequest.created_at.desc()).first()
    
    if not request:
        raise HTTPException(404, 'Неверный код подтверждения.')
    
    if datetime.now() > request.expires_at:
        raise HTTPException(400, 'Срок действия кода истек. Попробуйте снова.')
    
    Users.update({
            Users.password: hash_password(new_password)
        }).where(Users.id == request.user.id).execute()
    
    request.delete_instance()
    
    return {'message': 'Пароль успешно обновлен.'}