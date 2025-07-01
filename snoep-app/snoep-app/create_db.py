import sqlite3
import os
from werkzeug.security import generate_password_hash

db_path = "instance/business.db"
os.makedirs("instance", exist_ok=True)

if os.path.exists(db_path):
    os.remove(db_path)
    print("🧹 Oude database verwijderd.")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE product (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    stock INTEGER NOT NULL
)
""")

cursor.execute("""
CREATE TABLE "order" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    date DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_price REAL,
    FOREIGN KEY (user_id) REFERENCES user(id)
)
""")

cursor.execute("""
CREATE TABLE order_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    FOREIGN KEY (order_id) REFERENCES "order"(id),
    FOREIGN KEY (product_id) REFERENCES product(id)
)
""")

# Voorbeeldadmin met gehashed wachtwoord
hashed_password = generate_password_hash("admin123")
cursor.execute("INSERT INTO user (email, password_hash, is_admin) VALUES (?, ?, ?)",
               ("admin@example.com", hashed_password, 1))

# Voorbeeldproducten
cursor.execute("INSERT INTO product (name, price, stock) VALUES (?, ?, ?)",
               ("Chips", 1.5, 100))
cursor.execute("INSERT INTO product (name, price, stock) VALUES (?, ?, ?)",
               ("Cola", 1.2, 80))

conn.commit()
conn.close()

print("✅ Database aangemaakt met tabellen: user, product, order, order_item.")
