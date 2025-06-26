import tkinter as tk
from tkinter import ttk, messagebox
import requests
from tkinter.font import Font
import os
import re

os.environ['TCL_LIBRARY'] = r"C:\Users\User\AppData\Local\Programs\Python\Python311\tcl\tcl8.6"
os.environ['TK_LIBRARY'] = r"C:\Users\User\AppData\Local\Programs\Python\Python311\tcl\tk8.6"

class MainApp:
    def __init__(self, root, token):
        self.root = root
        self.token = token
        self.user_data = {}
        self.root.title("AN Travel")
        self.root.geometry("1920x1080")
        self.root.state('zoomed')
        
        self.bg_color = "#f5f5f5"
        self.fg_color = "#333333"
        self.accent_color = "#4a6fa5"
        self.button_fg = "#ffffff"
        self.card_bg = "#ffffff"
        
        self.title_font = Font(family="Helvetica", size=28, weight="bold")
        self.normal_font = Font(family="Arial", size=14)
        self.small_font = Font(family="Arial", size=12)

        if not self.load_user_data():
            messagebox.showerror("Ошибка", "Не удалось загрузить данные пользователя")
            self.root.destroy()
            return
            
        self.create_top_bar()
        self.create_main_content()
        
    def load_user_data(self):
        try:
            response = requests.get(
                "http://127.0.0.1:8000/users/me/",
                params={"token": self.token},
                timeout=5
            )
            
            if response.status_code == 200:
                self.user_data = response.json()
                return True
            else:
                error = response.json().get("detail", "Неизвестная ошибка")
                messagebox.showerror("Ошибка", f"Ошибка загрузки данных: {error}")
                return False
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Ошибка", f"Не удалось подключиться к серверу: {e}")
            return False
        
    def create_top_bar(self):
        self.top_bar = tk.Frame(self.root, bg=self.accent_color, height=60)
        self.top_bar.pack(fill="x", side="top")
        
        self.title_label = tk.Label(
            self.top_bar, 
            text="AN Travel", 
            font=self.title_font,
            bg=self.accent_color,
            fg=self.button_fg
        )
        self.title_label.pack(side="left", padx=20)
        
        self.profile_btn = ttk.Button(
            self.top_bar,
            text="Мой профиль",
            command=self.show_profile,
            style="TButton"
        )
        self.profile_btn.pack(side="right", padx=20)
        
    def create_main_content(self):
        self.main_frame = tk.Frame(self.root, bg=self.bg_color)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        if not self.user_data:
            messagebox.showerror("Ошибка", "Данные пользователя не загружены")
            self.root.destroy()
            return
            
        if self.user_data.get("role") == "Администратор":
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
        
        tours_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        tours_frame.pack(fill="x", pady=20)
        
        tk.Label(
            tours_frame,
            text="Доступные туры:",
            font=self.normal_font,
            bg=self.bg_color,
            fg=self.fg_color
        ).pack(anchor="w")
        
        try:
            response = requests.get(
                "http://127.0.0.1:8000/tours/get_tours/",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=5
            )
            
            if response.status_code == 200:
                tours = response.json()
                for tour in tours:
                    self.create_tour_card(tours_frame, tour)
            else:
                error = response.json().get("detail", "Неизвестная ошибка")
                messagebox.showerror("Ошибка", f"Не удалось загрузить туры: {error}")
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Ошибка", f"Ошибка соединения: {e}")
    
    def create_tour_card(self, parent, tour):
        tour_card = tk.Frame(
            parent,
            bg=self.card_bg,
            bd=2,
            relief="groove",
            padx=10,
            pady=10
        )
        tour_card.pack(fill="x", pady=5)
        
        fields = [
            ("Тур", "Название тура:"),
            ("Цена", "Цена"),
            ("Длительность", "Длительность")
        ]
        
        for label, key in fields:
            tk.Label(
                tour_card,
                text=f"{label}: {tour.get(key, 'Не указано')}",
                font=self.small_font if label != "Тур" else self.normal_font,
                bg=self.card_bg
            ).pack(anchor="w")
            
        ttk.Button(
            tour_card,
            text="Забронировать",
            command=lambda t=tour: self.book_tour(t),
            style="TButton"
        ).pack(anchor="e", pady=5)
    
    def book_tour(self, tour):
        messagebox.showinfo("Информация", f"Бронирование тура {tour.get('Название тура:', '')}")
    
    def create_admin_content(self):
        welcome_label = tk.Label(
            self.main_frame,
            text="Панель администратора",
            font=self.title_font,
            bg=self.bg_color,
            fg=self.fg_color
        )
        welcome_label.pack(pady=20)
        
        admin_btn_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        admin_btn_frame.pack(pady=20)
        
        buttons = [
            ("Управление турами", self.show_tours_management),
            ("Управление пользователями", self.show_users_management),
            ("Статистика", self.show_stats)
        ]
        
        for text, command in buttons:
            ttk.Button(
                admin_btn_frame,
                text=text,
                command=command,
                style="TButton"
            ).pack(side="left", padx=10)
    
    def show_profile(self):
        if not self.load_user_data():
            messagebox.showerror("Ошибка", "Не удалось обновить данные профиля")
            return
            
        profile_window = tk.Toplevel(self.root)
        profile_window.title("Мой профиль")
        profile_window.geometry("600x500")
        profile_window.resizable(False, False)
        
        profile_frame = tk.Frame(profile_window, padx=20, pady=20)
        profile_frame.pack(fill="both", expand=True)
        
        tk.Label(
            profile_frame,
            text="Личные данные",
            font=self.title_font
        ).pack(pady=10)
        
        info_frame = tk.Frame(profile_frame)
        info_frame.pack(fill="x", pady=10)

        fields = [
            ("ФИО", "full_name"),
            ("Email", "email"),
            ("Телефон", "number_phone"),
            ("Роль", "role")
        ]
        
        for label, key in fields:
            tk.Label(
                info_frame,
                text=f"{label}: {self.user_data.get(key, 'Не указано')}",
                font=self.normal_font
            ).pack(anchor="w", pady=5)
        
        btn_frame = tk.Frame(profile_frame)
        btn_frame.pack(pady=20)
        
        buttons = [
            ("Изменить пароль", self.show_change_password),
            ("Удалить аккаунт", self.delete_account)
        ]
        
        for text, command in buttons:
            ttk.Button(
                btn_frame,
                text=text,
                command=command,
                style="TButton"
            ).pack(side="left", padx=10)
    
    def show_change_password(self):
        change_pass_window = tk.Toplevel(self.root)
        change_pass_window.title("Смена пароля")
        change_pass_window.geometry("400x300")
        
        tk.Label(
            change_pass_window,
            text="Введите email для смены пароля:",
            font=self.normal_font
        ).pack(pady=10)
        
        email_entry = ttk.Entry(change_pass_window, width=30, font=self.normal_font)
        email_entry.pack(pady=10)
        email_entry.insert(0, self.user_data.get('email', ''))
        
        ttk.Button(
            change_pass_window,
            text="Отправить код подтверждения",
            command=lambda: self.send_password_code(email_entry.get()),
            style="TButton"
        ).pack(pady=20)
    
    def send_password_code(self, email):
        if not email:
            messagebox.showerror("Ошибка", "Введите email")
            return
            
        try:
            response = requests.post(
                "http://127.0.0.1:8000/users/change_password/",
                params={"email": email},
                timeout=5
            )
            
            if response.status_code == 200:
                messagebox.showinfo("Успех", "Код подтверждения отправлен на ваш email")
            else:
                error = response.json().get("detail", "Ошибка отправки кода")
                messagebox.showerror("Ошибка", error)
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Ошибка", f"Не удалось подключиться к серверу: {e}")
    
    def delete_account(self):
        if not messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить аккаунт?"):
            return
            
        try:
            response = requests.delete(
                "http://127.0.0.1:8000/users/delete_profile/",
                params={"token": self.token},
                timeout=5
            )
            
            if response.status_code == 200:
                messagebox.showinfo("Успех", "Аккаунт успешно удален")
                self.root.destroy()
            else:
                error = response.json().get("detail", "Ошибка удаления аккаунта")
                messagebox.showerror("Ошибка", error)
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Ошибка", f"Не удалось подключиться к серверу: {e}")
    
    def show_tours_management(self):
        messagebox.showinfo("Информация", "Функционал управления турами будет реализован позже")
    
    def show_users_management(self):
        messagebox.showinfo("Информация", "Функционал управления пользователями будет реализован позже")
    
    def show_stats(self):
        messagebox.showinfo("Информация", "Функционал статистики будет реализован позже")

