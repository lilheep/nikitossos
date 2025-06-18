from fastapi import FastAPI, HTTPException, Request, Query, Header, Depends, Form
import hashlib
from database import db_connection
import re
from models import Users, Tours, StatusBooking, Bookings, PaymentsMethods, PaymentStatus, Payments, Destinations, TourDestinations, PasswordChangeRequest
from pydantic import BaseModel
from email_utils import send_email, generation_confirmation_code
from datetime import datetime, timedelta
import uuid
from typing import Optional


app = FastAPI()

def hash_password(password: str) -> str:
    return hashlib.sha512(password.encode('utf-8')).hexdigest()

EMAIL_REGEX = r'^[A-Za-zА-Яа-яЁё0-9._%+-]+@[A-Za-zА-Яа-яЁё-]+\.[A-Za-zА-Яа-яЁё-]{2,10}$'
PHONE_REGEX = r'^[0-9+()\-#]{10,15}$'

def get_user_by_token(token: str) -> Users:
    user = Users.select().where(Users.token==token).first()
    if not user:
        raise HTTPException(401, 'Неверный или отсутствующий токен.')
    if user.token_expires_at is None or datetime.now() > user.token_expires_at:
        raise HTTPException(401, 'Срок действия токена истек.')

    user.token_expires_at = datetime.now() + timedelta(hours=1)
    user.save()
    return user

class AuthRequest(BaseModel):
    email: str | None = None
    number_phone: str | None = None
    password: str
    
class TourSchema(BaseModel):
    name: str
    description: str | None = None
    price: int
    days: int
    country: str  

class TourSchemaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None
    days: Optional[int] = None
    country: Optional[str] = None
  
@app.post('/users/register/', tags=['Users'])
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
                number_phone=number_phone,
            )
        return {'message': 'Вы успешно зарегистрировались!'}
    except Exception as e:
        raise HTTPException(500, f'Произошла ошибка при регистрации: {e}')
            
@app.post('/users/auth/', tags=['Users'])
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
            query = Users.select().where(Users.number_phone==number_phone)
        existing_user = query.first() if query else None
        if not existing_user:
            raise HTTPException(404, 'Пользователь с таким email/номера телефона не существует.')
        enter_hash_password = hash_password(password)
        if enter_hash_password != existing_user.password:
            raise HTTPException(401, 'Вы ввели неверный пароль! Попробуйте еще раз.')
        
        token = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(hours=1)
        existing_user.token = token
        existing_user.token_expires_at = expires_at
        existing_user.save()
        
        return {'message': 'Вы успешно авторизовались.',
                'token': token,
                'token_expires_at': expires_at.isoformat()
                }
    except HTTPException:
        raise
    
    except Exception as e:
        raise HTTPException(500, f'Произошла ошибка при авторизации: {e}')

@app.post('/users/change_password/', tags=['Users'])
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

@app.post('/users/confirm_change_password/', tags=['Users'])
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
    
    updated_rows = Users.update({
            Users.password: hash_password(new_password)
        }).where(Users.id == request.user.id).execute()
    
    if updated_rows == 0:
        raise HTTPException(500, 'Не удалось обновить пароль.')
    
    request.delete_instance()
    
    return {'message': 'Пароль успешно обновлен.'}

@app.delete('/users/delete_profile/', tags=['Users'])
async def delete_profile(token: str = Form(...)):
    user = Users.select().where(Users.token == token).first()
    if not user:
        raise HTTPException(401, 'Пользователь не найден.')
    user.delete_instance()
    return {'message': 'Аккаунт успешно удален.'}

@app.get('/users/me/', tags=['Users'])
async def get_profile(token: str):
    user = Users.select().where(Users.token == token).first()
    if not user:
        raise HTTPException(401, 'Пользователь не найден.')
    return {
        'id': user.id,
        'email': user.email,
        'full_name': user.full_name,
        'number_phone': user.number_phone
    }

@app.post('/tours/create/', tags=['Tours'])
async def create_tour(data: TourSchema):
    name = data.name
    description = data.description
    price = data.price
    days = data.days
    country = data.country
    
    try:
        Tours.create(name=name, description=description, price=price, days=days, country=country)
        return {'message': 'Тур успешно создан.'}
    except Exception as e:
        raise HTTPException(500, f'Ошибка при создании тура: {e}')

@app.get('/tours/get_tours/', tags=['Tours'])
async def get_all_tours():
    tours = Tours.select()
    return [{
        'Название тура:': t.name,
        'Описание:': t.description,
        'Цена': t.price,
        'Длительность': t.days,
        'Страна': t.country
    } for t in tours
    ]
    
@app.get('/tours/get_tour_id', tags=['Tours'])
async def get_tour_by_id(tour_id: int):
    tour = Tours.select().where(Tours.id==tour_id).first()
    if not tour:
        raise HTTPException(404, 'Указанный тур не найден.')
    try:
        return {
            'Название тура:': tour.name,
            'Описание:': tour.description,
            'Цена': tour.price,
            'Длительность': tour.days,
            'Страна': tour.country
        }
    except Exception as e:
        raise HTTPException(500, f'Ошибка при получении тура: {e}')

@app.patch('/tours/update/', tags=['Tours'])
async def update_tour(tour_id: int, data: TourSchemaUpdate):
    tour = Tours.select().where(Tours.id==tour_id).first()
    if not tour:
        raise HTTPException(404, 'Указанный тур не найден.')
    try:
        if data.name is not None:
            tour.name = data.name
        if data.description is not None:
            tour.description = data.description
        if data.price is not None:
            tour.price = data.price
        if data.days is not None:
            tour.days = data.days
        if data.country is not None:
            tour.country = data.country
        
        tour.save()
        return {'message': 'Информация о туре успешно изменена.'}
    except Exception as e:
        raise HTTPException(500, f'Ошибка при обновлении данных о туре: {e}.')

@app.delete('/tours/delete_tour/', tags=['Tours'])
async def delete_tour_by_id(tour_id: int):
    tour = Tours.select().where(Tours.id==tour_id).first()
    if not tour:
        raise HTTPException(404, 'Указанный тур не найден.')
    
    try:
        tour.delete_instance()
        return {'message': 'Тур успешно удален.'}
    except Exception as e:
        raise HTTPException(500, f'Ошибка, тур не был удален: {e}')