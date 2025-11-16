import os
import sqlite3
import json
import csv
import yaml
import xml.etree.ElementTree as ET


def main():
    DB_NAME = "DuberBuber.db"
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.executescript("""
    DROP TABLE IF EXISTS Notification;
    DROP TABLE IF EXISTS Orders;
    DROP TABLE IF EXISTS About_orders;
    DROP TABLE IF EXISTS Drivers;
    DROP TABLE IF EXISTS Passengers;

    CREATE TABLE Drivers (
        Driver_id INTEGER PRIMARY KEY,
        Username TEXT,
        Rating REAL
    );

    CREATE TABLE Passengers (
        Passenger_id INTEGER PRIMARY KEY,
        Username TEXT,
        Rating REAL
    );

    CREATE TABLE About_orders (
        About_orders_id INTEGER PRIMARY KEY,
        Delivery_address TEXT,
        Time_order TEXT,
        Price REAL,
        Final_address TEXT,
        Distance_km BOOLEAN
    );

    CREATE TABLE Orders (
        Orders_id INTEGER PRIMARY KEY,
        Driver_id INTEGER,
        Passenger_id INTEGER,
        About_orders_id INTEGER,
        FOREIGN KEY(Driver_id) REFERENCES Drivers(Driver_id),
        FOREIGN KEY(Passenger_id) REFERENCES Passengers(Passenger_id),
        FOREIGN KEY(About_orders_id) REFERENCES About_orders(About_orders_id)
    );

    CREATE TABLE Notification (
        notification_id INTEGER PRIMARY KEY,
        Drivers_id INTEGER,
        message TEXT,
        FOREIGN KEY(Drivers_id) REFERENCES Drivers(Driver_id)
    );
    """)

    Drivers = [
        (1, "Славка Андрей Владиславович", 2.3),
        (2, "Капитанов Иван Александрович", 4.7),
        (3, "Хороших Егор Эдуардович", 3.6)
    ]
    Passengers = [
        (1, "Раева Кира Сергеевна", 4.3),
        (2, "Галкин Илья Алексеевич", 5.0),
        (3, "Боярсков Павел Владиславович", 2.8)
    ]
    About_orders = [
        (1, "Ул. Красная Поляна, д. 2, подъезд 1", "15:06", 654, "Ул. Бурнаковская, д. 75", 1.9),
        (2, "Ул. Осипенко, д. 82", "19:59", 427, "Ул. Нижневолжсая, д. 19", 5.0),
        (3, "Ул. Минина, д. 24", "6:44", 987, "Ул. Рожденственская, д 10", 2.8)
    ]
    Orders = [
        (1, 2, 3, 2),
        (2, 1, 1, 1),
        (3, 3, 2, 3)
    ]
    notifications = [
        (1, 1, "Ваше такси подъезжает!"),
        (2, 2, "Ваше такси подъезжает!"),
        (3, 3, "Ваше такси подъезжает!")
    ]

    cursor.executemany("INSERT INTO Drivers VALUES (?, ?, ?)", Drivers)
    cursor.executemany("INSERT INTO Passengers VALUES (?, ?, ?)", Passengers)
    cursor.executemany("INSERT INTO About_orders VALUES (?, ?, ?, ?, ?, ?)", About_orders)
    cursor.executemany("INSERT INTO Orders VALUES (?, ?, ?, ?)", Orders)
    cursor.executemany("INSERT INTO Notification VALUES (?, ?, ?)", notifications)

    conn.commit()

    cursor.execute("""
    SELECT O.Orders_id, D.Driver_id, D.Username, D.Rating, P.Passenger_id, P.Username, P.Rating, 
           A.Delivery_address, A.Final_address, A.Time_order, A.Price, A.Distance_km
    FROM Orders O
    JOIN Drivers D ON O.Driver_id = D.Driver_id
    JOIN Passengers P ON O.Passenger_id = P.Passenger_id
    JOIN About_orders A ON O.About_orders_id = A.About_orders_id
    LEFT JOIN Notification N ON D.Driver_id = N.Drivers_id
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

    with open("out/DuberBuber.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    with open("out/DuberBuber.csv", "w", newline='', encoding="utf-8") as f:
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
    tree.write("out/DuberBuber.xml", encoding="utf-8", xml_declaration=True)

    with open("out/DuberBuber.yaml", "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    conn.close()

if __name__ == "__main__":
    main()