class AuthApp:
    def __init__(self, root):
        self.root = root
        self.root.title("")
        self.root.geometry("1920x1080")
        self.root.state('zoomed')
        
        self.bg_color = "#f5f5f5"
        self.fg_color = "#333333"
        self.accent_color = "#4a6fa5"
        self.button_fg = "#ffffff"
        self.entry_bg = "#ffffff"
        
        self.title_font = Font(family="Helvetica", size=28, weight="bold")
        self.normal_font = Font(family="Arial", size=14)
        self.root.configure(bg=self.bg_color)

        self.main_frame = tk.Frame(self.root, bg=self.bg_color)
        self.main_frame.place(relx=0.5, rely=0.5, anchor="center")
 
        self.create_auth_widgets()

        self.base_url = "http://127.0.0.1:8000"
        self.token = None
    
    def create_auth_widgets(self):
        tk.Label(
            self.main_frame, 
            text="Добро пожаловать\nВ AN Travel!", 
            font=self.title_font,
            bg=self.bg_color,
            fg=self.fg_color
        ).grid(row=0, column=0, columnspan=2, pady=(0, 40))

        tk.Label(
            self.main_frame, 
            text="Email или телефон:", 
            font=self.normal_font,
            bg=self.bg_color,
            fg=self.fg_color
        ).grid(row=1, column=0, sticky="e", padx=10, pady=5)
        
        self.login_entry = ttk.Entry(self.main_frame, width=30, font=self.normal_font)
        self.login_entry.grid(row=1, column=1, pady=5, ipady=5)
        
        tk.Label(
            self.main_frame, 
            text="Пароль:", 
            font=self.normal_font,
            bg=self.bg_color,
            fg=self.fg_color
        ).grid(row=2, column=0, sticky="e", padx=10, pady=5)
        
        self.password_entry = ttk.Entry(self.main_frame, width=30, show="*", font=self.normal_font)
        self.password_entry.grid(row=2, column=1, pady=5, ipady=5)

        btn_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        btn_frame.grid(row=3, columnspan=2, pady=30)
        
        style = ttk.Style()
        style.configure("TButton", 
                      font=self.normal_font, 
                      background=self.accent_color,
                      foreground=self.button_fg,
                      padding=10)
        
        ttk.Button(
            btn_frame, 
            text="Войти", 
            command=self.login,
            style="TButton"
        ).pack(side="left", padx=10)
        
        ttk.Button(
            btn_frame, 
            text="Регистрация", 
            command=self.show_register,
            style="TButton"
        ).pack(side="left", padx=10)
        
        ttk.Button(
            btn_frame, 
            text="Забыли пароль?", 
            command=self.show_forgot_password,
            style="TButton"
        ).pack(side="left", padx=10)
    
    def show_forgot_password(self):
        self.forgot_window = tk.Toplevel(self.root)
        self.forgot_window.title("Восстановление пароля")
        self.forgot_window.geometry("600x500")
        self.forgot_window.resizable(False, False)
        
        tk.Label(
            self.forgot_window, 
            text="Введите email для восстановления пароля", 
            font=self.normal_font
        ).pack(pady=20)
        
        self.email_entry = ttk.Entry(self.forgot_window, width=30, font=self.normal_font)
        self.email_entry.pack(pady=10)
        
        self.send_code_btn = ttk.Button(
            self.forgot_window, 
            text="Отправить код", 
            command=self.send_confirmation_code,
            style="TButton"
        )
        self.send_code_btn.pack(pady=20)
        
        self.code_frame = tk.Frame(self.forgot_window)
        
    def send_confirmation_code(self):
        email = self.email_entry.get().strip()
        if not email:
            messagebox.showerror("Ошибка", "Введите email")
            return
            
        try:
            response = requests.post(
                f"{self.base_url}/users/change_password/",
                params={"email": email}
            )
            
            if response.status_code == 200:
                messagebox.showinfo("Успех", "Код подтверждения отправлен на ваш email")
                self.send_code_btn.pack_forget()
                
                tk.Label(
                    self.code_frame, 
                    text="Введите код подтверждения:", 
                    font=self.normal_font
                ).pack(pady=10)
                
                self.code_entry = ttk.Entry(self.code_frame, width=30, font=self.normal_font)
                self.code_entry.pack(pady=10)
                
                tk.Label(
                    self.code_frame, 
                    text="Новый пароль:", 
                    font=self.normal_font
                ).pack(pady=10)
                
                self.new_password_entry = ttk.Entry(self.code_frame, width=30, show="*", font=self.normal_font)
                self.new_password_entry.pack(pady=10)
                
                ttk.Button(
                    self.code_frame, 
                    text="Подтвердить", 
                    command=self.confirm_password_change,
                    style="TButton"
                ).pack(pady=20)
                
                self.code_frame.pack()
            else:
                error = response.json().get("detail", "Ошибка отправки кода")
                messagebox.showerror("Ошибка", error)
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Ошибка", f"Не удалось подключиться к серверу: {e}")
    
    def confirm_password_change(self):
        email = self.email_entry.get().strip()
        code = self.code_entry.get().strip()
        new_password = self.new_password_entry.get().strip()
        
        if not all([email, code, new_password]):
            messagebox.showerror("Ошибка", "Заполните все поля")
            return
            
        try:
            response = requests.post(
                f"{self.base_url}/users/confirm_change_password/",
                params={
                    "email": email,
                    "code": code,
                    "new_password": new_password
                }
            )
            
            if response.status_code == 200:
                messagebox.showinfo("Успех", "Пароль успешно изменен")
                self.forgot_window.destroy()
            else:
                error = response.json().get("detail", "Ошибка смены пароля")
                messagebox.showerror("Ошибка", error)
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Ошибка", f"Не удалось подключиться к серверу: {e}")
    
    def is_phone(self, text):
        cleaned = re.sub(r'\D', '', text)
        return len(cleaned) >= 10
    
    def login(self):
        login = self.login_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not login or not password:
            messagebox.showerror("Ошибка", "Заполните все поля")
            return
        
        try:
            if self.is_phone(login):
                auth_data = {"number_phone": login, "password": password}
            else:
                auth_data = {"email": login, "password": password}
            
            response = requests.post(
                f"{self.base_url}/users/auth/",
                json=auth_data
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                self.open_main_app()
            else:
                error = response.json().get("detail", "Ошибка авторизации")
                messagebox.showerror("Ошибка", error)
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Ошибка", f"Не удалось подключиться к серверу: {e}")

    def open_main_app(self):
        self.root.destroy()
        root = tk.Tk()
        MainApp(root, self.token)
        root.mainloop()

    def show_register(self):
        register_window = tk.Toplevel(self.root)
        register_window.title("Регистрация")
        register_window.geometry("600x500")
        register_window.resizable(False, False)
        
        tk.Label(
            register_window, 
            text="Регистрация", 
            font=self.title_font
        ).pack(pady=20)
        
        form_frame = tk.Frame(register_window)
        form_frame.pack(pady=20)
        
        tk.Label(
            form_frame, 
            text="Email:", 
            font=self.normal_font
        ).grid(row=0, column=0, sticky="e", padx=10, pady=5)
        
        self.reg_email = ttk.Entry(form_frame, width=30, font=self.normal_font)
        self.reg_email.grid(row=0, column=1, pady=5, ipady=5)
        
        tk.Label(
            form_frame, 
            text="Пароль:", 
            font=self.normal_font
        ).grid(row=1, column=0, sticky="e", padx=10, pady=5)
        
        self.reg_password = ttk.Entry(form_frame, width=30, show="*", font=self.normal_font)
        self.reg_password.grid(row=1, column=1, pady=5, ipady=5)
        
        tk.Label(
            form_frame, 
            text="Подтвердите пароль:", 
            font=self.normal_font
        ).grid(row=2, column=0, sticky="e", padx=10, pady=5)
        
        self.reg_confirm_password = ttk.Entry(form_frame, width=30, show="*", font=self.normal_font)
        self.reg_confirm_password.grid(row=2, column=1, pady=5, ipady=5)
        
        tk.Label(
            form_frame, 
            text="ФИО:", 
            font=self.normal_font
        ).grid(row=3, column=0, sticky="e", padx=10, pady=5)
        
        self.reg_full_name = ttk.Entry(form_frame, width=30, font=self.normal_font)
        self.reg_full_name.grid(row=3, column=1, pady=5, ipady=5)
        
        tk.Label(
            form_frame, 
            text="Телефон:", 
            font=self.normal_font
        ).grid(row=4, column=0, sticky="e", padx=10, pady=5)
        
        self.reg_phone = ttk.Entry(form_frame, width=30, font=self.normal_font)
        self.reg_phone.grid(row=4, column=1, pady=5, ipady=5)
        
        ttk.Button(
            register_window, 
            text="Зарегистрироваться", 
            command=self.register,
            style="TButton"
        ).pack(pady=20)
    
    def register(self):
        data = {
            "email": self.reg_email.get(),
            "password": self.reg_password.get(),
            "confirm_password": self.reg_confirm_password.get(),
            "full_name": self.reg_full_name.get(),
            "phone": self.reg_phone.get()
        }
        
        if not all(data.values()):
            messagebox.showerror("Ошибка", "Все поля обязательны")
            return
            
        if data["password"] != data["confirm_password"]:
            messagebox.showerror("Ошибка", "Пароли не совпадают")
            return
        
        try:
            response = requests.post(
                f"{self.base_url}/users/register/",
                params={
                    "email": data["email"],
                    "password": data["password"],
                    "full_name": data["full_name"],
                    "number_phone": data["phone"]
                }
            )
            if response.status_code == 200:
                messagebox.showinfo("Успех", "Регистрация успешна!")
                self.reg_email.master.destroy()
            else:
                error = response.json().get("detail", "Ошибка регистрации")
                messagebox.showerror("Ошибка", error)
                
        except requests.exceptions.RequestException:
            messagebox.showerror("Ошибка", "Не удалось подключиться к серверу")


if __name__ == "__main__":
    root = tk.Tk()
    app = AuthApp(root)
    root.mainloop()

MainApp.delete_account()