import os
import sqlite3
import json
import csv
import yaml
import xml.etree.ElementTree as ET
import hashlib


def hash_password(password, salt):
    hash_obj = hashlib.sha256()
    hash_obj.update(f"{password}{salt}".encode('utf-8'))
    return hash_obj.hexdigest()


def verify_password(password, stored_hash, salt):
    hash_obj = hashlib.sha256()
    hash_obj.update(f"{password}{salt}".encode('utf-8'))
    return hash_obj.hexdigest() == stored_hash


def login_user(conn, user_type):
    cursor = conn.cursor()

    print(f"\n=== Авторизация {user_type}а ===")

    username = input("Введите ФИО: ")
    password = input("Введите пароль: ")

    try:
        if user_type == "driver":
            cursor.execute("""
                SELECT d.Driver_id, d.Username, d.Rating, dc.PasswordHash, dc.Salt 
                FROM Drivers d
                JOIN DriverCredentials dc ON d.Driver_id = dc.Driver_id
                WHERE d.Username = ?
            """, (username,))

            user_data = cursor.fetchone()

            if user_data and verify_password(password, user_data[3], user_data[4]):
                print(f"\n✓ Успешный вход! Добро пожаловать, {user_data[1]}!")
                return {
                    'id': user_data[0],
                    'username': user_data[1],
                    'rating': user_data[2],
                    'type': 'driver'
                }

        elif user_type == "passenger":
            cursor.execute("""
                SELECT p.Passenger_id, p.Username, p.Rating, pc.PasswordHash, pc.Salt 
                FROM Passengers p
                JOIN PassengerCredentials pc ON p.Passenger_id = pc.Passenger_id
                WHERE p.Username = ?
            """, (username,))

            user_data = cursor.fetchone()

            if user_data and verify_password(password, user_data[3], user_data[4]):
                print(f"\n✓ Успешный вход! Добро пожаловать, {user_data[1]}!")
                return {
                    'id': user_data[0],
                    'username': user_data[1],
                    'rating': user_data[2],
                    'type': 'passenger'
                }

        print("\n✗ Ошибка: Неверное имя пользователя или пароль!")
        return None

    except sqlite3.Error as e:
        print(f"\n✗ Ошибка при авторизации: {e}")
        return None


def show_user_menu(conn, user):
    cursor = conn.cursor()

    while True:
        print(f"\n{'=' * 40}")
        print(f"МЕНЮ: {user['username']} ({user['type']})")
        print(f"{'=' * 40}")
        print("1. 📋 Просмотреть мои заказы")
        print("2. 🔔 Просмотреть уведомления")
        print("3. 🗑️ Удалить заказ (физическое удаление)")
        print("4. 🚪 Выйти из аккаунта")

        if user['type'] == 'driver':
            print("5. 📦 Просмотреть доступные заказы")
            print("6. ✅ Принять заказ")
        elif user['type'] == 'passenger':
            print("2. 🔔 Просмотреть уведомления")
            print("5. 🚕 Создать новый заказ")

        choice = input("\nВыберите действие (1-6): ")

        if choice == '1':
            show_user_orders(cursor, user)
        elif choice == '2':
            show_notifications(cursor, user)
        elif choice == '3':
            delete_order(conn, cursor, user)
        elif choice == '4':
            print("\nВыход из аккаунта...")
            break
        elif choice == '5' and user['type'] == 'driver':
            show_available_orders(cursor)
        elif choice == '6' and user['type'] == 'driver':
            accept_order(conn, cursor, user)
        elif choice == '5' and user['type'] == 'passenger':
            create_order(conn, cursor, user)
        else:
            print("\n✗ Неверный выбор! Попробуйте снова.")


