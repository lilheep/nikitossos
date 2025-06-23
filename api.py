from fastapi import FastAPI, HTTPException, Request, Query, Header, Depends, Form
import hashlib
from database import db_connection
import re
from models import Users, Tours, StatusBooking, Bookings, PaymentsMethods, PaymentStatus, Payments, Destinations, TourDestinations, PasswordChangeRequest
from pydantic import BaseModel, EmailStr
from email_utils import send_email, generation_confirmation_code
from datetime import datetime, timedelta, date
import uuid
from typing import Optional
from pydantic import Field


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

class StatusBookingSchema(BaseModel):
    status_name: str

class BookingSchemaCreate(BaseModel):
    birthday: date
    tour_name: Optional[str] = None
    status: Optional[str] = None
    number_of_people: int = Field(gt=0, description='Количество человек должно быть больше нуля.')
    
class BookingSchemaUpdate(BaseModel):
    birthday: Optional[date] = None
    tour_name: Optional[str] = None
    status: Optional[str] = None
    number_of_people: Optional[int] = Field(default=None, gt=0, description='Количество человек должно быть больше нуля.')

class BookingSchema(BaseModel):
    user_id: int
    email: str
    birthday: date
    tour_id: Optional[int]
    status: Optional[str]
    number_of_people: int
    
class PaymentMethodCreateSchema(BaseModel):
    method_name: str

class PaymentMethodUpdateSchema(BaseModel):
    method_name: str
    new_name_method: str
    
class PaymentMethodDeleteSchema(BaseModel):
    method_name: str
    
class PaymentStatusCreateSchema(BaseModel):
    status_payment: str

class PaymentStatusUpdateSchema(BaseModel):
    old_status_name: str
    new_status_name: str

class PaymentStatusDeleteSchema(BaseModel):
    status_name: str
    
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
    
    except HTTPException as http_exc:
        raise http_exc
    
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
    except HTTPException as http_exc:
        raise http_exc
    
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
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Пользователь не найден.')
    user.delete_instance()
    return {'message': 'Аккаунт успешно удален.'}

@app.get('/users/me/', tags=['Users'])
async def get_profile(token: str):
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Пользователь не найден.')
    return {
        'id': user.id,
        'email': user.email,
        'full_name': user.full_name,
        'number_phone': user.number_phone
    }

@app.post('/tours/create/', tags=['Tours'])
async def create_tour(data: TourSchema, token: str = Header(...)):
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    name = data.name
    description = data.description
    price = data.price
    days = data.days
    country = data.country
    
    try:
        Tours.create(name=name, description=description, price=price, days=days, country=country)
        return {'message': 'Тур успешно создан.'}
    
    except HTTPException as http_exc:
        raise http_exc
    
    except Exception as e:
        raise HTTPException(500, f'Ошибка при создании тура: {e}')

@app.get('/tours/get_tours/', tags=['Tours'])
async def get_all_tours(token: str = Header(...)):
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
        
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
async def get_tour_by_id(tour_id: int, token: str = Header(...)):
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
        
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
        
    except HTTPException as http_exc:
        raise http_exc
    
    except Exception as e:
        raise HTTPException(500, f'Ошибка при получении тура: {e}')

@app.patch('/tours/update/', tags=['Tours'])
async def update_tour(tour_id: int, data: TourSchemaUpdate, token: str = Header(...)):
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
        
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
    
    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(500, f'Ошибка при обновлении данных о туре: {e}.')

@app.delete('/tours/delete_tour/', tags=['Tours'])
async def delete_tour_by_id(tour_id: int, token: str = Header(...)):
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
        
    tour = Tours.select().where(Tours.id==tour_id).first()
    if not tour:
        raise HTTPException(404, 'Указанный тур не найден.')
    
    try:
        tour.delete_instance()
        return {'message': 'Тур успешно удален.'}
    
    except HTTPException as http_exc:
        raise http_exc
    
    except Exception as e:
        raise HTTPException(500, f'Ошибка, тур не был удален: {e}')

@app.post('/statusbooking/add_status', tags=['StatusBooking'])
async def add_status_booking(data: StatusBookingSchema, token: str = Header(...)):
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
        
    status = data.status_name
    try:
        StatusBooking.create(status_name=status)
        return {'message': 'Статус успешно создан.'}
    
    except HTTPException as http_exc:
        raise http_exc
    
    except Exception as e:
        raise HTTPException(500, f'Ошибка при создании статуса: {e}')
    
@app.get('/statusbooking/get_all/', tags=['StatusBooking'])
async def get_all_status_booking(token: str = Header(...)):
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
        
    status = StatusBooking.select()
    return [{
        'Статус': s.status_name
    } for s in status]

@app.put('/statusbooking/edit_status/', tags=['StatusBooking'])
async def edit_status_booking(status_id: int, data: StatusBookingSchema, token: str = Header(...)):
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
        
    status = StatusBooking.select().where(StatusBooking.id==status_id).first()
    if not status:
        raise HTTPException(404, f'Указанного статуса не существует.')
    try:
        status.status_name = data.status_name
        status.save()
        return {'message': 'Статус успешно изменен.'}
    
    except HTTPException as http_exc:
        raise http_exc
    
    except Exception as e:
        raise HTTPException(500, f'Ошибка при внесении изменений: {e}')

