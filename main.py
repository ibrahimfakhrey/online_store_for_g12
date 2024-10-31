from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = 'your_secret_key'

# Initialize the database and Flask-Login
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Redirect users here if not logged in
login_manager.login_message_category = 'info'
# User model
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='customer', nullable=False)

    # Relationships
    orders = db.relationship('Order', back_populates='user', cascade="all, delete-orphan")
    cards = db.relationship('Card', back_populates='user', cascade="all, delete-orphan")
    cart = db.relationship('Cart', back_populates='user', uselist=False, cascade="all, delete-orphan")


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255))
    stock = db.Column(db.Integer, nullable=False)

    # Relationships
    orders = db.relationship('OrderProduct', back_populates='product')
    cart_items = db.relationship('CartItem', back_populates='product')


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date_created = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relationships
    user = db.relationship('User', back_populates='orders')
    products = db.relationship('OrderProduct', back_populates='order', cascade="all, delete-orphan")


class OrderProduct(db.Model):
    __tablename__ = 'order_products'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)

    # Relationships
    order = db.relationship('Order', back_populates='products')
    product = db.relationship('Product', back_populates='orders')


class Card(db.Model):
    __tablename__ = 'cards'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    card_number = db.Column(db.String(20), unique=True, nullable=False)
    card_type = db.Column(db.String(50), nullable=False)
    expiry_date = db.Column(db.String(5), nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='cards')


class CartItem(db.Model):
    __tablename__ = 'cart_items'

    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    # Relationships
    cart = db.relationship('Cart', back_populates='items')
    product = db.relationship('Product', back_populates='cart_items')


class Cart(db.Model):
    __tablename__ = 'cart'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relationships
    user = db.relationship('User', back_populates='cart')
    items = db.relationship('CartItem', back_populates='cart', cascade="all, delete-orphan")
# Flask-Login: Load user
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
@app.route("/")
def start():
    return render_template("index.html")
# Route to register user
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']
        password = request.form['password']

        # Check if email already exists
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists. Please log in.', 'danger')
            return redirect(url_for('login'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(name=name, phone=phone, email=email, password=hashed_password)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('User registered successfully', 'success')
            return redirect(url_for('login'))
        except:
            flash('Error! Something went wrong.', 'danger')
            return redirect(url_for('register'))

    return render_template('register.html')

# Route to log in user
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed. Check your credentials', 'danger')

    return render_template('login.html')


# Route to log out the user
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# Route to view the dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    user_orders = current_user.orders  # Access user's orders
    user_cards = current_user.cards  # Access user's cards
    all_products = Product.query.all()  # Display all products
    return render_template('dashboard.html', orders=user_orders, cards=user_cards, products=all_products)


# Route to create a new product
@app.route('/product/new', methods=['GET', 'POST'])
@login_required
def create_product():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form.get('description', '')
        stock = int(request.form['stock'])

        new_product = Product(name=name, price=price, description=description, stock=stock)
        db.session.add(new_product)
        db.session.commit()
        flash('Product created successfully!')
        return redirect(url_for('dashboard'))
    return render_template('create_product.html')


# Route to create a new order
@app.route('/order/new', methods=['POST'])
@login_required
def create_order():
    product_ids = request.form.getlist('product_ids')  # List of product IDs for the order
    new_order = Order(user_id=current_user.id)
    db.session.add(new_order)
    db.session.commit()

    for product_id in product_ids:
        order_product = OrderProduct(order_id=new_order.id, product_id=product_id)
        db.session.add(order_product)

    db.session.commit()
    flash('Order placed successfully!')
    return redirect(url_for('dashboard'))


# Route to view all orders for the current user
@app.route('/orders')
@login_required
def view_orders():
    user_orders = current_user.orders  # All orders for the logged-in user
    return render_template('orders.html', orders=user_orders)


# Route to add a new payment card
@app.route('/card/new', methods=['GET', 'POST'])
@login_required
def add_card():
    if request.method == 'POST':
        card_number = request.form['card_number']
        card_type = request.form['card_type']
        expiry_date = request.form['expiry_date']

        new_card = Card(user_id=current_user.id, card_number=card_number, card_type=card_type, expiry_date=expiry_date)
        db.session.add(new_card)
        db.session.commit()
        flash('Payment card added successfully!')
        return redirect(url_for('dashboard'))
    return render_template('add_card.html')


# Route to view all payment cards for the current user
@app.route('/cards')
@login_required
def view_cards():
    user_cards = current_user.cards
    return render_template('cards.html', cards=user_cards)


# Route to delete a product
@app.route('/product/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.get(product_id)
    if product:
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully!')
    return redirect(url_for('dashboard'))


# Route to delete an order
@app.route('/order/delete/<int:order_id>', methods=['POST'])
@login_required
def delete_order(order_id):
    order = Order.query.get(order_id)
    if order:
        db.session.delete(order)
        db.session.commit()
        flash('Order deleted successfully!')
    return redirect(url_for('view_orders'))


# Route to delete a payment card
@app.route('/card/delete/<int:card_id>', methods=['POST'])
@login_required
def delete_card(card_id):
    card = Card.query.get(card_id)
    if card:
        db.session.delete(card)
        db.session.commit()
        flash('Card deleted successfully!')
    return redirect(url_for('view_cards'))


@app.route('/cart')
@login_required
def view_cart():
    cart_items = current_user.cart.items if current_user.cart else []
    total = sum(item.product.price * item.quantity for item in cart_items)  # Calculate total
    return render_template('cart.html', items=cart_items, total=total)


# Route to add a product to the cart
@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get(product_id)
    if product:
        # Check if the user has a cart
        if not current_user.cart:  # This checks if the user has a cart
            new_cart = Cart(user_id=current_user.id)
            db.session.add(new_cart)
            db.session.commit()

        # Get the cart ID from the user's cart
        cart_item = CartItem.query.filter_by(cart_id=current_user.cart.id, product_id=product_id).first()
        if cart_item:
            cart_item.quantity += 1  # Increment quantity if item already in cart
        else:
            cart_item = CartItem(cart_id=current_user.cart.id, product_id=product_id, quantity=1)
            db.session.add(cart_item)

        db.session.commit()
        flash('Product added to cart!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    cart_item = CartItem.query.get(item_id)
    if cart_item and cart_item.cart.user_id == current_user.id:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Item removed from cart!', 'info')
    return redirect(url_for('view_cart'))



if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create all tables
    app.run(debug=True)