def show_user_orders(cursor, user):
    if user['type'] == 'driver':
        cursor.execute("""
            SELECT o.Orders_id, p.Username, a.Delivery_address, a.Final_address, 
                   a.Time_order, a.Price, a.Distance_km
            FROM Orders o
            JOIN Passengers p ON o.Passenger_id = p.Passenger_id
            JOIN About_orders a ON o.About_orders_id = a.About_orders_id
            WHERE o.Driver_id = ?
        """, (user['id'],))
    else:
        cursor.execute("""
            SELECT o.Orders_id, d.Username, a.Delivery_address, a.Final_address, 
                   a.Time_order, a.Price, a.Distance_km
            FROM Orders o
            LEFT JOIN Drivers d ON o.Driver_id = d.Driver_id
            JOIN About_orders a ON o.About_orders_id = a.About_orders_id
            WHERE o.Passenger_id = ?
        """, (user['id'],))

    orders = cursor.fetchall()

    if orders:
        print(f"\n📋 Ваши заказы ({len(orders)}):")
        print("-" * 90)
        for order in orders:
            print(f"   ID заказа: {order[0]}")
            if user['type'] == 'driver':
                print(f"   Пассажир: {order[1]}")
            else:
                print(f"   Водитель: {order[1] if order[1] else 'Ожидание водителя...'}")
            print(f"   Откуда: {order[2]}")
            print(f"   Куда: {order[3]}")
            print(f"   Время: {order[4]}")
            print(f"   Цена: {order[5]} руб.")
            print(f"   Расстояние: {order[6]} км")
            print("-" * 90)
    else:
        print("\n📭 У вас пока нет заказов.")


def show_notifications(cursor, user):
    if user['type'] == 'passenger':
        cursor.execute("""
            SELECT notification_id, message, CreatedAt 
            FROM Notification 
            WHERE Passenger_id = ? AND IsRead = 0
            ORDER BY CreatedAt DESC
        """, (user['id'],))
    else:
        print("\nℹ️ Уведомления доступны только для пассажиров.")
        return

    notifications = cursor.fetchall()

    if notifications:
        print(f"\n🔔 Ваши уведомления ({len(notifications)}):")
        print("-" * 60)
        for notification in notifications:
            print(f"   ID: {notification[0]}")
            print(f"   Сообщение: {notification[1]}")
            print(f"   Время: {notification[2]}")
            print("-" * 60)

        cursor.execute("""
            UPDATE Notification 
            SET IsRead = 1 
            WHERE Passenger_id = ? AND IsRead = 0
        """, (user['id'],))
    else:
        print("\n📭 У вас нет новых уведомлений.")


