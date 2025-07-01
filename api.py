from fastapi import FastAPI, HTTPException, Request, Query, Header, Depends, Form
from fastapi import UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from database import db_connection
import hashlib
import re
import os
from models import Roles, Users, Tours, StatusBooking, Bookings, PaymentsMethods, PaymentStatus, Payments, Destinations, TourDestinations, PasswordChangeRequest
from pydantic import BaseModel, EmailStr
from email_utils import send_email, generation_confirmation_code
from datetime import datetime, timedelta, date
import uuid
from typing import Optional
from pydantic import Field
import aiofiles



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

"""Настройка директории для хранения изображений"""
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, 'data', 'images')
os.makedirs(IMAGE_DIR, exist_ok=True)
app.mount('/images', StaticFiles(directory=IMAGE_DIR), name='images')

def hash_password(password: str) -> str:
    """Функция хеширования паролей"""
    return hashlib.sha512(password.encode('utf-8')).hexdigest()

EMAIL_REGEX = r'^[A-Za-zА-Яа-яЁё0-9._%+-]+@[A-Za-zА-Яа-яЁё-]+\.[A-Za-zА-Яа-яЁё-]{2,10}$'
PHONE_REGEX = r'^[0-9+()\-#]{10,15}$'


def get_user_by_token(token: str, required_role: Optional[str] = None) -> Users:
    """Функция аутентификации пользователя по токену"""
    user = Users.select().where(Users.token==token).first()
    if not user:
        raise HTTPException(401, 'Неверный или отсутствующий токен.')
    if user.token_expires_at is None or datetime.now() > user.token_expires_at:
        raise HTTPException(401, 'Срок действия токена истек.')
    if required_role and user.role.name != required_role:
        raise HTTPException(403, 'Недостаточно прав для выполнения этого действия.')

    user.token_expires_at = datetime.now() + timedelta(hours=1)
    user.save()
    return user

class AuthRequest(BaseModel):
    """Модель запроса аутентификации"""
    email: str | None = None
    number_phone: str | None = None
    password: str

class SetRoleRequest(BaseModel):
    """Модель запроса смены роли пользователя"""
    email: Optional[str] = None
    number_phone: Optional[str] = None
    new_role: str
    
class TourSchema(BaseModel):
    """Модель создания тура"""
    name: str = Form(...)
    description: Optional[str] = Form(None)
    price: int = Form(...)
    days: int = Form(...)
    country: str = Form(...)
    token: str = Header(...)
    image: UploadFile = File(...) 

class TourSchemaUpdate(BaseModel):
    """Модель обновления тура"""
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None
    days: Optional[int] = None
    country: Optional[str] = None

class StatusBookingSchema(BaseModel):
    """Модель статуса бронирования"""
    status_name: str

class BookingSchemaCreate(BaseModel):
    """Модель создания бронирования"""
    birthday: date
    tour_name: Optional[str] = None
    status: Optional[str] = None
    number_of_people: int = Field(gt=0, description='Количество человек должно быть больше нуля.')
    
class BookingSchemaUpdate(BaseModel):
    """Модель обновления бронирования"""
    birthday: Optional[date] = None
    tour_name: Optional[str] = None
    status: Optional[str] = None
    number_of_people: Optional[int] = Field(default=None, gt=0, description='Количество человек должно быть больше нуля.')

class BookingSchema(BaseModel):
    """Модель бронирования"""
    user_id: int
    email: str
    birthday: date
    tour_id: Optional[int]
    status: Optional[str]
    number_of_people: int
    
class PaymentMethodCreateSchema(BaseModel):
    """Модель создания метода оплаты"""
    method_name: str

class PaymentMethodUpdateSchema(BaseModel):
    """Модель обновления метода оплаты"""
    method_name: str
    new_name_method: str
    
class PaymentMethodDeleteSchema(BaseModel):
    """Модель удаления метода оплаты"""
    method_name: str
    
class PaymentStatusCreateSchema(BaseModel):
    """Модель создания статуса оплаты"""
    status_payment: str

class PaymentStatusUpdateSchema(BaseModel):
    """Модель обновления статуса оплаты"""
    old_status_name: str
    new_status_name: str