@app.get('/statusbooking/get_status_by_id/', tags=['StatusBooking'])
async def get_status_by_id(status_id: int, token: str = Header(...)):
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
        
    status = StatusBooking.select().where(StatusBooking.id==status_id).first()
    if not status:
        raise HTTPException(404, f'Указанного статуса не существует.')
    return {
        'Статус': status.status_name
    }

@app.post('/booking/create_booking/', tags=['Bookings'])
def create_booking(data: BookingSchemaCreate, token: str = Header(...)):
    try:
        user = get_user_by_token(token)
        if not user:
            raise HTTPException(401, 'Недействительный токен.')
        
        age = datetime.now().date() - data.birthday
        if age < timedelta(days = 365 * 18):
            raise HTTPException(403, 'Пользователю должно быть больше 18 лет.')
        
        tour = Tours.get_or_none(Tours.name==data.tour_name)
        if not tour:
            raise HTTPException(404, 'Тур не найден.')
        
        status_booking = StatusBooking.get_or_none(StatusBooking.status_name==data.status)
        if not status_booking:
            raise HTTPException(404, 'Статус не найден.')
        
        booking_number = uuid.uuid4().hex[:8].upper()
        
        booking = Bookings.create(
            user_id=user.id,
            email=user.email,
            birthday=data.birthday,
            tour_id=tour.id,
            booking_date=datetime.now(),
            status=status_booking.id,
            number_of_people=data.number_of_people,
            booking_number=booking_number
        )
        return {'message': 'Бронирование тура прошло успешно.',
                'Номер заявки': booking_number
                }
        
    except HTTPException as http_exc:
        raise http_exc
    
    except Exception as e:
        raise HTTPException(500, f'Произошла ошибка: {e}')
    
@app.put('/booking/update_booking/', tags=['Bookings'])
async def update_booking(booking_number: str, data: BookingSchemaUpdate, token: str = Header(...)):
    try:
        user = get_user_by_token(token)
        if not user:
            raise HTTPException(401, 'Недействительный токен.')
        
        booking = Bookings.select().where(Bookings.booking_number==booking_number).first()
        if not booking:
            raise HTTPException(404, 'Бронирование не найдено.')
        
        if booking.user_id.id != user.id:
            raise HTTPException(403, 'Нет прав на изменение этого бронирования.')

        if data is not None:
            if data.birthday is not None:
                age = datetime.now().date() - data.birthday
                if age < timedelta(days=365 * 18):
                    raise HTTPException(403, 'Пользователю должно быть больше 18 лет.')
                booking.birthday = data.birthday

            if data.tour_name is not None:
                tour = Tours.select().where(Tours.name == data.tour_name).first()
                if not tour:
                    raise HTTPException(404, 'Указанный тур не найден.')
                booking.tour_id = tour.id

            if data.status is not None:
                status_booking = StatusBooking.select().where(StatusBooking.status_name == data.status).first()
                if not status_booking:
                    raise HTTPException(404, 'Статус не найден.')
                booking.status = status_booking.id

            if data.number_of_people is not None:
                if data.number_of_people <= 0:
                    raise HTTPException(400, 'Количество человек должно быть больше нуля.')
                booking.number_of_people = data.number_of_people

            booking.save()

        return {'message': 'Бронирование успешно обновлено.'}

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(500, f'Произошла ошибка: {e}')
    
@app.delete('/booking/delete_booking/', tags=['Bookings'])
async def delete_booking(booking_number: str, token: str = Header(...)):
    try:
        user = get_user_by_token(token)
        if not user:
            raise HTTPException(401, 'Недействительный токен.')

        booking = Bookings.select().where(Bookings.booking_number == booking_number).first()
        if not booking:
            raise HTTPException(404, 'Бронирование не найдено.')

        if booking.user_id.id != user.id:
            raise HTTPException(403, 'Нет прав на удаление этого бронирования.')

        booking.delete_instance()
        
        return {'message': 'Бронирование успешно удалено.'}
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(500, f'Произошла ошибка при удалении: {e}')

@app.get('/booking/all_bookings/', tags=['Bookings'])
async def get_all_bookings(token: str = Header(...)):
    try:
        user = get_user_by_token(token)
        if not user:
            raise HTTPException(401, 'Недействительный токен.')
        
        bookings = Bookings.select()
        return [{
            'Номер заявки:': b.booking_number,
            'e-mail:': b.email,
            'Название тура:': b.tour_id.name,
            'Дата бронирования:': b.booking_date,
            'Статус:': b.status.status_name,
            'Количество человек:': b.number_of_people
            } for b in bookings]
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(500, f'Ошибка при получении списка бронирований: {e}')

