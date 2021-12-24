import os
import requests
import stripe
from flask import Flask, request, render_template, redirect, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required, AnonymousUserMixin
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)


app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
# Bootstrap(app)


# CONNECTING TO DATABASE
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


login_manager = LoginManager()
login_manager.init_app(app)

# For Anonymous Users who have not logged in.
login_manager.anonymous_user = AnonymousUserMixin

# Stripe

app.config['STRIPE_PUBLIC_KEY']= os.environ.get('STRIPE_PUBLIC_KEY')
app.config['STRIPE_SECRET_KEY'] = os.environ.get('SECRET_TEST_MODE_KEY')
stripe.api_key = os.environ.get('SECRET_TEST_MODE_KEY')


# CREATE TABLES
class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(500), nullable = False)
    size = db.Column(db.String(250), nullable = True)
    price = db.Column(db.String(250), nullable = False)
    image = db.Column(db.String(1000), nullable = False)


class User(db.Model,UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key = True)
    email = db.Column(db.String(250), nullable =False, unique = True)
    name = db.Column(db.String(250), nullable = False)
    password = db.Column(db.String(250), nullable = False)

    items = relationship('Cart', back_populates = 'user')


class Cart(db.Model):
    __tablename__ = 'cart'
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(500), nullable=False)
    size = db.Column(db.String(250), nullable=True)
    price = db.Column(db.String(250), nullable=False)
    image = db.Column(db.String(1000), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = relationship('User', back_populates = 'items')


db.create_all()


@app.route('/')
def home():
    all_products = db.session.query(Product).all()
    return render_template('index.html', products = all_products)


# btn_flag = False
# Show the product
@app.route('/show_product/<int:prod_id>')
def show(prod_id):
    flag = False
    all_products = db.session.query(Product).all()
    prod = db.session.query(Product).get(prod_id)

    if current_user.is_authenticated:
        all_cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    else:
        all_cart_items = []

    # For Add to cart and remove from cart button
    for item in all_cart_items:
        if item.name == prod.name:
            flag = True
            break
        else:
            flag = False
    return render_template('show_product.html', product = prod, products = all_products, btn_flag = flag)


# Registering user
@app.route('/register', methods = ['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['Username']
        email = request.form['email']
        password = request.form['password']

        hashed_pass = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)

        all_registered_user = db.session.query(User).all()

        for user in all_registered_user:
            if user.email == email:
                flash('This Email is already registered. Login Instead!')
                return redirect(url_for('login'))

        new_user = User(email = email, name = username, password = hashed_pass)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


# Logging in user
@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            # flash('Logged in successfully.')
            return redirect(url_for('home'))
        elif not user:
            flash("Email not registered, Sign Up instead")
            return redirect(url_for('register'))
        elif not check_password_hash(user.password, password):
            flash("Email or password incorrect, please try again.")
    return render_template('login.html')


# All items in your cart/Show your cart
@app.route('/your_cart')
def cart():
    all_products = db.session.query(Product).all()

    if current_user.is_authenticated:
        all_cart_items = Cart.query.filter_by(user_id=current_user.id).all()
        print(all_cart_items)
        # Adding price of all items in cart
        numeric_price_list = []

        for item in all_cart_items:
            numeric_price = int(item.price.replace(',',''))
            numeric_price_list.append(numeric_price)
        total_paying_price = sum(numeric_price_list)

        return render_template('cart.html', user_id = current_user.id,products = all_products, all_items =all_cart_items,
                               total_price = total_paying_price)
    else:
        flash('You need to Log in to view cart.')
        return redirect('login')


# Add item in your cart
@app.route('/add_to_cart/<int:prod_id>')
def add_to_cart(prod_id):

    if current_user.is_authenticated:
        product_to_be_added = db.session.query(Product).get(prod_id)
        new_cart_item = Cart(name = product_to_be_added.name,
                             size = product_to_be_added.size,
                             price = product_to_be_added.price,
                             image = product_to_be_added.image,
                             user = current_user)
        db.session.add(new_cart_item)
        db.session.commit()

        all_cart_items = Cart.query.filter_by(user_id = current_user.id).all()

        return redirect(url_for('show', prod_id =product_to_be_added.id))
    else:
        flash('You need to Log in to view cart.')
        return redirect(url_for('login'))


# Delete items from your cart through product id(from show page)
@app.route('/delete_from_cart/<int:prod_id>')
def delete_from_cart(prod_id):

    product_to_be_deleted_from_cart = db.session.query(Product).get(prod_id)
    all_cart_items = Cart.query.filter_by(user_id=current_user.id).all()

    for item in all_cart_items:
        if item.name == product_to_be_deleted_from_cart.name:
            db.session.delete(item)
            db.session.commit()
    return redirect(url_for('show', prod_id=prod_id))


# Delete items from your card using cart_item id(directly from your cart)
@app.route('/remove_from_Cart/<int:item_id>')
def remove_from_cart(item_id):
    item_to_delete = Cart.query.get(item_id)
    db.session.delete(item_to_delete)
    db.session.commit()
    return redirect(url_for('cart'))


# CHECKOUT AND PAYMENT
@app.route('/checkout-page')
def checkout():
    return render_template('checkout.html')


@app.route('/payment_checkout_session')
def payment_checkout():
    all_cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    stripe_product_list = stripe.Product.list()
    stripe_id_list = stripe_product_list["data"]
    prod_list = []
    for item in stripe_id_list:
        prod_name = item['name']
        prod_id = item['id']
        prod_dict = {
            'prod_name': prod_name,
            'prod_id': prod_id
        }
        prod_list.append(prod_dict)

    # All the id of products which are in cart
    prod_id_list = []
    for item in all_cart_items:
        for product in prod_list:
            if item.name == product['prod_name']:
                prod_id_list.append(product['prod_id'])

    # Retrieving price id of the products in cart
    stripe_price_list = stripe.Price.list()
    stripe_price_id_list = stripe_price_list["data"]
    price_list = []
    for item in stripe_price_id_list:
        price_id = item['id']
        product_id = item['product']
        price_dict = {
            'price_id': price_id,
            'product_id': product_id
        }
        price_list.append(price_dict)

    # List of price ids of all the products in cart
    price_ids_final = []
    for item in prod_id_list:
        for price in price_list:
            if item == price['product_id']:
                price_ids_final.append(price['price_id'])

    my_cart_list = []
    for item in price_ids_final:
        price = item
        my_dict = {
            'price': price,
            'quantity': 1
        }
        my_cart_list.append(my_dict)

    session = stripe.checkout.Session.create(
        payment_method_types = ['card'],
        line_items=my_cart_list,
        mode='payment',
        success_url=url_for('success', _external=True)+'?session_id={CHECKOUT_SESSION_ID}',
        cancel_url= url_for('home',_external=True)
    )
    return redirect(session.url, code=303)


@app.route('/success')
def success():
    return render_template('success.html')


# For logging out the user
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
