import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
from tkinter.font import Font
import os
import re
from PIL import Image, ImageTk
from io import BytesIO
import datetime

os.environ['TCL_LIBRARY'] = r'C:\Users\User\AppData\Local\Programs\Python\Python311\tcl\tcl8.6'
os.environ['TK_LIBRARY'] = r'C:\Users\User\AppData\Local\Programs\Python\Python311\tcl\tk8.6'

class MainApp:
    def __init__(self, root, token):
        self.root = root
        self.token = token
        self.user_data = {}
        self.root.title('AN Travel')
        self.root.geometry('1920x1080')
        self.root.state('zoomed')
        
        self.bg_color = '#f5f5f5'
        self.fg_color = '#333333'
        self.accent_color = '#4a6fa5'
        self.button_fg = '#ffffff'
        self.card_bg = '#ffffff'
        
        self.title_font = Font(family='Helvetica', size=28, weight='bold')
        self.normal_font = Font(family='Arial', size=14)
        self.small_font = Font(family='Arial', size=12)

        if not self.load_user_data():
            messagebox.showerror('Ошибка', 'Не удалось загрузить данные пользователя')
            self.root.destroy()
            return
            
        self.create_top_bar()
        self.create_main_content()
        
    def load_user_data(self):
        try:
            response = requests.get(
                'http://127.0.0.1:8000/users/me/',
                params={'token': self.token},
                timeout=5
            )
            
            if response.status_code == 200:
                self.user_data = response.json()
                return True
            else:
                error = response.json().get('detail', 'Неизвестная ошибка')
                messagebox.showerror('Ошибка', f'Ошибка загрузки данных: {error}')
                return False
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Не удалось подключиться к серверу: {e}')
            return False
        
    def create_top_bar(self):
        self.top_bar = tk.Frame(self.root, bg=self.accent_color, height=60)
        self.top_bar.pack(fill='x', side='top')
        
        self.title_label = tk.Label(
            self.top_bar, 
            text='AN Travel', 
            font=self.title_font,
            bg=self.accent_color,
            fg=self.button_fg
        )
        self.title_label.pack(side='left', padx=20)

        button_frame = tk.Frame(self.top_bar, bg=self.accent_color)
        button_frame.pack(side='right', padx=20)

        self.bookings_btn = ttk.Button(
            button_frame,
            text='Мои заявки',
            command=self.show_my_bookings,
            style='TButton'
        )
        self.bookings_btn.pack(side='left', padx=10)
        
        self.profile_btn = ttk.Button(
            button_frame,
            text='Мой профиль',
            command=self.show_profile,
            style='TButton'
        )
        self.profile_btn.pack(side='left', padx=10)
        
        button_frame = tk.Frame(self.top_bar, bg=self.accent_color)
        button_frame.pack(side="right", padx=10)

        self.destinations_btn = ttk.Button(
            button_frame,
            text="Направления",
            command=self.show_destinations,
            style="TButton"
        )
        self.destinations_btn.pack(side="left", padx=10)
        
    def create_main_content(self):
        self.main_frame = tk.Frame(self.root, bg=self.bg_color)
        self.main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        if not self.user_data:
            messagebox.showerror('Ошибка', 'Данные пользователя не загружены')
            self.root.destroy()
            return
            
        if self.user_data.get('role') == 'Администратор':
            self.create_admin_content()
        else:
            self.create_user_content()

    def create_user_content(self):
        welcome_label = tk.Label(
            self.main_frame,
            text=f"Добро пожаловать, {self.user_data.get('full_name', 'Пользователь')}!",
            font=self.title_font,
            bg=self.bg_color,
            fg=self.fg_color
        )
        welcome_label.pack(pady=20)

        tours_header = tk.Label(
            self.main_frame,
            text='Доступные туры:',
            font=self.normal_font,
            bg=self.bg_color,
            fg=self.fg_color
        )
        tours_header.pack(anchor='w', padx=20)

        container = tk.Frame(self.main_frame, bg=self.bg_color)
        container.pack(fill='both', expand=True, padx=20, pady=10)

        canvas = tk.Canvas(container, bg=self.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient='vertical', command=canvas.yview)

        self.tours_frame = tk.Frame(canvas, bg=self.bg_color)
        self.tours_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )
        canvas.create_window((0, 0), window=self.tours_frame, anchor='nw', width=canvas.winfo_width())
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        
        def update_frame_width(event):
            canvas.itemconfig('all', width=event.width)
        
        canvas.bind('<Configure>', update_frame_width)
        
        canvas.bind_all('<MouseWheel>', lambda event: canvas.yview_scroll(int(-1*(event.delta/120)), 'units'))
        
        try:
            response = requests.get(
                'http://127.0.0.1:8000/tours/get_tours/',
                headers={'token': self.token},
                timeout=5
            )
            
            if response.status_code == 200:
                tours = response.json()
                for tour in tours:
                    self.create_tour_card(self.tours_frame, tour)
            else:
                error = response.json().get('detail', 'Неизвестная ошибка')
                messagebox.showerror('Ошибка', f'Не удалось загрузить туры: {error}')
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Ошибка соединения: {e}')

    def create_tour_card(self, parent, tour):
        tour_card = tk.Frame(
            parent,
            bg=self.card_bg,
            bd=2,
            relief='groove',
            padx=10,
            pady=10
        )
        tour_card.pack(fill='x', pady=5, expand=True)
        

        content_frame = tk.Frame(tour_card, bg=self.card_bg)
        content_frame.pack(fill='x', expand=True)

        image_frame = tk.Frame(content_frame, bg=self.card_bg)
        image_frame.pack(side='left', padx=(0, 15))
        
        if tour.get('image_url'):
            try:
                response = requests.get(f"http://127.0.0.1:8000{tour['image_url']}")
                if response.status_code == 200:
                    image_data = BytesIO(response.content)
                    image = Image.open(image_data)
                    image = image.resize((200, 150), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(image)
                    
                    image_label = tk.Label(image_frame, image=photo, bg=self.card_bg)
                    image_label.image = photo
                    image_label.pack()
                else:
                    tk.Label(image_frame, 
                            text='Изображение не найдено', 
                            bg=self.card_bg).pack()
            except Exception as e:
                tk.Label(image_frame, 
                        text=f'Ошибка загрузки: {str(e)}', 
                        bg=self.card_bg).pack()
        else:
            tk.Label(image_frame, 
                    text='Нет изображения', 
                    bg=self.card_bg).pack()
        
        info_frame = tk.Frame(content_frame, bg=self.card_bg)
        info_frame.pack(side='left', fill='x', expand=True)
        
        fields = [
            ('Тур', 'name'),
            ('Описание', 'description'),
            ('Цена (1 чел.)', 'price'),
            ('Длительность (в днях)', 'days'),
            ('Страна', 'country')
        ]
        
        for label, key in fields:
            value = tour.get(key)
            if value:
                tk.Label(
                    info_frame,
                    text=f'{label}: {value}',
                    font=self.small_font,
                    bg=self.card_bg,
                    anchor='w',
                    justify='left'
                ).pack(anchor='w', fill='x', pady=2)
                
        btn_frame = tk.Frame(tour_card, bg=self.card_bg)
        btn_frame.pack(anchor='e', pady=5)
        
        ttk.Button(
            tour_card,
            text='Забронировать',
            command=lambda t=tour: self.book_tour(t),
            style='TButton'
        ).pack(anchor='e', pady=5)
        
        ttk.Button(
        tour_card,
        text='Направления тура',
        command=lambda t=tour: self.show_tour_destinations(t),
        style='TButton'
        ).pack(anchor='e', pady=5)

    def book_tour(self, tour):
        booking_window = tk.Toplevel(self.root)
        booking_window.title(f"Бронирование тура: {tour['name']}")
        booking_window.geometry('800x500')
        booking_window.resizable(False, False)

        frame = tk.Frame(booking_window, padx=20, pady=20)
        frame.pack(fill='both', expand=True)

        tk.Label(
            frame,
            text=f"Бронирование тура: {tour['name']}",
            font=self.title_font
        ).pack(pady=10)

        tour_info_frame = tk.Frame(frame)
        tour_info_frame.pack(fill='x', pady=10)
        
        tk.Label(
            tour_info_frame,
            text='Информация о туре:',
            font=self.normal_font,
            justify='left'
        ).pack(anchor='w')
        
        info_text = (
            f"Страна: {tour['country']}\n"
            f"Длительность: {tour['days']} дней\n"
            f"Цена (1 чел.): {tour['price']} руб.\n"
            f"Описание: {tour['description']}"
        )
        
        tk.Label(
            tour_info_frame,
            text=info_text,
            font=self.small_font,
            justify='left',
            anchor='w'
        ).pack(anchor='w', padx=20)

        form_frame = tk.Frame(frame)
        form_frame.pack(fill='x', pady=10)

        tk.Label(
            form_frame,
            text='Дата рождения (ГГГГ-ММ-ДД):',
            font=self.normal_font
        ).pack(anchor='w', pady=5)
        
        birthday_entry = ttk.Entry(form_frame, width=20, font=self.normal_font)
        birthday_entry.pack(anchor='w', fill='x', pady=5)

        tk.Label(
            form_frame,
            text='Количество человек:',
            font=self.normal_font
        ).pack(anchor='w', pady=5)
        
        people_var = tk.IntVar(value=1)
        people_spinbox = ttk.Spinbox(
            form_frame,
            from_=1,
            to=10,
            textvariable=people_var,
            width=5,
            font=self.normal_font
        )
        people_spinbox.pack(anchor='w', pady=5)
        
        def submit_booking():
            birthday = birthday_entry.get()
            people = people_var.get()
            
            if not birthday or not re.match(r'\d{4}-\d{2}-\d{2}', birthday):
                messagebox.showerror('Ошибка', 'Некорректный формат даты рождения. Используйте ГГГГ-ММ-ДД')
                return
            
            try:
                response = requests.post(
                    'http://127.0.0.1:8000/booking/create_booking/',
                    headers={'token': self.token},
                    json={
                        'birthday': birthday,
                        'tour_name': tour['name'],
                        'number_of_people': people
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    messagebox.showinfo(
                        'Успех', 
                        f"Бронирование успешно оформлено!\nНомер заявки: {result.get('Номер заявки', '')}"
                    )
                    booking_window.destroy()
                else:
                    error = response.json().get('detail', 'Неизвестная ошибка')
                    messagebox.showerror('Ошибка', f'Не удалось оформить бронирование: {error}')
                    
            except requests.exceptions.RequestException as e:
                messagebox.showerror('Ошибка', f'Не удалось подключиться к серверу: {e}')
        
        ttk.Button(
            frame,
            text='Забронировать',
            command=submit_booking,
            style='TButton'
        ).pack(pady=20)

    def create_admin_content(self):
        welcome_label = tk.Label(
            self.main_frame,
            text='Панель администратора',
            font=self.title_font,
            bg=self.bg_color,
            fg=self.fg_color
        )
        welcome_label.pack(pady=20)
        
        admin_btn_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        admin_btn_frame.pack(pady=20)
        
        buttons = [
            ('Управление турами', self.show_tours_management),
            ('Управление пользователями', self.show_users_management),
            ('Статусы бронирования', self.show_booking_statuses_management),
            ('Бронирования', self.show_bookings_management)
        ]
        
        for text, command in buttons:
            ttk.Button(
                admin_btn_frame,
                text=text,
                command=command,
                style='TButton'
            ).pack(side='left', padx=10)

    def show_profile(self):
        if not self.load_user_data():
            messagebox.showerror('Ошибка', 'Не удалось обновить данные профиля')
            return
            
        profile_window = tk.Toplevel(self.root)
        profile_window.title('Мой профиль')
        profile_window.geometry('600x500')
        profile_window.resizable(False, False)
        
        profile_frame = tk.Frame(profile_window, padx=20, pady=20)
        profile_frame.pack(fill='both', expand=True)
        
        tk.Label(
            profile_frame,
            text='Личные данные',
            font=self.title_font
        ).pack(pady=10)
        
        info_frame = tk.Frame(profile_frame)
        info_frame.pack(fill='x', pady=10)

        fields = [
            ('ФИО', 'full_name'),
            ('Email', 'email'),
            ('Телефон', 'number_phone'),
            ('Роль', 'role')
        ]
        
        for label, key in fields:
            tk.Label(
                info_frame,
                text=f"{label}: {self.user_data.get(key, 'Не указано')}",
                font=self.normal_font
            ).pack(anchor='w', pady=5)
        
        btn_frame = tk.Frame(profile_frame)
        btn_frame.pack(pady=20)
        
        buttons = [
            ('Изменить пароль', self.show_change_password),
            ('Удалить аккаунт', self.delete_account)
        ]
        
        for text, command in buttons:
            ttk.Button(
                btn_frame,
                text=text,
                command=command,
                style='TButton'
            ).pack(side='left', padx=10)

    def show_change_password(self):
        change_pass_window = tk.Toplevel(self.root)
        change_pass_window.title('Смена пароля')
        change_pass_window.geometry('400x300')
        
        tk.Label(
            change_pass_window,
            text='Введите email для смены пароля:',
            font=self.normal_font
        ).pack(pady=10)
        
        email_entry = ttk.Entry(change_pass_window, width=30, font=self.normal_font)
        email_entry.pack(pady=10)
        email_entry.insert(0, self.user_data.get('email', ''))
        
        ttk.Button(
            change_pass_window,
            text='Отправить код подтверждения',
            command=lambda: self.send_password_code(email_entry.get()),
            style='TButton'
        ).pack(pady=20)

    def send_password_code(self, email):
        if not email:
            messagebox.showerror('Ошибка', 'Введите email')
            return
            
        try:
            response = requests.post(
                'http://127.0.0.1:8000/users/change_password/',
                params={'email': email},
                timeout=5
            )
            
            if response.status_code == 200:
                messagebox.showinfo('Успех', 'Код подтверждения отправлен на ваш email')
            else:
                error = response.json().get('detail', 'Ошибка отправки кода')
                messagebox.showerror('Ошибка', error)
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Не удалось подключиться к серверу: {e}')

    def delete_account(self):
        
        if not messagebox.askyesno('Подтверждение', 'Вы уверены, что хотите удалить аккаунт?'):
            return
            
        try:
            response = requests.delete(
                'http://127.0.0.1:8000/users/delete_profile/',
                headers={'token': self.token},
                timeout=5
            )
            
            if response.status_code == 200:
                messagebox.showinfo('Успех', 'Аккаунт успешно удален')
                self.root.destroy()
            else:
                error = response.json().get('detail', 'Ошибка удаления аккаунта')
                messagebox.showerror('Ошибка', error)
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Не удалось подключиться к серверу: {e}')

    def show_my_bookings(self):
        if not self.load_user_data():
            messagebox.showerror('Ошибка', 'Не удалось обновить данные профиля')
            return
            
        email = self.user_data.get('email')
        if not email:
            messagebox.showerror('Ошибка', 'Email пользователя не найден')
            return
            
        try:
            response = requests.get(
                'http://127.0.0.1:8000/booking/get_booking_by_user/',
                params={'email': email},
                headers={'token': self.token},
                timeout=5
            )
            
            if response.status_code == 200:
                bookings = response.json()
                self.display_bookings(bookings)
            else:
                error = response.json().get('detail', 'Неизвестная ошибка')
                messagebox.showerror('Ошибка', f'Не удалось загрузить заявки: {error}')
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Не удалось подключиться к серверу: {e}')
    
    def get_selected_booking_number(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning('Предупреждение', 'Выберите заявку из списка')
            return None
            
        item = self.tree.item(selected_item[0])
        return item['values'][0]

    def edit_selected_booking(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning('Предупреждение', 'Выберите заявку из списка')
            return
        item = self.tree.item(selected_item[0])
        booking_number = item['values'][0]
        self.edit_booking(booking_number)

    def delete_selected_booking(self):
        booking_number = self.get_selected_booking_number()
        if booking_number:
            self.delete_booking(booking_number)
                
    def edit_booking(self, booking_number):
    
        booking_data = None
        for booking in self.bookings_data:
            if booking.get('Номер заявки:') == booking_number:
                booking_data = booking
                break
        
        if not booking_data:
            messagebox.showerror('Ошибка', 'Данные заявки не найдены')
            return
            
        self.open_edit_window(booking_data)

    def open_edit_window(self, booking_data):
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"Редактирование заявки {booking_data['Номер заявки:']}")
        edit_window.geometry('500x400')
        
        frame = tk.Frame(edit_window, padx=20, pady=20)
        frame.pack(fill='both', expand=True)
        tk.Label(frame, text='Дата рождения (ГГГГ-ММ-ДД):', font=self.normal_font).pack(anchor='w', pady=5)
        birthday_var = tk.StringVar(value=booking_data.get('Дата рождения:', ''))
        birthday_entry = ttk.Entry(frame, textvariable=birthday_var, width=20, font=self.normal_font)
        birthday_entry.pack(fill='x', pady=5)
        tk.Label(frame, text='Количество человек:', font=self.normal_font).pack(anchor='w', pady=5)
        try:
            current_people = int(booking_data.get('Количество человек:', 1))
        except:
            current_people = 1

        people_var = tk.IntVar(value=current_people)
        people_spinbox = ttk.Spinbox(
            frame,
            from_=1,
            to=10,
            textvariable=people_var,
            width=5,
            font=self.normal_font
        )
        people_spinbox.pack(anchor='w', pady=5)

        def save_changes():
            birthday = birthday_var.get()
            if not re.match(r'\d{4}-\d{2}-\d{2}', birthday):
                messagebox.showerror('Ошибка', 'Некорректный формат даты рождения. Используйте ГГГГ-ММ-ДД')
                return

            try:
                response = requests.put(
                    'http://127.0.0.1:8000/booking/update_booking/',
                    headers={
                        'token': self.token,
                        'Content-Type': 'application/json'
                    },
                    params={'booking_number': booking_data['Номер заявки:']},
                    json={
                        'birthday': birthday,
                        'number_of_people': people_var.get()
                    }
                )
                
                if response.status_code == 200:
                    messagebox.showinfo('Успех', 'Заявка успешно обновлена!')
                    edit_window.destroy()
                    if hasattr(self, 'bookings_window') and self.bookings_window.winfo_exists():
                        self.bookings_window.destroy()
                    self.show_my_bookings()
                else:
                    try:
                        error_detail = response.json().get('detail', 'Неизвестная ошибка')
                        messagebox.showerror('Ошибка', f'Не удалось обновить заявку: {error_detail}')
                    except:
                        messagebox.showerror('Ошибка', f'Ошибка сервера: {response.status_code} - {response.text}')
                    
            except requests.exceptions.RequestException as e:
                messagebox.showerror('Ошибка', f'Не удалось подключиться к серверу: {e}')

        ttk.Button(
            frame,
            text='Сохранить изменения',
            command=save_changes,
            style='TButton'
        ).pack(pady=20)

    def delete_booking(self, booking_number):
        if not messagebox.askyesno('Подтверждение', 'Вы уверены, что хотите удалить эту заявку?'):
            return
            
        try:
            response = requests.delete(
                'http://127.0.0.1:8000/booking/delete_booking/',
                headers={'token': self.token},
                params={'booking_number': booking_number}
            )
            
            if response.status_code == 200:
                messagebox.showinfo('Успех', 'Заявка успешно удалена!')
                if hasattr(self, 'bookings_window') and self.bookings_window.winfo_exists():
                    self.bookings_window.destroy()
                self.show_my_bookings()
            else:
                error = response.json().get('detail', 'Неизвестная ошибка')
                messagebox.showerror('Ошибка', f'Не удалось удалить заявку: {error}')
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Не удалось подключиться к серверу: {e}')

    def display_bookings(self, bookings):
        self.bookings_window = tk.Toplevel(self.root)
        self.bookings_window.title('Мои заявки')
        self.bookings_window.geometry('1000x800')
        
        tk.Label(
            self.bookings_window,
            text='Мои заявки на бронирование',
            font=self.title_font,
            pady=10
        ).pack(fill='x')

        container = tk.Frame(self.bookings_window)
        container.pack(fill='both', expand=True, padx=20, pady=10)

        columns = ('Номер заявки', 'Тур', 'Дата бронирования', 'Статус', 'Количество человек', 'Дата рождения')
        self.tree = ttk.Treeview(container, columns=columns, show='headings', selectmode='browse')
        
        self.tree.column('Номер заявки', width=120, anchor='center')
        self.tree.column('Тур', width=200, anchor='w')
        self.tree.column('Дата бронирования', width=150, anchor='center')
        self.tree.column('Статус', width=150, anchor='center')
        self.tree.column('Количество человек', width=150, anchor='center')
        self.tree.column('Дата рождения', width=120, anchor='center')

        for col in columns:
            self.tree.heading(col, text=col)

        self.bookings_data = []
        for booking in bookings:
            self.bookings_data.append(booking)
            self.tree.insert('', 'end', values=(
                booking.get('Номер заявки:'),
                booking.get('Название тура:'),
                booking.get('Дата бронирования:'),
                booking.get('Статус:'),
                booking.get('Количество человек:'),
                booking.get('Дата рождения:')
                ))
        scrollbar = ttk.Scrollbar(container, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        button_frame = tk.Frame(self.bookings_window)
        button_frame.pack(pady=10)

        self.edit_btn = ttk.Button(
            button_frame,
            text='Редактировать выбранную заявку',
            command=self.edit_selected_booking,
            style='TButton'
        )
        self.edit_btn.pack(side='left', padx=10)
        self.delete_btn = ttk.Button(
            button_frame,
            text='Удалить выбранную заявку',
            command=self.delete_selected_booking,
            style='TButton'
        )
        self.delete_btn.pack(side='left', padx=10)

        status_label = tk.Label(
            self.bookings_window,
            text=f'Найдено заявок: {len(bookings)}',
            font=self.small_font,
            pady=10
        )
        status_label.pack(side='bottom')
        
        self.pay_btn = ttk.Button(
            button_frame,
            text='Оплатить выбранную заявку',
            command=self.pay_selected_booking,
            style='TButton'
        )
        self.pay_btn.pack(side='left', padx=10)
        self.tree.bind('<<TreeviewSelect>>', self.on_booking_select)
    def on_booking_select(self, event):
        
        selected_item = self.tree.selection()
        if not selected_item:
            return
            
        item = self.tree.item(selected_item[0])
        status = item['values'][3]
        
        if status == 'Оплачено':
            self.edit_btn.config(state='disabled')
        else:
            self.edit_btn.config(state='normal')

        if status == 'Ожидает оплаты':
            self.pay_btn.config(state='normal')
        else:
            self.pay_btn.config(state='disabled')
    
    def pay_selected_booking(self):
        booking_number = self.get_selected_booking_number()
        if booking_number:
            self.open_payment_window(booking_number)
    
    def open_payment_window(self, booking_number):
        payment_window = tk.Toplevel(self.root)
        payment_window.title(f'Оплата заявки {booking_number}')
        payment_window.geometry('600x500')
        payment_window.resizable(False, False)
        payment_window.grab_set()

        tk.Label(
            payment_window,
            text=f'Оплата заявки #{booking_number}',
            font=self.title_font
        ).pack(pady=10)

        form_frame = tk.Frame(payment_window, padx=20, pady=10)
        form_frame.pack(fill='both', expand=True)

        fields = [
            ('Номер карты (16 цифр):', 'card_number', r'^\d{16}$'),
            ('Держатель карты:', 'card_holder', r'^[A-Za-zА-Яа-яЁё\s]+$'),
            ('Срок действия (ММ/ГГ):', 'expiry_date', r'^\d{2}/\d{2}$'),
            ('CVV код:', 'cvv', r'^\d{3}$')
        ]
        
        self.card_entries = {}
        for i, (label, field, pattern) in enumerate(fields):
            tk.Label(form_frame, text=label, font=self.normal_font).grid(row=i, column=0, sticky='w', pady=5)
            entry = ttk.Entry(form_frame, width=25, font=self.normal_font)
            entry.grid(row=i, column=1, pady=5, padx=10)
            self.card_entries[field] = (entry, pattern)

            if field == 'expiry_date':
                entry.insert(0, 'ММ/ГГ')
                entry.bind('<FocusIn>', lambda e: self.clear_placeholder(e, 'ММ/ГГ'))
                entry.bind('<KeyRelease>', self.format_expiry_date)
    
        btn_frame = tk.Frame(payment_window)
        btn_frame.pack(pady=10)
        
        ttk.Button(
            btn_frame,
            text='Оплатить',
            command=lambda: self.process_payment(booking_number, payment_window),
            style='TButton'
        ).pack(side='left', padx=10)
        
        ttk.Button(
            btn_frame,
            text='Отмена',
            command=payment_window.destroy,
            style='TButton'
        ).pack(side='left', padx=10)
    
    def clear_placeholder(self, event, placeholder):
        if event.widget.get() == placeholder:
            event.widget.delete(0, tk.END)
    
    def format_expiry_date(self, event):
        text = event.widget.get().replace('/', '')
        if len(text) >= 2:
            formatted = text[:2] + '/' + text[2:4]
            event.widget.delete(0, tk.END)
            event.widget.insert(0, formatted)
    
    def validate_card_data(self):
        errors = []
        card_data = {}
        
        for field, (entry, pattern) in self.card_entries.items():
            value = entry.get().strip()
            
            if field == 'expiry_date' and value == 'ММ/ГГ':
                value = ''
            
            if not value:
                errors.append(f"Поле '{field.split('_')[0]}' не заполнено")
                continue
            
            if not re.match(pattern, value):
                errors.append(f"Некорректное значение для {field.split('_')[0]}")
                continue
            
            card_data[field] = value

        if 'expiry_date' in card_data:
            try:
                month, year = card_data['expiry_date'].split('/')
                current_year = datetime.datetime.now().year % 100
                current_month = datetime.datetime.now().month
                
                if int(year) < current_year or (int(year) == current_year and int(month) < current_month):
                    errors.append('Срок действия карты истек')
            except:
                errors.append('Неверный формат срока действия карты')
        
        return card_data, errors
    
    def process_payment(self, booking_number, window):
        
        card_data, errors = self.validate_card_data()
        
        if errors:
            messagebox.showerror('Ошибка', '\n'.join(errors))
            return
        
        try:
            response = requests.post(
                'http://127.0.0.1:8000/payments/add_payment/',
                headers={'token': self.token},
                json={
                    'booking_number': booking_number,
                    'method_name': 'Банковская карта',
                    'payment_status_name': 'Оплачено'
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                messagebox.showinfo(
                    'Успех', 
                    f"Оплата прошла успешно!\nСумма: {result.get('amount', 0)} руб."
                )
                window.destroy()
                
                if hasattr(self, 'bookings_window') and self.bookings_window.winfo_exists():
                    self.bookings_window.destroy()
                self.show_my_bookings()
            else:
                error = response.json().get('detail', 'Ошибка оплаты')
                messagebox.showerror('Ошибка', error)
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Не удалось подключиться к серверу: {e}')
            
    def show_destinations(self):
        dest_window = tk.Toplevel(self.root)
        dest_window.title('Направления туров')
        dest_window.geometry('800x600')
        
        search_frame = tk.Frame(dest_window, padx=10, pady=10)
        search_frame.pack(fill='x')
        
        tk.Label(search_frame, text='Страна:').grid(row=0, column=0, padx=5)
        self.country_entry = ttk.Entry(search_frame, width=20)
        self.country_entry.grid(row=0, column=1, padx=5)
        
        tk.Label(search_frame, text='Город:').grid(row=0, column=2, padx=5)
        self.city_entry = ttk.Entry(search_frame, width=20)
        self.city_entry.grid(row=0, column=3, padx=5)
        
        search_btn = ttk.Button(
            search_frame,
            text='Найти',
            command=self.search_destinations,
            style='TButton'
        )
        search_btn.grid(row=0, column=4, padx=10)

        columns = ('Город', 'Страна', 'Описание')
        self.dest_tree = ttk.Treeview(dest_window, columns=columns, show='headings')
        self.dest_tree.pack(fill='both', expand=True, padx=10, pady=10)
        
        for col in columns:
            self.dest_tree.heading(col, text=col)
            self.dest_tree.column(col, width=100, anchor='w')

        self.search_destinations()

    def search_destinations(self):
        for item in self.dest_tree.get_children():
            self.dest_tree.delete(item)
        
        country = self.country_entry.get().strip()
        city = self.city_entry.get().strip()
        
        try:
            response = requests.get(
                'http://127.0.0.1:8000/destinations/search/',
                headers={'token': self.token},
                params={
                    'country': country if country else None,
                    'city': city if city else None
                },
                timeout=5
            )
            
            if response.status_code == 200:
                destinations = response.json()
                for dest in destinations:
                    self.dest_tree.insert('', 'end', values=(
                        dest.get('Город'),
                        dest.get('Страна'),
                        dest.get('Описание')
                    ))
            else:
                error = response.json().get('detail', 'Неизвестная ошибка')
                messagebox.showerror('Ошибка', f'Не удалось загрузить направления: {error}')
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Ошибка соединения: {e}')
            
    def display_destinations_for_tour(self, tour_name, destinations):
        dest_window = tk.Toplevel(self.root)
        dest_window.title(f'Направления тура: {tour_name}')
        dest_window.geometry('800x600')
        
        tk.Label(
            dest_window,
            text=f'Направления тура: {tour_name}',
            font=self.title_font
        ).pack(pady=10)

        if not destinations or not isinstance(destinations, list):
            tk.Label(dest_window, text='Для этого тура не найдено направлений').pack()
            return

        columns = ('Город', 'Страна', 'Описание')
        tree = ttk.Treeview(dest_window, columns=columns, show='headings')
        tree.pack(fill='both', expand=True, padx=10, pady=10)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor='w')

        for dest in destinations:
            if isinstance(dest, dict):
                tree.insert('', 'end', values=(
                    dest.get('Город', ''),
                    dest.get('Страна', ''),
                    dest.get('Описание', '')
                ))
            else:
                tree.insert('', 'end', values=('', '', dest))
        
        scrollbar = ttk.Scrollbar(dest_window, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
    
    def show_tour_destinations(self, tour):
        try:
            response = requests.get(
                'http://127.0.0.1:8000/tour-destinations/get_by_tour/',
                headers={'token': self.token},
                params={'tour_name': tour['name']},
                timeout=5
            )
            
            if response.status_code == 200:
                destinations = response.json()
                if isinstance(destinations, dict) and 'message' in destinations:
                    self.display_destinations_for_tour(tour['name'], [])
                else:
                    self.display_destinations_for_tour(tour['name'], destinations)
            else:
                error = response.json().get('detail', 'Неизвестная ошибка')
                messagebox.showerror('Ошибка', f'Не удалось загрузить направления: {error}')
        
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Ошибка соединения: {e}')
            
    def load_users(self):
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        
        try:
            response = requests.get(
                'http://127.0.0.1:8000/users/get_all/',
                headers={'token': self.token},
                timeout=5
            )
            
            if response.status_code == 200:
                users = response.json()
                for user in users:
                    self.users_tree.insert('', 'end', values=(
                        user['id'],
                        user['email'],
                        user['full_name'],
                        user['number_phone'],
                        user['role']
                    ))
            else:
                error = response.json().get('detail', 'Неизвестная ошибка')
                messagebox.showerror('Ошибка', f'Не удалось загрузить пользователей: {error}')
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Ошибка соединения: {e}')
        
    def show_users_management(self):
        users_window = tk.Toplevel(self.root)
        users_window.title('Управление пользователями')
        users_window.geometry('1200x800')

        tk.Label(
            users_window,
            text='Управление пользователями',
            font=self.title_font
        ).pack(pady=10)

        columns = ('id', 'email', 'full_name', 'number_phone', 'role')
        self.users_tree = ttk.Treeview(users_window, columns=columns, show='headings')
        self.users_tree.pack(fill='both', expand=True, padx=10, pady=10)
    
        self.users_tree.heading('id', text='ID')
        self.users_tree.heading('email', text='Email')
        self.users_tree.heading('full_name', text='ФИО')
        self.users_tree.heading('number_phone', text='Телефон')
        self.users_tree.heading('role', text='Роль')
        
        self.users_tree.column('id', width=50, anchor='center')
        self.users_tree.column('email', width=200, anchor='w')
        self.users_tree.column('full_name', width=200, anchor='w')
        self.users_tree.column('number_phone', width=150, anchor='w')
        self.users_tree.column('role', width=150, anchor='w')

        btn_frame = tk.Frame(users_window)
        btn_frame.pack(pady=10)
        
        ttk.Button(
            btn_frame,
            text='Изменить роль',
            command=self.change_user_role,
            style='TButton'
        ).pack(side='left', padx=10)
        
        ttk.Button(
            btn_frame,
            text='Удалить пользователя',
            command=self.delete_user,
            style='TButton'
        ).pack(side='left', padx=10)

        self.load_users()
    
    def change_user_role(self):
        selected = self.users_tree.selection()
        if not selected:
            messagebox.showwarning('Предупреждение', 'Выберите пользователя')
            return
            
        user_id = self.users_tree.item(selected[0])['values'][0]
        current_role = self.users_tree.item(selected[0])['values'][4]
        
        role_window = tk.Toplevel(self.root)
        role_window.title('Изменение роли')
        role_window.geometry('300x200')
        
        tk.Label(role_window, text='Новая роль:').pack(pady=10)
        
        role_var = tk.StringVar(value=current_role)
        roles = ['Пользователь', 'Администратор']
        role_combobox = ttk.Combobox(role_window, textvariable=role_var, values=roles, state='readonly')
        role_combobox.pack(pady=10)
        
        def save_role():
            new_role = role_var.get()
            if new_role == current_role:
                messagebox.showinfo('Информация', 'Роль не изменена')
                role_window.destroy()
                return
                
            try:
                response = requests.post(
                    'http://127.0.0.1:8000/users/set_role/',
                    headers={'token': self.token},
                    json={
                        'email': self.users_tree.item(selected[0])['values'][1],
                        'new_role': new_role
                    }
                )
                
                if response.status_code == 200:
                    messagebox.showinfo('Успех', 'Роль пользователя изменена')
                    role_window.destroy()
                    self.load_users()
                else:
                    error = response.json().get('detail', 'Ошибка')
                    messagebox.showerror('Ошибка', error)
                    
            except requests.exceptions.RequestException as e:
                messagebox.showerror('Ошибка', f'Ошибка соединения: {e}')
        
        ttk.Button(
            role_window,
            text='Сохранить',
            command=save_role,
            style='TButton'
        ).pack(pady=10)
    
    def delete_user(self):
        selected = self.users_tree.selection()
        if not selected:
            messagebox.showwarning('Предупреждение', 'Выберите пользователя')
            return
            
        user_id = self.users_tree.item(selected[0])['values'][0]
        email = self.users_tree.item(selected[0])['values'][1]
        
        if not messagebox.askyesno('Подтверждение', f'Удалить пользователя {email}?'):
            return
            
        try:
            response = requests.delete(
                'http://127.0.0.1:8000/users/delete_admin_user/',
                headers={'token': self.token},
                params={'user_id': user_id}
            )
            
            if response.status_code == 200:
                messagebox.showinfo('Успех', 'Пользователь удален')
                self.load_users()
            else:
                error = response.json().get('detail', 'Ошибка')
                messagebox.showerror('Ошибка', error)
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Ошибка соединения: {e}')
            
    def load_tours(self):
        if not hasattr(self, 'tours_window') or not self.tours_window.winfo_exists():
            return

        for item in self.tours_tree.get_children():
            self.tours_tree.delete(item)
        
        try:
            response = requests.get(
                'http://127.0.0.1:8000/tours/get_tours/',
                headers={'token': self.token},
                timeout=5
            )
            
            if response.status_code == 200:
                tours = response.json()
                for tour in tours:
                    self.tours_tree.insert('', 'end', values=(
                        tour['id'],
                        tour['name'],
                        tour['description'],
                        tour['price'],
                        tour['days'],
                        tour['country'],
                        tour['image_url'] if 'image_url' in tour else ''
                    ))
            else:
                error = response.json().get('detail', 'Неизвестная ошибка')
                messagebox.showerror('Ошибка', f'Не удалось загрузить туры: {error}')
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Ошибка соединения: {e}')

    def show_tours_management(self):
        if hasattr(self, 'tours_window') and self.tours_window.winfo_exists():
            self.tours_window.lift()
            return
            
        self.tours_window = tk.Toplevel(self.root)
        self.tours_window.title('Управление турами')
        self.tours_window.geometry('1200x800')
        self.tours_window.protocol("WM_DELETE_WINDOW", self.on_tours_window_close)

        tk.Label(
            self.tours_window,
            text='Управление турами',
            font=self.title_font
        ).pack(pady=10)

        add_button = ttk.Button(
            self.tours_window,
            text='Добавить тур',
            command=self.add_tour_dialog,
            style='TButton'
        )
        add_button.pack(anchor='ne', padx=20, pady=10)

        columns = ('id', 'name', 'description', 'price', 'days', 'country', 'image')
        self.tours_tree = ttk.Treeview(self.tours_window, columns=columns, show='headings')

        self.tours_tree.heading('id', text='ID')
        self.tours_tree.heading('name', text='Название')
        self.tours_tree.heading('description', text='Описание')
        self.tours_tree.heading('price', text='Цена')
        self.tours_tree.heading('days', text='Дней')
        self.tours_tree.heading('country', text='Страна')
        self.tours_tree.heading('image', text='Изображение')
        
        self.tours_tree.column('id', width=50, anchor='center')
        self.tours_tree.column('name', width=200, anchor='w')
        self.tours_tree.column('description', width=300, anchor='w')
        self.tours_tree.column('price', width=100, anchor='center')
        self.tours_tree.column('days', width=80, anchor='center')
        self.tours_tree.column('country', width=150, anchor='w')
        self.tours_tree.column('image', width=200, anchor='w')
        
        scrollbar = ttk.Scrollbar(self.tours_window, orient='vertical', command=self.tours_tree.yview)
        self.tours_tree.configure(yscrollcommand=scrollbar.set)
        
        self.tours_tree.pack(fill='both', expand=True, padx=20, pady=10)
        scrollbar.pack(side='right', fill='y')

        btn_frame = tk.Frame(self.tours_window)
        btn_frame.pack(pady=10)
        
        edit_btn = ttk.Button(
            btn_frame,
            text='Редактировать',
            command=self.edit_tour_dialog,
            style='TButton'
        )
        edit_btn.pack(side='left', padx=10)
        
        delete_btn = ttk.Button(
            btn_frame,
            text='Удалить',
            command=self.delete_tour,
            style='TButton'
        )
        delete_btn.pack(side='left', padx=10)
        
        refresh_btn = ttk.Button(
            btn_frame,
            text='Обновить',
            command=self.load_tours,
            style='TButton'
        )
        refresh_btn.pack(side='left', padx=10)

        self.load_tours()
    
    def on_tours_window_close(self):
        self.tours_window.destroy()
        if hasattr(self, 'tours_tree'):
            del self.tours_tree
        if hasattr(self, 'tours_window'):
            del self.tours_window
        
    def add_tour_dialog(self):
        self.tour_dialog = tk.Toplevel(self.root)
        self.tour_dialog.title('Добавление нового тура')
        self.tour_dialog.geometry('600x500')
        
        fields = [
            ('Название тура:', 'name'),
            ('Описание:', 'description'),
            ('Цена:', 'price'),
            ('Длительность (дней):', 'days'),
            ('Страна:', 'country')
        ]
        
        self.tour_entries = {}
        for i, (label, field) in enumerate(fields):
            tk.Label(self.tour_dialog, text=label).grid(row=i, column=0, padx=10, pady=5, sticky='e')
            entry = ttk.Entry(self.tour_dialog, width=40)
            entry.grid(row=i, column=1, padx=10, pady=5, sticky='w')
            self.tour_entries[field] = entry
 
        tk.Label(self.tour_dialog, text='Изображение:').grid(row=len(fields), column=0, padx=10, pady=5, sticky='e')
        self.image_path = tk.StringVar()
        ttk.Entry(self.tour_dialog, textvariable=self.image_path, width=40, state='readonly').grid(
            row=len(fields), column=1, padx=10, pady=5, sticky='w')
        
        ttk.Button(
            self.tour_dialog,
            text='Выбрать файл',
            command=self.select_image
        ).grid(row=len(fields), column=2, padx=10, pady=5)

        ttk.Button(
            self.tour_dialog,
            text='Сохранить',
            command=self.create_tour,
            style='TButton'
        ).grid(row=len(fields)+1, column=1, pady=20)
    
    def select_image(self):
        file_path = filedialog.askopenfilename(
            title='Выберите изображение',
            filetypes=[('Изображения', '*.jpg *.jpeg *.png')]
        )
        if file_path:
            self.image_path.set(file_path)
    
    def create_tour(self):
        tour_data = {}
        for field, entry in self.tour_entries.items():
            tour_data[field] = entry.get()
        
        try:
            tour_data['price'] = int(tour_data['price'])
            tour_data['days'] = int(tour_data['days'])
        except ValueError:
            messagebox.showerror('Ошибка', 'Цена и длительность должны быть числами')
            return
        
        if not self.image_path.get():
            messagebox.showerror('Ошибка', 'Выберите изображение для тура')
            return

        try:
            with open(self.image_path.get(), 'rb') as img_file:
                files = {
                    'image': (os.path.basename(self.image_path.get()), img_file, 'image/jpeg'),
                    'name': (None, tour_data['name']),
                    'description': (None, tour_data['description']),
                    'price': (None, str(tour_data['price'])),
                    'days': (None, str(tour_data['days'])),
                    'country': (None, tour_data['country'])
                }
                
                response = requests.post(
                    'http://127.0.0.1:8000/tours/create/',
                    headers={'token': self.token},
                    files=files
                )

                if response.status_code == 200:
                    messagebox.showinfo('Успех', 'Тур успешно создан')
                    self.tour_dialog.destroy()
                    self.load_tours()
                else:
                    error_msg = f"Ошибка {response.status_code}"
                    try:
                        error_detail = response.json().get('detail', 'Без дополнительной информации')
                        error_msg += f": {error_detail}"
                    except:
                        error_msg += f"\n{response.text}"
                    messagebox.showerror('Ошибка', error_msg)
                    
        except Exception as e:
            messagebox.showerror('Ошибка', f'Ошибка при отправке данных: {e}')
        
    def edit_tour_dialog(self):
        selected = self.tours_tree.selection()
        if not selected:
            messagebox.showwarning('Предупреждение', 'Выберите тур для редактирования')
            return
        
        tour_id = self.tours_tree.item(selected[0])['values'][0]
        
        try:
            response = requests.get(
                'http://127.0.0.1:8000/tours/get_tour_id/',
                headers={'token': self.token},
                params={'tour_id': tour_id}
            )
            
            if response.status_code == 200:
                tour = response.json()
                self.edit_tour_window(tour_id, tour)
            else:
                error = response.json().get('detail', 'Ошибка получения данных тура')
                messagebox.showerror('Ошибка', error)
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Ошибка соединения: {e}')
    
    def edit_tour_window(self, tour_id, tour_data):
        self.edit_window = tk.Toplevel(self.root)
        self.edit_window.title(f'Редактирование тура #{tour_id}')
        self.edit_window.geometry('600x500')
        
        fields = [
            ('Название тура:', 'name'),
            ('Описание:', 'description'),
            ('Цена:', 'price'),
            ('Длительность (дней):', 'days'),
            ('Страна:', 'country')
        ]
        
        self.edit_entries = {}
        for i, (label, field) in enumerate(fields):
            tk.Label(self.edit_window, text=label).grid(row=i, column=0, padx=10, pady=5, sticky='e')
            entry = ttk.Entry(self.edit_window, width=40)
            entry.grid(row=i, column=1, padx=10, pady=5, sticky='w')
            entry.insert(0, tour_data.get(label.split(':')[0], ''))
            self.edit_entries[field] = entry

        ttk.Button(
            self.edit_window,
            text='Сохранить изменения',
            command=lambda: self.update_tour(tour_id),
            style='TButton'
        ).grid(row=len(fields)+1, column=1, pady=20)
    
    def update_tour(self, tour_id):
        tour_data = {}
        for field, entry in self.edit_entries.items():
            tour_data[field] = entry.get()

        if not all(tour_data.values()):
            messagebox.showerror('Ошибка', 'Все поля обязательны для заполнения')
            return

        try:
            tour_data['price'] = int(tour_data['price'])
            tour_data['days'] = int(tour_data['days'])
        except ValueError:
            messagebox.showerror('Ошибка', 'Цена и длительность должны быть числами')
            return
        
        try:
            response = requests.patch(
                'http://127.0.0.1:8000/tours/update/',
                headers={'token': self.token},
                params={'tour_id': tour_id},
                json=tour_data
            )
            
            if response.status_code == 200:
                messagebox.showinfo('Успех', 'Тур успешно обновлен')
                self.edit_window.destroy()
                self.load_tours()
            else:
                error = response.json().get('detail', 'Ошибка обновления тура')
                messagebox.showerror('Ошибка', error)
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Ошибка соединения: {e}')
    
    def delete_tour(self):
        selected = self.tours_tree.selection()
        if not selected:
            messagebox.showwarning('Предупреждение', 'Выберите тур для удаления')
            return
        
        tour_id = self.tours_tree.item(selected[0])['values'][0]
        
        if not messagebox.askyesno('Подтверждение', f'Вы уверены, что хотите удалить тур #{tour_id}?'):
            return
        
        try:
            response = requests.delete(
                'http://127.0.0.1:8000/tours/delete_tour/',
                headers={'token': self.token},
                params={'tour_id': tour_id}
            )
            
            if response.status_code == 200:
                messagebox.showinfo('Успех', 'Тур успешно удален')
                self.load_tours()
            else:
                error = response.json().get('detail', 'Ошибка удаления тура')
                messagebox.showerror('Ошибка', error)
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Ошибка соединения: {e}')
    
    def show_booking_statuses_management(self):
        status_window = tk.Toplevel(self.root)
        status_window.title('Управление статусами бронирования')
        status_window.geometry('800x600')

        tk.Label(
            status_window,
            text='Управление статусами бронирования',
            font=self.title_font
        ).pack(pady=10)

        btn_frame = tk.Frame(status_window)
        btn_frame.pack(pady=10)

        ttk.Button(
            btn_frame,
            text='Добавить статус',
            command=self.add_booking_status,
            style='TButton'
        ).pack(side='left', padx=10)

        ttk.Button(
            btn_frame,
            text='Редактировать статус',
            command=self.edit_booking_status,
            style='TButton'
        ).pack(side='left', padx=10)

        ttk.Button(
            btn_frame,
            text='Удалить статус',
            command=self.delete_booking_status,
            style='TButton'
        ).pack(side='left', padx=10)

        columns = ('ID', 'Название статуса')
        self.status_tree = ttk.Treeview(status_window, columns=columns, show='headings')
        self.status_tree.pack(fill='both', expand=True, padx=10, pady=10)

        for col in columns:
            self.status_tree.heading(col, text=col)
            self.status_tree.column(col, width=100, anchor='w')

        self.load_booking_statuses()

    def load_booking_statuses(self):
        for item in self.status_tree.get_children():
            self.status_tree.delete(item)
        
        try:
            response = requests.get(
                'http://127.0.0.1:8000/statusbooking/get_all/',
                headers={'token': self.token},
                timeout=5
            )
            
            if response.status_code == 200:
                statuses = response.json()
                for status in statuses:
                    if 'Статус' in status:
                        self.status_tree.insert('', 'end', values=(status['id'], status['Статус']))
                    elif 'status_name' in status:
                        self.status_tree.insert('', 'end', values=(status['id'], status['status_name']))
                    else:
                        self.status_tree.insert('', 'end', values=(status.get('id', ''), str(status)))
            else:
                error = response.json().get('detail', 'Неизвестная ошибка')
                messagebox.showerror('Ошибка', f'Не удалось загрузить статусы: {error}')
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Ошибка соединения: {e}')

    def add_booking_status(self):
        dialog = tk.Toplevel(self.root)
        dialog.title('Добавление статуса')
        dialog.geometry('300x150')
        
        tk.Label(dialog, text='Название статуса:').pack(pady=10)
        self.new_status_entry = ttk.Entry(dialog, width=30)
        self.new_status_entry.pack(pady=10)
        
        ttk.Button(
            dialog,
            text='Добавить',
            command=lambda: self.save_new_booking_status(dialog),
            style='TButton'
        ).pack(pady=10)
    
    def save_new_booking_status(self, dialog):
        status_name = self.new_status_entry.get().strip()
        if not status_name:
            messagebox.showerror('Ошибка', 'Введите название статуса')
            return
            
        try:
            response = requests.post(
                'http://127.0.0.1:8000/statusbooking/add_status',
                headers={'token': self.token},
                json={'status_name': status_name}
            )
            
            if response.status_code == 200:
                messagebox.showinfo('Успех', 'Статус успешно добавлен')
                dialog.destroy()
                self.load_booking_statuses()
            else:
                try:
                    error_detail = response.json().get('detail', 'Ошибка добавления статуса')
                    messagebox.showerror('Ошибка', error_detail)
                except:
                    messagebox.showerror('Ошибка', f'Ошибка сервера: {response.status_code}')
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Ошибка соединения: {e}')

    def edit_booking_status(self):
        selected = self.status_tree.selection()
        if not selected:
            messagebox.showwarning('Предупреждение', 'Выберите статус')
            return
            
        item = self.status_tree.item(selected[0])
        status_id = item['values'][0]
        old_name = item['values'][1]  
        
        dialog = tk.Toplevel(self.root)
        dialog.title('Редактирование статуса')
        dialog.geometry('300x150')
        
        tk.Label(dialog, text='Новое название:').pack(pady=10)
        new_name_entry = ttk.Entry(dialog, width=30)
        new_name_entry.insert(0, old_name)
        new_name_entry.pack(pady=10)
        
        def save_edit():
            new_name = new_name_entry.get().strip()
            if not new_name:
                messagebox.showerror('Ошибка', 'Введите название статуса')
                return
                
            try:
                response = requests.put(
                    f'http://127.0.0.1:8000/statusbooking/edit_status/?status_id={status_id}',
                    headers={'token': self.token},
                    json={'status_name': new_name}
                )
                
                if response.status_code == 200:
                    messagebox.showinfo('Успех', 'Статус обновлен')
                    dialog.destroy()
                    self.load_booking_statuses()
                else:
                    try:
                        error_detail = response.json().get('detail', 'Ошибка обновления статуса')
                        messagebox.showerror('Ошибка', error_detail)
                    except:
                        messagebox.showerror('Ошибка', f'Ошибка сервера: {response.status_code}')
                        
            except requests.exceptions.RequestException as e:
                messagebox.showerror('Ошибка', f'Ошибка соединения: {e}')
                
        ttk.Button(
            dialog,
            text='Сохранить',
            command=save_edit,
            style='TButton'
        ).pack(pady=10)
    
    def delete_booking_status(self):
        selected = self.status_tree.selection()
        if not selected:
            messagebox.showwarning('Предупреждение', 'Выберите статус')
            return
            
        item = self.status_tree.item(selected[0])
        status_id = item['values'][0]
        status_name = item['values'][1]
        
        if not messagebox.askyesno('Подтверждение', f'Удалить статус "{status_name}"?'):
            return
            
        try:
            response = requests.delete(
                'http://127.0.0.1:8000/statusbooking/delete_status/',
                headers={'token': self.token},
                params={'status_id': status_id}
            )
            
            if response.status_code == 200:
                messagebox.showinfo('Успех', 'Статус удален')
                self.load_booking_statuses()
            else:
                try:
                    error_detail = response.json().get('detail', 'Ошибка удаления статуса')
                    messagebox.showerror('Ошибка', error_detail)
                except:
                    messagebox.showerror('Ошибка', f'Ошибка сервера: {response.status_code}')
                    
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Ошибка соединения: {e}')
    
    def show_bookings_management(self):
        bookings_window = tk.Toplevel(self.root)
        bookings_window.title('Управление бронированиями')
        bookings_window.geometry('1200x800')

        tk.Label(
            bookings_window,
            text='Управление бронированиями',
            font=self.title_font
        ).pack(pady=10)

        btn_frame = tk.Frame(bookings_window)
        btn_frame.pack(pady=10)

        ttk.Button(
            btn_frame,
            text='Обновить',
            command=self.load_bookings,
            style='TButton'
        ).pack(side='left', padx=10)

        ttk.Button(
            btn_frame,
            text='Редактировать',
            command=self.edit_booking_admin,
            style='TButton'
        ).pack(side='left', padx=10)

        ttk.Button(
            btn_frame,
            text='Удалить',
            command=self.delete_booking_admin,
            style='TButton'
        ).pack(side='left', padx=10)

        columns = ('Номер заявки', 'Email', 'Тур', 'Дата бронирования', 'Статус', 'Количество человек', 'Дата рождения')
        self.bookings_tree = ttk.Treeview(bookings_window, columns=columns, show='headings')
        self.bookings_tree.pack(fill='both', expand=True, padx=10, pady=10)

        for col in columns:
            self.bookings_tree.heading(col, text=col)
            self.bookings_tree.column(col, width=100, anchor='w')

        scrollbar = ttk.Scrollbar(bookings_window, orient='vertical', command=self.bookings_tree.yview)
        self.bookings_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')

        self.load_bookings()

    def load_bookings(self):
        for item in self.bookings_tree.get_children():
            self.bookings_tree.delete(item)
        
        try:
            response = requests.get(
                'http://127.0.0.1:8000/booking/all_bookings/',
                headers={'token': self.token},
                timeout=5
            )
            
            if response.status_code == 200:
                bookings = response.json()
                for book in bookings:
                    self.bookings_tree.insert('', 'end', values=(
                        book.get('Номер заявки:', ''),
                        book.get('e-mail:', ''),
                        book.get('Название тура:', ''),
                        book.get('Дата бронирования:', ''),
                        book.get('Статус:', ''),
                        book.get('Количество человек:', ''),
                        book.get('Дата рождения:', '')
                    ))
            else:
                error = response.json().get('detail', 'Неизвестная ошибка')
                messagebox.showerror('Ошибка', f'Не удалось загрузить бронирования: {error}')
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Ошибка соединения: {e}')

    def edit_booking_admin(self):
        selected = self.bookings_tree.selection()
        if not selected:
            messagebox.showwarning('Предупреждение', 'Выберите бронирование')
            return
            
        item = self.bookings_tree.item(selected[0])
        values = item['values']
        booking_number = values[0]

        self.open_booking_edit_dialog(booking_number, values)

    def open_booking_edit_dialog(self, booking_number, current_values):
        dialog = tk.Toplevel(self.root)
        dialog.title(f'Редактирование бронирования {booking_number}')
        dialog.geometry('800x600')

        tk.Label(dialog, text='Email:').pack(pady=5)
        email_var = tk.StringVar(value=current_values[1])
        email_entry = ttk.Entry(dialog, textvariable=email_var, state='readonly')
        email_entry.pack(pady=5)

        tk.Label(dialog, text='Тур:').pack(pady=5)
        tour_var = tk.StringVar(value=current_values[2])
        tour_entry = ttk.Entry(dialog, textvariable=tour_var, state='readonly')
        tour_entry.pack(pady=5)

        tk.Label(dialog, text='Количество человек:').pack(pady=5)
        people_var = tk.IntVar(value=current_values[5])
        people_spinbox = ttk.Spinbox(dialog, from_=1, to=10, textvariable=people_var, width=5)
        people_spinbox.pack(pady=5)

        tk.Label(dialog, text='Дата рождения (ГГГГ-ММ-ДД):').pack(pady=5)
        birthday_var = tk.StringVar(value=current_values[6])
        birthday_entry = ttk.Entry(dialog, textvariable=birthday_var, width=20)
        birthday_entry.pack(pady=5)

        tk.Label(dialog, text='Статус:').pack(pady=5)
        try:
            status_response = requests.get(
                'http://127.0.0.1:8000/statusbooking/get_all/',
                headers={'token': self.token},
                timeout=5
            )
            if status_response.status_code == 200:
                statuses = [s['status_name'] for s in status_response.json()]
            else:
                statuses = []
        except:
            statuses = []

        status_var = tk.StringVar(value=current_values[4])
        status_combobox = ttk.Combobox(dialog, textvariable=status_var, values=statuses, state='readonly')
        status_combobox.pack(pady=5)

        def save_booking_changes():
            new_people = people_var.get()
            new_status = status_var.get()
            new_birthday = birthday_var.get()

            if not re.match(r'\d{4}-\d{2}-\d{2}', new_birthday):
                messagebox.showerror('Ошибка', 'Некорректный формат даты рождения. Используйте ГГГГ-ММ-ДД')
                return

            try:
                data = {
                    'number_of_people': new_people,
                    'status': new_status,
                    'birthday': new_birthday
                }
                response = requests.put(
                    f'http://127.0.0.1:8000/booking/update_booking/?booking_number={booking_number}',
                    headers={'token': self.token},
                    json=data
                )
                if response.status_code == 200:
                    messagebox.showinfo('Успех', 'Бронирование обновлено')
                    dialog.destroy()
                    self.load_bookings()
                else:
                    error = response.json().get('detail', 'Ошибка обновления')
                    messagebox.showerror('Ошибка', error)
            except requests.exceptions.RequestException as e:
                messagebox.showerror('Ошибка', f'Ошибка соединения: {e}')

        ttk.Button(
            dialog,
            text='Сохранить',
            command=save_booking_changes,
            style='TButton'
        ).pack(pady=20)

    def delete_booking_admin(self):
        selected = self.bookings_tree.selection()
        if not selected:
            messagebox.showwarning('Предупреждение', 'Выберите бронирование')
            return
            
        item = self.bookings_tree.item(selected[0])
        booking_number = item['values'][0]
        
        if not messagebox.askyesno('Подтверждение', f'Удалить бронирование {booking_number}?'):
            return
            
        try:
            response = requests.delete(
                'http://127.0.0.1:8000/booking/delete_booking/',
                headers={'token': self.token},
                params={'booking_number': booking_number}
            )
            
            if response.status_code == 200:
                messagebox.showinfo('Успех', 'Бронирование удалено')
                self.load_bookings()
            else:
                error = response.json().get('detail', 'Ошибка удаления')
                messagebox.showerror('Ошибка', error)
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Ошибка соединения: {e}')

class AuthApp:
    def __init__(self, root):
        self.root = root
        self.root.title('')
        self.root.geometry('1920x1080')
        self.root.state('zoomed')
        
        self.bg_color = '#f5f5f5'
        self.fg_color = '#333333'
        self.accent_color = '#4a6fa5'
        self.button_fg = '#ffffff'
        self.entry_bg = '#ffffff'
        
        self.title_font = Font(family='Helvetica', size=28, weight='bold')
        self.normal_font = Font(family='Arial', size=14)
        self.root.configure(bg=self.bg_color)

        self.main_frame = tk.Frame(self.root, bg=self.bg_color)
        self.main_frame.place(relx=0.5, rely=0.5, anchor='center')
 
        self.create_auth_widgets()

        self.base_url = 'http://127.0.0.1:8000'
        self.token = None
    
    def create_auth_widgets(self):
        tk.Label(
            self.main_frame, 
            text='Добро пожаловать\nВ AN Travel!', 
            font=self.title_font,
            bg=self.bg_color,
            fg=self.fg_color
        ).grid(row=0, column=0, columnspan=2, pady=(0, 40))

        tk.Label(
            self.main_frame, 
            text='Email или телефон:', 
            font=self.normal_font,
            bg=self.bg_color,
            fg=self.fg_color
        ).grid(row=1, column=0, sticky='e', padx=10, pady=5)
        
        self.login_entry = ttk.Entry(self.main_frame, width=30, font=self.normal_font)
        self.login_entry.grid(row=1, column=1, pady=5, ipady=5)
        
        tk.Label(
            self.main_frame, 
            text='Пароль:', 
            font=self.normal_font,
            bg=self.bg_color,
            fg=self.fg_color
        ).grid(row=2, column=0, sticky='e', padx=10, pady=5)
        
        self.password_entry = ttk.Entry(self.main_frame, width=30, show='*', font=self.normal_font)
        self.password_entry.grid(row=2, column=1, pady=5, ipady=5)

        btn_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        btn_frame.grid(row=3, columnspan=2, pady=30)
        
        style = ttk.Style()
        style.configure('TButton', 
                      font=self.normal_font, 
                      background=self.accent_color,
                      foreground=self.button_fg,
                      padding=10)
        
        ttk.Button(
            btn_frame, 
            text='Войти', 
            command=self.login,
            style='TButton'
        ).pack(side='left', padx=10)
        
        ttk.Button(
            btn_frame, 
            text='Регистрация', 
            command=self.show_register,
            style='TButton'
        ).pack(side='left', padx=10)
        
        ttk.Button(
            btn_frame, 
            text='Забыли пароль?', 
            command=self.show_forgot_password,
            style='TButton'
        ).pack(side='left', padx=10)
    
    def show_forgot_password(self):
        self.forgot_window = tk.Toplevel(self.root)
        self.forgot_window.title('Восстановление пароля')
        self.forgot_window.geometry('600x500')
        self.forgot_window.resizable(False, False)
        
        tk.Label(
            self.forgot_window, 
            text='Введите email для восстановления пароля', 
            font=self.normal_font
        ).pack(pady=20)
        
        self.email_entry = ttk.Entry(self.forgot_window, width=30, font=self.normal_font)
        self.email_entry.pack(pady=10)
        
        self.send_code_btn = ttk.Button(
            self.forgot_window, 
            text='Отправить код', 
            command=self.send_confirmation_code,
            style='TButton'
        )
        self.send_code_btn.pack(pady=20)
        
        self.code_frame = tk.Frame(self.forgot_window)
        
    def send_confirmation_code(self):
        email = self.email_entry.get().strip()
        if not email:
            messagebox.showerror('Ошибка', 'Введите email')
            return
            
        try:
            response = requests.post(
                f'{self.base_url}/users/change_password/',
                params={'email': email}
            )
            
            if response.status_code == 200:
                messagebox.showinfo('Успех', 'Код подтверждения отправлен на ваш email')
                self.send_code_btn.pack_forget()
                
                tk.Label(
                    self.code_frame, 
                    text='Введите код подтверждения:', 
                    font=self.normal_font
                ).pack(pady=10)
                
                self.code_entry = ttk.Entry(self.code_frame, width=30, font=self.normal_font)
                self.code_entry.pack(pady=10)
                
                tk.Label(
                    self.code_frame, 
                    text='Новый пароль:', 
                    font=self.normal_font
                ).pack(pady=10)
                
                self.new_password_entry = ttk.Entry(self.code_frame, width=30, show='*', font=self.normal_font)
                self.new_password_entry.pack(pady=10)
                
                ttk.Button(
                    self.code_frame, 
                    text='Подтвердить', 
                    command=self.confirm_password_change,
                    style='TButton'
                ).pack(pady=20)
                
                self.code_frame.pack()
            else:
                error = response.json().get('detail', 'Ошибка отправки кода')
                messagebox.showerror('Ошибка', error)
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Не удалось подключиться к серверу: {e}')
    
    def confirm_password_change(self):
        email = self.email_entry.get().strip()
        code = self.code_entry.get().strip()
        new_password = self.new_password_entry.get().strip()
        
        if not all([email, code, new_password]):
            messagebox.showerror('Ошибка', 'Заполните все поля')
            return
            
        try:
            response = requests.post(
                f'{self.base_url}/users/confirm_change_password/',
                params={
                    'email': email,
                    'code': code,
                    'new_password': new_password
                }
            )
            
            if response.status_code == 200:
                messagebox.showinfo('Успех', 'Пароль успешно изменен')
                self.forgot_window.destroy()
            else:
                error = response.json().get('detail', 'Ошибка смены пароля')
                messagebox.showerror('Ошибка', error)
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Не удалось подключиться к серверу: {e}')
    
    def is_phone(self, text):
        cleaned = re.sub(r'\D', '', text)
        return len(cleaned) >= 10
    
    def login(self):
        login = self.login_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not login or not password:
            messagebox.showerror('Ошибка', 'Заполните все поля')
            return
        
        try:
            if self.is_phone(login):
                auth_data = {'number_phone': login, 'password': password}
            else:
                auth_data = {'email': login, 'password': password}
            
            response = requests.post(
                f'{self.base_url}/users/auth/',
                json=auth_data
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('token')
                self.open_main_app()
            else:
                error = response.json().get('detail', 'Ошибка авторизации')
                messagebox.showerror('Ошибка', error)
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror('Ошибка', f'Не удалось подключиться к серверу: {e}')

    def open_main_app(self):
        self.root.destroy()
        root = tk.Tk()
        MainApp(root, self.token)
        root.mainloop()

    def show_register(self):
        register_window = tk.Toplevel(self.root)
        register_window.title('Регистрация')
        register_window.geometry('600x500')
        register_window.resizable(False, False)
        
        tk.Label(
            register_window, 
            text='Регистрация', 
            font=self.title_font
        ).pack(pady=20)
        
        form_frame = tk.Frame(register_window)
        form_frame.pack(pady=20)
        
        tk.Label(
            form_frame, 
            text='Email:', 
            font=self.normal_font
        ).grid(row=0, column=0, sticky='e', padx=10, pady=5)
        
        self.reg_email = ttk.Entry(form_frame, width=30, font=self.normal_font)
        self.reg_email.grid(row=0, column=1, pady=5, ipady=5)
        
        tk.Label(
            form_frame, 
            text='Пароль:', 
            font=self.normal_font
        ).grid(row=1, column=0, sticky='e', padx=10, pady=5)
        
        self.reg_password = ttk.Entry(form_frame, width=30, show='*', font=self.normal_font)
        self.reg_password.grid(row=1, column=1, pady=5, ipady=5)
        
        tk.Label(
            form_frame, 
            text='Подтвердите пароль:', 
            font=self.normal_font
        ).grid(row=2, column=0, sticky='e', padx=10, pady=5)
        
        self.reg_confirm_password = ttk.Entry(form_frame, width=30, show='*', font=self.normal_font)
        self.reg_confirm_password.grid(row=2, column=1, pady=5, ipady=5)
        
        tk.Label(
            form_frame, 
            text='ФИО:', 
            font=self.normal_font
        ).grid(row=3, column=0, sticky='e', padx=10, pady=5)
        
        self.reg_full_name = ttk.Entry(form_frame, width=30, font=self.normal_font)
        self.reg_full_name.grid(row=3, column=1, pady=5, ipady=5)
        
        tk.Label(
            form_frame, 
            text='Телефон:', 
            font=self.normal_font
        ).grid(row=4, column=0, sticky='e', padx=10, pady=5)
        
        self.reg_phone = ttk.Entry(form_frame, width=30, font=self.normal_font)
        self.reg_phone.grid(row=4, column=1, pady=5, ipady=5)
        
        ttk.Button(
            register_window, 
            text='Зарегистрироваться', 
            command=self.register,
            style='TButton'
        ).pack(pady=20)
    
    def register(self):
        data = {
            'email': self.reg_email.get(),
            'password': self.reg_password.get(),
            'confirm_password': self.reg_confirm_password.get(),
            'full_name': self.reg_full_name.get(),
            'phone': self.reg_phone.get()
        }
        
        if not all(data.values()):
            messagebox.showerror('Ошибка', 'Все поля обязательны')
            return
            
        if data['password'] != data['confirm_password']:
            messagebox.showerror('Ошибка', 'Пароли не совпадают')
            return
        
        try:
            response = requests.post(
                f'{self.base_url}/users/register/',
                params={
                    'email': data['email'],
                    'password': data['password'],
                    'full_name': data['full_name'],
                    'number_phone': data['phone']
                }
            )
            if response.status_code == 200:
                messagebox.showinfo('Успех', 'Регистрация успешна!')
                self.reg_email.master.destroy()
            else:
                error = response.json().get('detail', 'Ошибка регистрации')
                messagebox.showerror('Ошибка', error)
                
        except requests.exceptions.RequestException:
            messagebox.showerror('Ошибка', 'Не удалось подключиться к серверу')


if __name__ == '__main__':
    root = tk.Tk()
    app = AuthApp(root)
    root.mainloop()