@app.get('/booking/get_booking_by_user/', tags=['Bookings'])
def get_booking_by_user(email: str, token: str = Header(...)):
    try:
        user = get_user_by_token(token)
        if not user:
            raise HTTPException(401, 'Недействительный токен.')
        b = Bookings.get_or_none(Bookings.email==email)
        if not b:
            raise HTTPException(404, 'Для данного пользователя нет заявок на бронирование.')
        
        return [{
            'Номер заявки:': b.booking_number,
            'Название тура:': b.tour_id.name,
            'Дата бронирования:': b.booking_date,
            'Статус:': b.status.status_name,
            'Количество человек:': b.number_of_people
        }]
    
    except HTTPException as http_exc:
        raise http_exc
    
    except Exception as e:
        raise HTTPException(500, f'Ошибка при получении списка бронирований: {e}')
    
@app.post('/payment_methods/create_method/', tags=['Payment Methods'])
async def create_payment_method(data: PaymentMethodCreateSchema, token: str = Header(...)):
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    try:
        existing_method = PaymentsMethods.get_or_none(PaymentsMethods.method_name == data.method_name)
        if existing_method:
            raise HTTPException(400, 'Такой способ оплаты уже существует.')
            
        method = PaymentsMethods.create(method_name=data.method_name)
        return {'message': 'Способ оплаты успешно создан.'}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(500, f'Ошибка при создании способа оплаты: {e}')

@app.get('/payment_methods/get_all_methods/', tags=['Payment Methods'])
async def get_all_payment_methods(token: str = Header(...)):
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    try:
        methods = PaymentsMethods.select()
        return [{
            'ID:': method.id,
            'Название метода:': method.method_name
        } for method in methods]
    except Exception as e:
        raise HTTPException(500, f'Ошибка при получении способов оплаты: {e}')

@app.put('/payment_methods/edit_method/', tags=['Payment Methods'])
async def update_payment_method(data: PaymentMethodUpdateSchema, token: str = Header(...)):
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    try:
        method = PaymentsMethods.get_or_none(PaymentsMethods.method_name==data.method_name)
        if not method:
            raise HTTPException(404, 'Способ оплаты не найден.')

        existing_method = PaymentsMethods.get_or_none(PaymentsMethods.method_name == data.new_name_method)
        if existing_method:
            raise HTTPException(400, 'Способ оплаты с таким названием уже существует.')
        
        method.method_name = data.new_name_method
        method.save()
        
        return {
            'message': 'Способ оплаты успешно обновлен.',
            'Название метода': method.method_name
        }
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(500, f'Ошибка при обновлении способа оплаты: {e}')

@app.delete('/payment_methods/delete_method/', tags=['Payment Methods'])
async def delete_payment_method(data: PaymentMethodDeleteSchema, token: str = Header(...)):
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    try:
        method = PaymentsMethods.get_or_none(PaymentsMethods.method_name == data.method_name)
        if not method:
            raise HTTPException(404, 'Способ оплаты не найден.')
        
        method.delete_instance()
        return {'message': 'Способ оплаты успешно удален.'}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(500, f'Ошибка при удалении способа оплаты: {e}')
    
@app.post('/payment_status/create_status/', tags=['Payment Status'])
async def create_payment_status(data: PaymentStatusCreateSchema, token: str = Header(...)):
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    try:
        existing_status = PaymentStatus.get_or_none(PaymentStatus.status_payment == data.status_payment)
        if existing_status:
            raise HTTPException(400, 'Такой статус оплаты уже существует.')
            
        status = PaymentStatus.create(status_payment=data.status_payment)
        return {'message': 'Статус оплаты успешно создан.'}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(500, f'Ошибка при создании статуса оплаты: {e}')

@app.get('/payment_status/get_all_statuses/', tags=['Payment Status'])
async def get_all_payment_statuses(token: str = Header(...)):
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    try:
        statuses = PaymentStatus.select()
        return [{
            'ID': status.id,
            'Статус оплаты': status.status_payment
        } for status in statuses]
    except Exception as e:
        raise HTTPException(500, f'Ошибка при получении статусов оплаты: {e}')

@app.put('/payment_status/edit_status/', tags=['Payment Status'])
async def update_payment_status(data: PaymentStatusUpdateSchema, token: str = Header(...)):
    """Обновление статуса оплаты"""
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    try:
        status = PaymentStatus.get_or_none(PaymentStatus.status_payment == data.old_status_name)
        if not status:
            raise HTTPException(404, 'Статус оплаты не найден.')

        existing_status = PaymentStatus.get_or_none(PaymentStatus.status_payment == data.new_status_name)
        if existing_status:
            raise HTTPException(400, 'Статус оплаты с таким названием уже существует.')

        status.status_payment = data.new_status_name
        status.save()
        
        return {'message': 'Статус оплаты успешно обновлен.',}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(500, f'Ошибка при обновлении статуса оплаты: {e}')

@app.delete('/payment_status/delete_status/', tags=['Payment Status'])
async def delete_payment_status(data: PaymentStatusDeleteSchema, token: str = Header(...)):
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    try:
        status = PaymentStatus.get_or_none(PaymentStatus.status_payment == data.status_name)
        if not status:
            raise HTTPException(404, 'Статус оплаты не найден.')
        
        status.delete_instance()
        return {'message': 'Статус оплаты успешно удален.'}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(500, f'Ошибка при удалении статуса оплаты: {e}')