class PaymentStatusDeleteSchema(BaseModel):
    """Модель удаления статуса оплаты"""
    status_name: str
    
class PaymentsCreate(BaseModel):
    """Модель создания платежа"""
    booking_number: str
    method_name: str
    payment_status_name: str

class PaymentsUpdate(BaseModel):
    """Модель обновления платежа"""
    payment_id: int
    booking_number: Optional[str] | None = None
    amount: Optional[int] | None = None
    payment_status_name: Optional[str] | None = None

class DestinationCreateSchema(BaseModel):
    """Модель создания направления"""
    name: str
    country: str
    description: Optional[str] = None

class DestinationUpdateSchema(BaseModel):
    """Модель обновления направления"""
    name: Optional[str] = None
    country: Optional[str] = None
    description: Optional[str] = None

class TourDestinationCreateSchema(BaseModel):
    """Модель создания связи тур-направление"""
    tour_name: str
    destination_id: int

class TourDestinationResponseSchema(BaseModel):
    """Модель ответа для связи тур-направление"""
    id: int
    tour_name: str
    city: str
    country: str

class TourDestinationUpdateSchema(BaseModel):
    """Модель обновления связи тур-направление"""
    old_tour_name: str
    old_destination_id: int
    new_tour_name: Optional[str] = None
    new_destination_id: Optional[int] = None

@app.post('/users/register/', tags=['Users'])
async def create_user(email: str, password: str, full_name: str, number_phone: str): 
    """Регистрация нового пользователя"""
    if not re.fullmatch(EMAIL_REGEX, email) or not re.fullmatch(PHONE_REGEX, number_phone):
        raise HTTPException(400, 'Неверный формат данных email/номера телефона.')
    try:
        existing_user = Users.select().where((Users.email==email) | (Users.number_phone==number_phone)).first()
        if existing_user:
            raise HTTPException(403, 'Пользователь с таким email/номером телефона уже существует.')
            
        hashed_password = hash_password(password=password)
        with db_connection.atomic():
            user_role = Roles.get(Roles.id == 1)
            Users.create(
                email=email,
                password=hashed_password,
                full_name=full_name,
                number_phone=number_phone,
                role=user_role
            )
        return {'message': 'Вы успешно зарегистрировались!'}
    
    except HTTPException as http_exc:
        raise http_exc
    
    except Exception as e:
        raise HTTPException(500, f'Произошла ошибка при регистрации: {e}')
            
@app.post('/users/auth/', tags=['Users'])
async def auth_user(data: AuthRequest):
    """Аутентификация пользователя"""
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
    """Запрос на смену пароля"""
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
    """Подтверждение смены пароля"""
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
async def delete_profile(token: str = Header(...)):
    """Удаление профиля пользователя"""
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Пользователь не найден.')
    user.delete_instance()
    return {'message': 'Аккаунт успешно удален.'}

@app.get('/users/me/', tags=['Users'])
async def get_profile(token: str):
    """Получение информации о текущем пользователе"""
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Пользователь не найден.')
    return {
        'id': user.id,
        'email': user.email,
        'full_name': user.full_name,
        'number_phone': user.number_phone,
        'role': user.role.name
    }


@app.post('/users/set_role/', tags=['Users'])
async def set_user_role(data: SetRoleRequest, token: str = Header(...)):
    """Изменение роли пользователя (только для администратора)"""
    current_user = get_user_by_token(token, 'Администратор')
    try:
        if not data.email and not data.number_phone:
            raise HTTPException(400, 'Укажите email или номер телефона.')
        
        if data.email:
            user = Users.select().where(Users.email == data.email).first()
        elif data.number_phone:
            user = Users.select().where(Users.number_phone == data.number_phone).first()
        
        if not user:
            raise HTTPException(404, 'Пользователь не найден')
        
        new_role = Roles.get_or_none(Roles.name == data.new_role)
        if not new_role:
            raise HTTPException(400, 'Недопустимая роль. Допустимые значения: Пользователь, Администратор')
        
        user.role = new_role
        user.save()
        
        return {
            'message': 'Роль пользователя успешно изменена',
            'email': user.email,
            'Номер телефона': user.number_phone,
            'Новая роль': data.new_role
            }
    except HTTPException as http_exc:
        raise http_exc
              
    except Exception as e:
        raise HTTPException(500, f'Ошибка при изменении роли: {e}')
    