def delete_order(conn, cursor, user):
    try:
        print(f"\n{'=' * 60}")
        print("🗑️  УДАЛЕНИЕ ЗАКАЗА ИЗ БАЗЫ ДАННЫХ")
        print("=" * 60)
        print("⚠️  ВНИМАНИЕ: Это действие НЕОБРАТИМО!")
        print("   Заказ будет полностью удален из базы данных.")
        print("-" * 60)

        if user['type'] == 'driver':
            cursor.execute("""
                SELECT o.Orders_id, p.Username, a.Delivery_address, a.Final_address
                FROM Orders o
                JOIN Passengers p ON o.Passenger_id = p.Passenger_id
                JOIN About_orders a ON o.About_orders_id = a.About_orders_id
                WHERE o.Driver_id = ?
            """, (user['id'],))
        else:
            cursor.execute("""
                SELECT o.Orders_id, d.Username, a.Delivery_address, a.Final_address
                FROM Orders o
                LEFT JOIN Drivers d ON o.Driver_id = d.Driver_id
                JOIN About_orders a ON o.About_orders_id = a.About_orders_id
                WHERE o.Passenger_id = ?
            """, (user['id'],))

        orders = cursor.fetchall()

        if not orders:
            print("У вас нет заказов для удаления.")
            return

        print("\n📋 Ваши заказы:")
        print("-" * 70)
        for order in orders:
            if user['type'] == 'driver':
                print(f"   ID: {order[0]}, Пассажир: {order[1]}")
                print(f"      Откуда: {order[2]}")
                print(f"      Куда: {order[3]}")
            else:
                print(f"   ID: {order[0]}, Водитель: {order[1] if order[1] else 'Не назначен'}")
                print(f"      Откуда: {order[2]}")
                print(f"      Куда: {order[3]}")
            print("-" * 70)

        order_id = input("\nВведите ID заказа для удаления: ")

        if not order_id.isdigit():
            print("\n✗ Ошибка: ID заказа должен быть числом!")
            return

        if user['type'] == 'driver':
            cursor.execute("""
                SELECT o.Orders_id, o.Passenger_id, a.About_orders_id, p.Username
                FROM Orders o
                JOIN About_orders a ON o.About_orders_id = a.About_orders_id
                JOIN Passengers p ON o.Passenger_id = p.Passenger_id
                WHERE o.Orders_id = ? AND o.Driver_id = ?
            """, (order_id, user['id']))
        else:
            cursor.execute("""
                SELECT o.Orders_id, o.Passenger_id, a.About_orders_id, d.Username
                FROM Orders o
                JOIN About_orders a ON o.About_orders_id = a.About_orders_id
                LEFT JOIN Drivers d ON o.Driver_id = d.Driver_id
                WHERE o.Orders_id = ? AND o.Passenger_id = ?
            """, (order_id, user['id']))

        order_data = cursor.fetchone()

        if not order_data:
            print(f"\n✗ Ошибка: Заказ с ID {order_id} не найден или не принадлежит вам!")
            return

        print(f"\n📄 Информация о заказе #{order_id}:")
        print("-" * 50)
        if user['type'] == 'driver':
            print(f"   Пассажир: {order_data[3]}")
        else:
            print(f"   Водитель: {order_data[3] if order_data[3] else 'Не назначен'}")

        print(f"\n{'!' * 60}")
        print("⚠️  ВНИМАНИЕ! ⚠️")
        print(f"Вы собираетесь ФИЗИЧЕСКИ удалить заказ #{order_id}!")
        print(f"Это действие НЕЛЬЗЯ отменить!")
        print(f"{'!' * 60}")

        confirm1 = input(f"\nДля подтверждения введите 'УДАЛИТЬ': ")

        if confirm1 != 'УДАЛИТЬ':
            print("❌ Удаление отменено.")
            return

        confirm2 = input(f"\nПоследнее подтверждение. Введите 'ДА, УДАЛИТЬ': ")

        if confirm2 != 'ДА, УДАЛИТЬ':
            print("❌ Удаление отменено.")
            return

        passenger_id = order_data[1]
        about_order_id = order_data[2]

        cursor.execute("DELETE FROM Orders WHERE Orders_id = ?", (order_id,))
        print(f"✓ Запись Orders #{order_id} удалена")

        cursor.execute("""
            SELECT COUNT(*) FROM Orders WHERE About_orders_id = ?
        """, (about_order_id,))

        other_orders_count = cursor.fetchone()[0]

        if other_orders_count == 0:
            cursor.execute("DELETE FROM About_orders WHERE About_orders_id = ?", (about_order_id,))
            print(f"✓ Детали заказа About_orders #{about_order_id} удалены")

        if user['type'] == 'driver':
            cursor.execute("""
                INSERT INTO Notification (Passenger_id, message)
                VALUES (?, ?)
            """, (passenger_id, f"Водитель {user['username']} удалил заказ #{order_id} из системы."))
            print(f"✓ Пассажир #{passenger_id} уведомлен об удалении")
        else:
            cursor.execute("""
                INSERT INTO Notification (Passenger_id, message)
                VALUES (?, ?)
            """, (user['id'], f"Вы удалили свой заказ #{order_id} из системы."))
            print(f"✓ Вы уведомлены об удалении заказа")

        conn.commit()
        print(f"\n✅ Заказ #{order_id} успешно УДАЛЕН из базы данных!")
        print("⚠️  Восстановление данных НЕВОЗМОЖНО!")

    except sqlite3.Error as e:
        print(f"\n✗ Ошибка при удалении заказа: {e}")
        conn.rollback()
        print("❌ Удаление отменено из-за ошибки.")


