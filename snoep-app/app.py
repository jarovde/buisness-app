from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'jouw-secret-key-hier'  # Zet een veilige sleutel!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///business.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Models ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    total_price = db.Column(db.Float)
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer)
    product = db.relationship('Product')

# --- Decorators ---

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Je moet ingelogd zijn om deze pagina te bekijken.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = None
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('Alleen admins mogen hier komen.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('E-mail al in gebruik.', 'danger')
            return redirect(url_for('register'))
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registratie gelukt! Je kunt nu inloggen.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            flash('Succesvol ingelogd!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Ongeldige login.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Uitgelogd.', 'info')
    return redirect(url_for('index'))

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', product=product)

@app.route('/order', methods=['POST'])
@login_required
def order():
    try:
        product_id = int(request.form['product_id'])
        quantity = int(request.form['quantity'])
    except (ValueError, KeyError):
        flash('Ongeldige invoer.', 'danger')
        return redirect(url_for('index'))

    product = Product.query.get_or_404(product_id)
    if quantity <= 0:
        flash('Ongeldige hoeveelheid.', 'danger')
        return redirect(url_for('index'))
    if product.stock < quantity:
        flash(f'Niet genoeg voorraad. Huidige voorraad: {product.stock}', 'danger')
        return redirect(url_for('index'))

    # Maak bestelling
    order = Order(user_id=session['user_id'], total_price=product.price * quantity)
    db.session.add(order)
    db.session.flush()  # om order.id te krijgen

    order_item = OrderItem(order_id=order.id, product_id=product.id, quantity=quantity)
    product.stock -= quantity

    db.session.add(order_item)
    db.session.commit()
    flash('Bestelling geplaatst! Dank je wel.', 'success')
    return redirect(url_for('index'))

@app.route('/admin')
@admin_required
def admin():
    products = Product.query.all()
    orders = Order.query.order_by(Order.date.desc()).limit(10).all()
    return render_template('admin.html', products=products, orders=orders)

@app.route('/admin/add_product', methods=['POST'])
@admin_required
def add_product():
    try:
        name = request.form['name']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
    except (ValueError, KeyError):
        flash('Ongeldige invoer bij toevoegen product.', 'danger')
        return redirect(url_for('admin'))

    product = Product(name=name, price=price, stock=stock)
    db.session.add(product)
    db.session.commit()
    flash('Product toegevoegd!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/update_stock/<int:product_id>', methods=['POST'])
@admin_required
def update_stock(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        new_stock = int(request.form['stock'])
    except ValueError:
        flash('Ongeldige voorraadwaarde.', 'danger')
        return redirect(url_for('admin'))
    product.stock = new_stock
    db.session.commit()
    flash('Voorraad bijgewerkt!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/sales_data')
@admin_required
def sales_data():
    today = datetime.date.today()
    dates = []
    counts = []
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        count = Order.query.filter(db.func.date(Order.date) == day).count()
        dates.append(day.strftime("%Y-%m-%d"))
        counts.append(count)
    return jsonify({'dates': dates, 'counts': counts})
@app.route('/whoami')
def whoami():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return f"Je bent ingelogd als {user.email}, admin? {user.is_admin}"
    else:
        return "Niet ingelogd"

# --- Run app ---

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False, host='0.0.0.0')