@app.get('/users/get_all/', tags=['Users'])
async def get_all_users(token: str = Header(...)):
    """Получение списка всех пользователей (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    users = Users.select()
    return [{
        'id': u.id,
        'email': u.email,
        'full_name': u.full_name,
        'number_phone': u.number_phone,
        'role': u.role.name
    } for u in users]

@app.delete('/users/delete_admin_user/', tags=['Users'])
async def admin_delete_user(user_id: int, token: str = Header(...)):
    """Удаление пользователя администратором"""
    admin = get_user_by_token(token, 'Администратор')
    if not admin:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    try:
        user = Users.get(Users.id == user_id)
        if user.role.name == 'Администратор':
            admins_count = Users.select().where(Users.role.name == 'Администратор').count()
            if admins_count == 1:
                raise HTTPException(400, 'Нельзя удалить последнего администратора.')

        user.delete_instance()
        return {'message': 'Пользователь успешно удален.'}
        
    except Users.DoesNotExist:
        raise HTTPException(404, 'Пользователь не найден.')
    except Exception as e:
        raise HTTPException(500, f'Ошибка при удалении пользователя: {e}')

@app.post('/tours/create/', tags=['Tours'])
async def create_tour(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    price: int = Form(...),
    days: int = Form(...),
    country: str = Form(...),
    token: str = Header(...),
    image: UploadFile = File(...)
):
    """Создание нового тура (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    try:
        allowed_extensions = ['.jpg', '.jpeg', '.png']
        file_ext = os.path.splitext(image.filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(400, 'Недопустимый формат изображения. Допустимы: jpg, jpeg, png.')
        
        filename = f'{uuid.uuid4().hex}{file_ext}'
        file_path = os.path.join(IMAGE_DIR, filename)

        async with aiofiles.open(file_path, 'wb') as buffer:
            content = await image.read()
            await buffer.write(content)
            
        Tours.create(
            name=name,
            description=description,
            price=price,
            days=days,
            country=country,
            image_filename=filename
        )
        return {'message': 'Тур успешно создан.'}
    
    except HTTPException as http_exc:
        raise http_exc
    
    except Exception as e:
        raise HTTPException(500, f'Ошибка при создании тура: {e}')

@app.get('/tours/get_tours/', tags=['Tours'])
async def get_all_tours(token: str = Header(...)):
    """Получение списка всех туров"""
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
        
    tours = Tours.select()
    return [{
        'id': t.id,
        'name': t.name,
        'description': t.description,
        'price': t.price,
        'days': t.days,
        'country': t.country,
        'image_url': f'/images/{t.image_filename}' if t.image_filename else None
    } for t in tours]
    
@app.get('/tours/get_tour_id/', tags=['Tours'])
async def get_tour_by_id(tour_id: int, token: str = Header(...)):
    """Получение тура по ID (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
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
    """Обновление информации о туре (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
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
    """Удаление тура по ID (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
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

"""Эндпоинты для работы со статусами бронирования"""
@app.post('/statusbooking/add_status', tags=['StatusBooking'])
async def add_status_booking(data: StatusBookingSchema, token: str = Header(...)):
    """Добавление нового статуса бронирования (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
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
    """Получение всех статусов бронирования (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
        
    status = list(StatusBooking.select())
    if not status:
        raise HTTPException(404, 'Статусы бронирования не найдены')
    return [{
        'id': s.id,
        'Статус': s.status_name
    } for s in status]

@app.put('/statusbooking/edit_status/', tags=['StatusBooking'])
async def edit_status_booking(status_id: int, data: StatusBookingSchema, token: str = Header(...)):
    """Редактирование статуса бронирования (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
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
    """Получение статуса бронирования по ID (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
        
    status = StatusBooking.select().where(StatusBooking.id==status_id).first()
    if not status:
        raise HTTPException(404, f'Указанного статуса не существует.')
    return {
        'Статус': status.status_name
    }
    
@app.delete('/statusbooking/delete_status/', tags=['StatusBooking'])
async def delete_booking_status(status_id: int, token: str = Header(...)):
    """Удаление статуса бронирования (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
        
    try:
        status = StatusBooking.get_or_none(StatusBooking.id == status_id)
        if not status:
            raise HTTPException(404, 'Статус не найден.')
        
        bookings_count = Bookings.select().where(Bookings.status == status_id).count()
        if bookings_count > 0:
            raise HTTPException(400, 'Невозможно удалить статус, так как он используется в бронированиях.')
        
        status.delete_instance()
        return {'message': 'Статус успешно удален.'}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(500, f'Ошибка при удалении статуса: {e}')

@app.post('/booking/create_booking/', tags=['Bookings'])
def create_booking(data: BookingSchemaCreate, token: str = Header(...)):
    """Создание нового бронирования"""
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
        
        status_booking = StatusBooking.get_or_none(StatusBooking.status_name=='Ожидает оплаты')
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
    """Обновление информации о бронировании"""
    try:
        user = get_user_by_token(token)
        if not user:
            raise HTTPException(401, 'Недействительный токен.')
        
        booking = Bookings.select().where(Bookings.booking_number==booking_number).first()
        if not booking:
            raise HTTPException(404, 'Бронирование не найдено.')
        
        if user.role != 'Администратор' and booking.user_id.id != user.id:
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
    """Удаление бронирования"""
    try:
        user = get_user_by_token(token)
        if not user:
            raise HTTPException(401, 'Недействительный токен.')

        booking = Bookings.select().where(Bookings.booking_number == booking_number).first()
        if not booking:
            raise HTTPException(404, 'Бронирование не найдено.')

        if user.role != 'Администратор' and booking.user_id.id != user.id:
            raise HTTPException(403, 'Нет прав на удаление этого бронирования.')

        booking.delete_instance()
        
        return {'message': 'Бронирование успешно удалено.'}
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(500, f'Произошла ошибка при удалении: {e}')

@app.get('/booking/all_bookings/', tags=['Bookings'])
async def get_all_bookings(token: str = Header(...)):
    """Получение всех бронирований (только для администратора)"""
    try:
        user = get_user_by_token(token, 'Администратор')
        if not user:
            raise HTTPException(401, 'Недействительный токен.')
        
        bookings = Bookings.select()
        return [{
            'Номер заявки:': b.booking_number,
            'e-mail:': b.email,
            'Дата рождения:': b.birthday.isoformat(),
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
    """Получение бронирований по email пользователя"""
    try:
        user = get_user_by_token(token)
        if not user:
            raise HTTPException(401, 'Недействительный токен.')
        bookings = Bookings.select().where(Bookings.email==email)
        if not bookings:
            raise HTTPException(404, 'Для данного пользователя нет заявок на бронирование.')
        
        return [{
            'Номер заявки:': b.booking_number,
            'Название тура:': b.tour_id.name,
            'Дата бронирования:': b.booking_date,
            'Статус:': b.status.status_name,
            'Количество человек:': b.number_of_people,
            'Дата рождения:': b.birthday.isoformat()
        } for b in bookings]
    
    except HTTPException as http_exc:
        raise http_exc
    
    except Exception as e:
        raise HTTPException(500, f'Ошибка при получении списка бронирований: {e}')

@app.post('/payment_methods/create_method/', tags=['Payment Methods'])
async def create_payment_method(data: PaymentMethodCreateSchema, token: str = Header(...)):
    """Создание метода оплаты (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
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
    """Получение всех методов оплаты (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
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
    """Обновление метода оплаты (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
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
    """Удаление метода оплаты (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
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
    """Создание статуса оплаты (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
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
    """Получение всех статусов оплаты (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
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
    """Обновление статуса оплаты (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
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
    """Удаление статуса оплаты (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
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

@app.post('/payments/add_payment/', tags=['Payments'])
async def create_payment(data: PaymentsCreate, token: str = Header(...)):
    """Создание платежа"""
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    try:
        booking = Bookings.get_or_none(Bookings.booking_number==data.booking_number)
        if not booking:
            raise HTTPException(404, 'Бронирования с таким номером не найдено.')

        tour = Tours.get_or_none(Tours.id == booking.tour_id_id)
        if not tour:
            raise HTTPException(404, 'Тур не найден.')
        
        amount = tour.price * booking.number_of_people
        
        method = PaymentsMethods.get_or_none(PaymentsMethods.method_name==data.method_name)
        if not method:
            raise HTTPException(404, 'Неверно указан способ оплаты.')
        
        status = PaymentStatus.get_or_none(PaymentStatus.status_payment==data.payment_status_name)
        if not status:
            raise HTTPException(404, 'Неверно указан статус оплаты.')

        payments = Payments.create(
            booking_id=booking.booking_id,
            payment_date=datetime.now(),
            amount=amount,
            method=method.id,
            payment_status=status.id         
        )

        paid_status = StatusBooking.get_or_none(StatusBooking.status_name=='Оплачено')
        if not paid_status:
            try:
                paid_status = StatusBooking.create(status_name='Оплачено')
            except Exception as e:
                raise HTTPException(500, f'Ошибка при создании статуса оплаты: {e}')
        
        booking.status_id = paid_status.id
        booking.save()
        
        return {
            'message': 'Платеж успешно добавлен.',
            'payment_id': payments.id,
            'amount': amount
        }
    
    except HTTPException as http_exc:
        raise http_exc
    
    except Exception as e:
        raise HTTPException(500, f'Произошла ошибка при создании платежа: {e}')

@app.patch('/payments/edit_payment/', tags=['Payments'])
async def edit_payment(data: PaymentsUpdate, token: str = Header(...)):
    """Редактирование платежа"""
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    try:
        payment = Payments.select().where(Payments.id==data.payment_id).first()
    
        if not payment:
            raise HTTPException(404, 'Платеж с указанным ID не найден.')
        if data.booking_number is not None:
            booking = Bookings.get_or_none(Bookings.booking_number==data.booking_number)
            if not booking:
                raise HTTPException(404, 'Бронирования с таким номером не найдено.')
            payment.booking_id = booking.booking_id
        if data.amount is not None:
            if data.amount <= 0:
                raise HTTPException(400, 'Сумма платежа должна быть положительной.')
            payment.amount = data.amount
        if data.payment_status_name is not None:
            status = PaymentStatus.get_or_none(PaymentStatus.status_payment == data.payment_status_name)
            if not status:
                raise HTTPException(404, 'Указанный статус платежа не найден.')
            payment.payment_status = status.id
            
        payment.save()
        
        return {'message': 'Платеж успешно обновлен.'}
    
    except HTTPException as http_exc:
        raise http_exc
    
    except Exception as e:
        raise HTTPException(500, f'Произошла ошибка при обновлении платежа: {e}')

@app.get('/payments/get_payment_by_id/', tags=['Payments'])
async def get_payment_by_id(payment_id: int, token: str = Header(...)):
    """Получение платежа по ID"""
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    try:
        payment = Payments.get_or_none(Payments.id == payment_id)
        if not payment:
            raise HTTPException(404, 'Платеж с указанным ID не найден.')

        booking = Bookings.get_or_none(Bookings.booking_id == payment.booking_id)
        method = PaymentsMethods.get_or_none(PaymentsMethods.id == payment.method)
        status = PaymentStatus.get_or_none(PaymentStatus.id == payment.payment_status)
        
        return {
            'id': payment.id,
            'Номер бронирования': booking.booking_number if booking else None,
            'Сумма': payment.amount,
            'Дата': payment.payment_date,
            'Метод оплаты': method.method_name if method else None,
            'Статус оплаты': status.status_payment if status else None
        }
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(500, f'Ошибка при получении платежа: {e}')


@app.get('/payments/get_all_payments/', tags=['Payments'])
async def get_all_payments(token: str = Header(...)):
    """Получение всех платежей (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    try:
        payments = Payments.select()
        result = []
        for payment in payments:
            booking = Bookings.get_or_none(Bookings.booking_id == payment.booking_id)
            method = PaymentsMethods.get_or_none(PaymentsMethods.id == payment.method)
            status = PaymentStatus.get_or_none(PaymentStatus.id == payment.payment_status)
            result.append({
                'id': payment.id,
                'Номер бронирования': booking.booking_number if booking else None,
                'Сумма': payment.amount,
                'Дата': payment.payment_date,
                'Метод оплаты': method.method_name if method else None,
                'Статус оплаты': status.status_payment if status else None
            })
        return result
    
    except Exception as e:
        raise HTTPException(500, f'Ошибка при получении списка платежей: {e}')

@app.delete('/payments/delete_payment/', tags=['Payments'])
async def delete_payment(payment_id: int, token: str = Header(...)):
    """Удаление платежа (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    try:
        payment = Payments.get_or_none(Payments.id == payment_id)
        if not payment:
            raise HTTPException(404, 'Платеж с указанным ID не найден.')
        
        payment.delete_instance()
        
        return {'message': 'Платеж успешно удален.'}
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(500, f'Ошибка при удалении платежа: {e}')

@app.post('/destinations/create_destination/', tags=['Destinations'])
async def create_destination(data: DestinationCreateSchema, token: str = Header(...)):
    """Создание направления (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    try:
        Destinations.create(
            name=data.name,
            country=data.country,
            description=data.description
        )
        return {'message': 'Направление успешно создано.'}
    
    except HTTPException as http_exc:
        raise http_exc
    
    except Exception as e:
        raise HTTPException(500, f'Ошибка при создании направления: {e}')
            
@app.get('/destinations/get_all/', tags=['Destinations'])
async def get_all_destinations(token: str = Header(...)):
    """Получение всех направлений"""
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    try:
        destinations = Destinations.select()
        return [{
            'id': d.id,
            'Город': d.name,
            'Страна': d.country,
            'Описание': d.description
        } for d in destinations]
        
    except HTTPException as http_exc:
        raise http_exc
    
    except Exception as e:
        raise HTTPException(500, f'Ошибка при получении направлений: {e}')
    
@app.patch('/destinations/update_destination/', tags=['Destinations'])
async def update_destination(destination_id: int, data: DestinationUpdateSchema, token: str = Header(...)):
    """Обновление направления (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    try:
        destination = Destinations.get_or_none(Destinations.id == destination_id)
        if not destination:
            raise HTTPException(404, 'Направление не найдено.')

        if data.name is not None:
            destination.name = data.name
        if data.country is not None:
            destination.country = data.country
        if data.description is not None:
            destination.description = data.description

        destination.save()
        return {'message': 'Направление успешно обновлено.'}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(500, f'Ошибка при обновлении направления: {e}')

@app.delete('/destinations/delete_destination/', tags=['Destinations'])
async def delete_destination(destination_id: int, token: str = Header(...)):
    """Удаление направления (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    try:
        destination = Destinations.get_or_none(Destinations.id == destination_id)
        if not destination:
            raise HTTPException(404, 'Направление не найдено.')
        
        destination.delete_instance()
        
        return {'message': 'Направление успешно удалено.'}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(500, f'Ошибка при удалении направления: {e}')

@app.get('/destinations/search/', tags=['Destinations'])
async def search_destinations(country: Optional[str] = None, city: Optional[str] = None, token: str = Header(...)):
    """Поиск направлений по стране/городу"""
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    try:
        query = Destinations.select()
        if country:
            query = query.where(Destinations.country.ilike(f'%{country}%'))
        if city:
            query = query.where(Destinations.name.ilike(f'%{city}%'))
        destinations = list(query)
        if not destinations:
            raise HTTPException(404, 'Направления по заданным критериям не найдены.')
        
        return [{
            'Город': d.name,
            'Страна': d.country,
            'Описание': d.description
        } for d in destinations]
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(500, f'Ошибка при поиске направлений: {e}')

@app.post('/tour-destinations/create/', tags=['Tour Destinations'])
async def create_tour_destination(data: TourDestinationCreateSchema, token: str = Header(...)):
    """Создание связи тур-направление (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    try:

        tour = Tours.get_or_none(Tours.name == data.tour_name)
        if not tour:
            raise HTTPException(404, 'Тур с указанным названием не найден.')

        destination = Destinations.get_or_none(Destinations.id == data.destination_id)
        if not destination:
            raise HTTPException(404, 'Указанное направление не найдено.')

        existing_link = TourDestinations.get_or_none(
            (TourDestinations.tour_id == tour.id) & 
            (TourDestinations.destinations_id == destination.id)
        )
        if existing_link:
            raise HTTPException(400, 'Такая связь тур-направление уже существует.')

        TourDestinations.create(
            tour_id=tour.id,
            destinations_id=destination.id
        )

        return {'message': 'Связь тур-направление успешно создана.'}
    
    except HTTPException as http_exc:
        raise http_exc
    
    except Exception as e:
        raise HTTPException(500, f'Ошибка при создании связи: {e}')

@app.get('/tour-destinations/all/', tags=['Tour Destinations'])
async def get_all_tour_destinations(token: str = Header(...)):
    """Получение всех связей тур-направление"""
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    try:
        tour_destinations = TourDestinations.select()
        for td in tour_destinations:
            tour = Tours.get_by_id(td.tour_id)
            destination = Destinations.get_by_id(td.destinations_id)
            return [{
                'id': td.id,
                'Название тура': tour.name,
                'Город': destination.name,
                'Страна': destination.country
            }]
    
    except HTTPException as http_exc:
        raise http_exc
        
    except Exception as e:
        raise HTTPException(500, f'Ошибка при получении данных: {e}')
    
@app.get('/tour-destinations/get_by_tour/', tags=['Tour Destinations'])
async def get_destinations_by_tour(tour_name: str, token: str = Header(...)):
    """Получение направлений по названию тура"""
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    try:
        tour = Tours.get_or_none(Tours.name == tour_name)
        if not tour:
            raise HTTPException(404, 'Тур с таким названием не найден.')

        query = (TourDestinations.select().where(TourDestinations.tour_id == tour.id))
        
        result = []
        for td in query:
            destination = Destinations.get_by_id(td.destinations_id)
            
            result.append({
                'id': td.id,
                'Название тура': tour.name,
                'Город': destination.name,
                'Страна': destination.country,
                'Описание': destination.description
            })
        
        if not result:
            return {'message': 'Для этого тура не найдено направлений'}
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f'Ошибка при получении данных: {e}')

@app.put('/tour-destinations/update/', tags=['Tour Destinations'])
async def update_tour_destination(data: TourDestinationUpdateSchema, token: str = Header(...)):
    """Обновление связи тур-направление (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    
    try:
        old_tour = Tours.get_or_none(Tours.name == data.old_tour_name)
        if not old_tour:
            raise HTTPException(404, 'Тур с указанным названием не найден.')

        old_destination = Destinations.get_or_none(Destinations.id == data.old_destination_id)
        if not old_destination:
            raise HTTPException(404, 'Направление с указанным ID не найдено.')

        link = TourDestinations.get_or_none(
            (TourDestinations.tour_id == old_tour.id) & 
            (TourDestinations.destinations_id == old_destination.id)
        )
        if not link:
            raise HTTPException(404, 'Указанная связь тур-направление не найдена.')

        if data.new_tour_name:
            new_tour = Tours.get_or_none(Tours.name == data.new_tour_name)
            if not new_tour:
                raise HTTPException(404, 'Указанного тура не существует.')
            link.tour_id = new_tour.id

        if data.new_destination_id:
            new_destination = Destinations.get_or_none(Destinations.id == data.new_destination_id)
            if not new_destination:
                raise HTTPException(404, 'Указанного города не существует.')
            link.destinations_id = new_destination.id

        link.save()
        return {'message': 'Связь тур-направление успешно обновлена.'}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(500, f'Ошибка при обновлении связи: {e}')

@app.delete('/tour-destinations/delete/', tags=['Tour Destinations'])
async def delete_tour_destination(td_id: int, token: str = Header(...)):
    """Удаление связи тур-направление (только для администратора)"""
    user = get_user_by_token(token, 'Администратор')
    if not user:
        raise HTTPException(401, 'Неверный токен авторизации.')
    try:
        link = TourDestinations.get_or_none(TourDestinations.id == td_id)
        if not link:
            raise HTTPException(404, 'Связь с указанным ID не найдена.')
        link.delete_instance()
        return {'message': 'Связь тур-направление успешно удалена.'}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(500, f'Ошибка при удалении связи: {e}')