def show_available_orders(cursor):
    cursor.execute("""
        SELECT a.About_orders_id, p.Username, a.Delivery_address, a.Final_address, 
               a.Time_order, a.Price, a.Distance_km, o.Orders_id
        FROM About_orders a
        LEFT JOIN Orders o ON a.About_orders_id = o.About_orders_id
        LEFT JOIN Passengers p ON o.Passenger_id = p.Passenger_id
        WHERE o.Driver_id IS NULL
        ORDER BY a.Time_order
    """)

    orders = cursor.fetchall()

    if orders:
        print(f"\n📦 Доступные заказы ({len(orders)}):")
        print("-" * 100)
        for order in orders:
            print(f"   ID заказа: {order[7] if order[7] else 'Новый'}")
            print(f"   ID деталей: {order[0]}")
            print(f"   Пассажир: {order[1]}")
            print(f"   Откуда: {order[2]}")
            print(f"   Куда: {order[3]}")
            print(f"   Время: {order[4]}")
            print(f"   Цена: {order[5]} руб.")
            print(f"   Расстояние: {order[6]} км")
            print("-" * 100)
    else:
        print("\n📭 Нет доступных заказов в данный момент.")


def accept_order(conn, cursor, driver):
    try:
        order_id = input("Введите ID заказа для принятия: ")

        if not order_id.isdigit():
            print("\n✗ Ошибка: ID заказа должен быть числом!")
            return

        cursor.execute("""
            SELECT o.Orders_id, o.Driver_id, o.Passenger_id
            FROM Orders o
            WHERE o.Orders_id = ?
        """, (order_id,))

        order_data = cursor.fetchone()

        if not order_data:
            print(f"\n✗ Ошибка: Заказ с ID {order_id} не найден!")
            return

        if order_data[1]:
            print(f"\n✗ Ошибка: Этот заказ уже принят другим водителем!")
            return

        cursor.execute("""
            UPDATE Orders 
            SET Driver_id = ?
            WHERE Orders_id = ?
        """, (driver['id'], order_id))

        passenger_id = order_data[2]

        cursor.execute("""
            INSERT INTO Notification (Passenger_id, message)
            VALUES (?, ?)
        """, (passenger_id, f"Ваш заказ #{order_id} принят водителем {driver['username']}!"))

        conn.commit()
        print(f"\n✓ Успех! Вы приняли заказ #{order_id}!")

    except sqlite3.Error as e:
        print(f"\n✗ Ошибка при принятии заказа: {e}")
        conn.rollback()


def create_order(conn, cursor, passenger):
    try:
        print("\n📝 Создание нового заказа")
        print("-" * 40)

        delivery_address = input("Откуда (адрес подачи): ")
        final_address = input("Куда (адрес назначения): ")
        time_order = input("Время заказа (например, 15:30): ")

        try:
            price = float(input("Стоимость поездки (руб.): "))
            distance = float(input("Расстояние (км): "))
        except ValueError:
            print("\n✗ Ошибка: Стоимость и расстояние должны быть числами!")
            return

        cursor.execute("""
            INSERT INTO About_orders (Delivery_address, Time_order, Price, Final_address, Distance_km)
            VALUES (?, ?, ?, ?, ?)
        """, (delivery_address, time_order, price, final_address, distance))

        about_order_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO Orders (Driver_id, Passenger_id, About_orders_id)
            VALUES (NULL, ?, ?)
        """, (passenger['id'], about_order_id))

        order_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO Notification (Passenger_id, message)
            VALUES (?, ?)
        """, (passenger['id'], f"Ваш заказ #{order_id} создан! Ожидайте водителя."))

        conn.commit()
        print(f"\n✓ Успех! Заказ #{order_id} создан!")
        print(f"   Откуда: {delivery_address}")
        print(f"   Куда: {final_address}")
        print(f"   Время: {time_order}")
        print(f"   Стоимость: {price} руб.")
        print(f"   Расстояние: {distance} км")

    except sqlite3.Error as e:
        print(f"\n✗ Ошибка при создании заказа: {e}")
        conn.rollback()


def main():
    DB_NAME = "DuberBuber.db"
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.executescript("""
    DROP TABLE IF EXISTS Notification;
    DROP TABLE IF EXISTS Orders;
    DROP TABLE IF EXISTS About_orders;
    DROP TABLE IF EXISTS DriverCredentials;
    DROP TABLE IF EXISTS PassengerCredentials;
    DROP TABLE IF EXISTS Drivers;
    DROP TABLE IF EXISTS Passengers;

    CREATE TABLE Drivers (
        Driver_id INTEGER PRIMARY KEY AUTOINCREMENT,
        Username TEXT NOT NULL,
        Rating REAL,
        CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE Passengers (
        Passenger_id INTEGER PRIMARY KEY AUTOINCREMENT,
        Username TEXT NOT NULL,
        Rating REAL,
        CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE DriverCredentials (
        Credential_id INTEGER PRIMARY KEY AUTOINCREMENT,
        Driver_id INTEGER NOT NULL,
        PasswordHash TEXT NOT NULL,
        Salt TEXT NOT NULL,
        FOREIGN KEY(Driver_id) REFERENCES Drivers(Driver_id) ON DELETE CASCADE,
        UNIQUE(Driver_id)
    );

    CREATE TABLE PassengerCredentials (
        Credential_id INTEGER PRIMARY KEY AUTOINCREMENT,
        Passenger_id INTEGER NOT NULL,
        PasswordHash TEXT NOT NULL,
        Salt TEXT NOT NULL,
        FOREIGN KEY(Passenger_id) REFERENCES Passengers(Passenger_id) ON DELETE CASCADE,
        UNIQUE(Passenger_id)
    );

    CREATE TABLE About_orders (
        About_orders_id INTEGER PRIMARY KEY AUTOINCREMENT,
        Delivery_address TEXT NOT NULL,
        Time_order TEXT NOT NULL,
        Price REAL NOT NULL,
        Final_address TEXT NOT NULL,
        Distance_km REAL NOT NULL,
        CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE Orders (
        Orders_id INTEGER PRIMARY KEY AUTOINCREMENT,
        Driver_id INTEGER,
        Passenger_id INTEGER NOT NULL,
        About_orders_id INTEGER NOT NULL,
        CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(Driver_id) REFERENCES Drivers(Driver_id),
        FOREIGN KEY(Passenger_id) REFERENCES Passengers(Passenger_id),
        FOREIGN KEY(About_orders_id) REFERENCES About_orders(About_orders_id)
    );

    CREATE TABLE Notification (
        notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
        Passenger_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        IsRead BOOLEAN DEFAULT 0,
        CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(Passenger_id) REFERENCES Passengers(Passenger_id)
    );
    """)

    test_drivers = [
        ("Славка Андрей Владиславович", 2.3, "driver123"),
        ("Капитанов Иван Александрович", 4.7, "driver456"),
        ("Хороших Егор Эдуардович", 3.6, "driver789")
    ]

    test_passengers = [
        ("Раева Кира Сергеевна", 4.3, "pass123"),
        ("Галкин Илья Алексеевич", 5.0, "pass456"),
        ("Боярсков Павел Владиславович", 2.8, "pass789")
    ]

    print("\n" + "=" * 50)
    print("СОЗДАНИЕ ТЕСТОВЫХ ДАННЫХ")
    print("=" * 50)

    print("\nСоздаю тестовых водителей...")
    for username, rating, password in test_drivers:
        cursor.execute("INSERT INTO Drivers (Username, Rating) VALUES (?, ?)",
                       (username, rating))
        driver_id = cursor.lastrowid
        salt = f"salt_driver_{driver_id}"
        password_hash = hash_password(password, salt)
        cursor.execute("INSERT INTO DriverCredentials (Driver_id, PasswordHash, Salt) VALUES (?, ?, ?)",
                       (driver_id, password_hash, salt))
        print(f"  ✓ Водитель: {username} (пароль: {password})")

    print("\nСоздаю тестовых пассажиров...")
    for username, rating, password in test_passengers:
        cursor.execute("INSERT INTO Passengers (Username, Rating) VALUES (?, ?)",
                       (username, rating))
        passenger_id = cursor.lastrowid
        salt = f"salt_passenger_{passenger_id}"
        password_hash = hash_password(password, salt)
        cursor.execute("INSERT INTO PassengerCredentials (Passenger_id, PasswordHash, Salt) VALUES (?, ?, ?)",
                       (passenger_id, password_hash, salt))
        print(f"  ✓ Пассажир: {username} (пароль: {password})")

    print("\nСоздаю тестовые заказы...")
    About_orders = [
        ("Ул. Красная Поляна, д. 2, подъезд 1", "15:06", 654, "Ул. Бурнаковская, д. 75", 1.9),
        ("Ул. Осипенко, д. 82", "19:59", 427, "Ул. Нижневолжсая, д. 19", 5.0),
        ("Ул. Минина, д. 24", "6:44", 987, "Ул. Рожденственская, д 10", 2.8)
    ]

    for order in About_orders:
        cursor.execute(
            "INSERT INTO About_orders (Delivery_address, Time_order, Price, Final_address, Distance_km) VALUES (?, ?, ?, ?, ?)",
            order)
        print(f"  ✓ Заказ из {order[0]} в {order[3]}")

    print("\nНазначаю заказы...")
    cursor.execute("INSERT INTO Orders (Driver_id, Passenger_id, About_orders_id) VALUES (2, 3, 2)")
    cursor.execute("INSERT INTO Orders (Driver_id, Passenger_id, About_orders_id) VALUES (1, 1, 1)")
    cursor.execute("INSERT INTO Orders (Driver_id, Passenger_id, About_orders_id) VALUES (3, 2, 3)")
    cursor.execute("INSERT INTO Orders (Driver_id, Passenger_id, About_orders_id) VALUES (NULL, 1, 1)")
    print("  ✓ Назначено 4 заказа (3 с водителями, 1 ожидающий)")

    notifications = [
        (1, "Ваш водитель уже в пути!"),
        (2, "Ваш водитель подъезжает!"),
        (3, "Ожидайте водителя в течение 5 минут")
    ]

    for passenger_id, message in notifications:
        cursor.execute("INSERT INTO Notification (Passenger_id, message) VALUES (?, ?)", (passenger_id, message))

    conn.commit()
    print("\n" + "=" * 50)
    print("СИСТЕМА ГОТОВА К РАБОТЕ")
    print("=" * 50)

    while True:
        print("\n" + "=" * 50)
        print("DUBER BUBER - СИСТЕМА ЗАКАЗА ТАКСИ")
        print("=" * 50)
        print("1. 🚗 Войти как водитель")
        print("2. 👤 Войти как пассажир")
        print("3. 📊 Экспортировать данные (администратор)")
        print("4. 🚪 Выйти из системы")

        choice = input("\nВыберите действие (1-4): ")

        if choice == '1':
            user = login_user(conn, "driver")
            if user:
                show_user_menu(conn, user)
        elif choice == '2':
            user = login_user(conn, "passenger")
            if user:
                show_user_menu(conn, user)
        elif choice == '3':
            admin_pass = input("Введите пароль администратора: ")
            if admin_pass == "admin123":
                export_data(conn)
            else:
                print("\n✗ Неверный пароль администратора!")
        elif choice == '4':
            print("\n" + "=" * 50)
            print("Спасибо за использование DuberBuber! До свидания!")
            print("=" * 50)
            break
        else:
            print("\n✗ Неверный выбор! Пожалуйста, выберите 1-4.")

    conn.close()


def export_data(conn):
    cursor = conn.cursor()

    print("\n" + "=" * 50)
    print("ЭКСПОРТ ДАННЫХ")
    print("=" * 50)

    cursor.execute("""
    SELECT O.Orders_id, D.Driver_id, D.Username, D.Rating, P.Passenger_id, P.Username, P.Rating, 
           A.Delivery_address, A.Final_address, A.Time_order, A.Price, A.Distance_km
    FROM Orders O
    JOIN Drivers D ON O.Driver_id = D.Driver_id
    JOIN Passengers P ON O.Passenger_id = P.Passenger_id
    JOIN About_orders A ON O.About_orders_id = A.About_orders_id
    LEFT JOIN Notification N ON P.Passenger_id = N.Passenger_id
    ORDER BY O.Orders_id
    """)
    rows = cursor.fetchall()

    data = []
    for row in rows:
        data.append({
            "order_id": row[0],
            "driver": {
                "driver_id": row[1],
                "name": row[2],
                "rating": row[3]
            },
            "passenger": {
                "passenger_id": row[4],
                "name": row[5],
                "rating": row[6]
            },
            "order_details": {
                "delivery_address": row[7],
                "final_address": row[8],
                "time_order": row[9],
                "price": row[10],
                "distance_km": row[11]
            }
        })

    os.makedirs("out", exist_ok=True)

    json_path = "out/DuberBuber.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ Данные экспортированы в JSON: {json_path}")

    csv_path = "out/DuberBuber.csv"
    with open(csv_path, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "order_id", "driver_id", "driver_name", "driver_rating",
            "passenger_id", "passenger_name", "passenger_rating",
            "delivery_address", "final_address", "time_order", "price",
            "distance_km"
        ])
        writer.writeheader()
        for d in data:
            writer.writerow({
                "order_id": d["order_id"],
                "driver_id": d["driver"]["driver_id"],
                "driver_name": d["driver"]["name"],
                "driver_rating": d["driver"]["rating"],
                "passenger_id": d["passenger"]["passenger_id"],
                "passenger_name": d["passenger"]["name"],
                "passenger_rating": d["passenger"]["rating"],
                "delivery_address": d["order_details"]["delivery_address"],
                "final_address": d["order_details"]["final_address"],
                "time_order": d["order_details"]["time_order"],
                "price": d["order_details"]["price"],
                "distance_km": d["order_details"]["distance_km"],
            })
    print(f"✓ Данные экспортированы в CSV: {csv_path}")

    xml_path = "out/DuberBuber.xml"
    root = ET.Element("orders")
    for d in data:
        order_elem = ET.SubElement(root, "order")
        ET.SubElement(order_elem, "order_id").text = str(d["order_id"])

        driver_elem = ET.SubElement(order_elem, "driver")
        ET.SubElement(driver_elem, "driver_id").text = str(d["driver"]["driver_id"])
        ET.SubElement(driver_elem, "name").text = str(d["driver"]["name"])
        ET.SubElement(driver_elem, "rating").text = str(d["driver"]["rating"])

        passenger_elem = ET.SubElement(order_elem, "passenger")
        ET.SubElement(passenger_elem, "passenger_id").text = str(d["passenger"]["passenger_id"])
        ET.SubElement(passenger_elem, "name").text = str(d["passenger"]["name"])
        ET.SubElement(passenger_elem, "rating").text = str(d["passenger"]["rating"])

        order_details_elem = ET.SubElement(order_elem, "order_details")
        ET.SubElement(order_details_elem, "delivery_address").text = str(d["order_details"]["delivery_address"])
        ET.SubElement(order_details_elem, "final_address").text = str(d["order_details"]["final_address"])
        ET.SubElement(order_details_elem, "time_order").text = str(d["order_details"]["time_order"])
        ET.SubElement(order_details_elem, "price").text = str(d["order_details"]["price"])
        ET.SubElement(order_details_elem, "distance_km").text = str(d["order_details"]["distance_km"])

    tree = ET.ElementTree(root)
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)
    print(f"✓ Данные экспортированы в XML: {xml_path}")

    yaml_path = "out/DuberBuber.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)
    print(f"✓ Данные экспортированы в YAML: {yaml_path}")

    print(f"\n📁 Все файлы сохранены в папке 'out/'")
    print(f"📊 Всего экспортировано заказов: {len(data)}")


if __name__ == "__main__":
    main()