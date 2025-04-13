from flask import Flask, redirect, render_template, jsonify, request, session, flash, url_for
import stripe
from forms import RegisterForm, LoginForm, AddProductForm
from email_validator import validate_email, EmailNotValidError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String
import os
from flask_bootstrap import Bootstrap
import smtplib

stripe.api_key = os.getenv('SECRET KEY')
DOMAIN = 'http://localhost:5001'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'SECRET KEY'
bootstrap = Bootstrap(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(Perdoruesit, user_id)


# ------------------------------------------------DATABASE--------------------------------------------------------------
class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URI', 'sqlite:///perdoruesit.db')
db = SQLAlchemy(model_class=Base)
db.init_app(app)


class Perdoruesit(db.Model, UserMixin):
    __tablename__ = "Perdoruesit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(250), nullable=False)


with app.app_context():
    db.create_all()


# ----------------------------------------------USER HANDLING-----------------------------------------------------------
@app.route('/create-admin')
def create_admin():
    # Prevent re-creation if user already exists
    input_email = "admin@gmail.com"
    input_password = "12345678"
    input_name = "Admin"
    input_role = "admin"

    existing_user = db.session.execute(
        db.select(Perdoruesit).where(Perdoruesit.email == input_email)
    ).scalar()

    if existing_user:
        return "Admin user already exists."

    hashed_password = generate_password_hash(input_password, method='pbkdf2:sha256', salt_length=8)
    new_user = Perdoruesit(
        email=input_email,
        password=hashed_password,
        name=input_name,
        role=input_role
    )

    db.session.add(new_user)
    db.session.commit()
    login_user(new_user)

    return "Admin user created successfully."


@app.route('/', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            validate_email(form.email.data)
            user = db.session.execute(db.select(Perdoruesit).where(Perdoruesit.email == form.email.data)).scalar()
            if user:
                flash("You've already signed up with that email, log in instead!")
                return redirect(url_for("login"))

            hash_salted_password = generate_password_hash(
                form.password.data,
                method='pbkdf2:sha256',
                salt_length=8
            )
            new_user = Perdoruesit(
                email=form.email.data,
                password=hash_salted_password,
                name=form.name.data,
                role=form.role.data
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for("home"))
        except EmailNotValidError as e:
            flash(str(e), "error")
            return redirect(url_for("register"))
    return render_template("register.html", form=form, current_user=current_user)



@app.route('/login', methods=["POST", "GET"])
def login():
    form = LoginForm()
    email = form.email.data
    password = form.password.data
    if form.validate_on_submit():
        user = db.session.execute(db.select(Perdoruesit).where(Perdoruesit.email == email)).scalar()
        if not user:
            flash("This email does not exist, please try again or go to the register page.")
            return redirect(url_for("login"))
        elif not check_password_hash(user.password, password):
            flash("Incorrect password, please try again.")
            return redirect(url_for("login"))
        else:
            login_user(user)
            return redirect(url_for("home"))
    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('register'))


# ------------------------------------------FUNCTIONS REGARDING PRODUCTS------------------------------------------------

@app.route('/produktet-e-tua', methods=["GET", "POST"])
def produktet_fermer():
    try:
        # Fetch products and prices from Stripe
        products = stripe.Product.list()
        prices = stripe.Price.list()

        products_data = []

        # Filter products by category
        for product in products['data']:
            if not product.get('active', True):
                continue
                # Get all prices for this product
            product_prices = [p for p in prices['data'] if p['product'] == product['id']]

            if not product_prices:
                continue

            # Sort prices by creation date (newest first)
            latest_price = sorted(product_prices, key=lambda p: p['created'], reverse=True)[0]

            # Check if product belongs to current farmer
            if product['metadata'].get('Fermeri', '') == current_user.name:
                products_data.append({
                    'id': product['id'],
                    'name': product['name'],
                    'description': product['description'],
                    'image': product['images'][0] if product['images'] else None,
                    'price': latest_price['unit_amount'] / 100,
                    'category': product['metadata'].get('Category', 'Uncategorized'),
                    'price_id': latest_price['id']
                })

        if request.method == 'POST':
            action = request.form.get('action')
            product_id = request.form.get('product_id')

            if action == 'delete':
                stripe.Product.modify(product_id, active=False)
                return redirect('/produktet-e-tua')

            if action == 'edit':
                new_price = request.form.get('new_price')
                price_id = request.form.get('price_id')

                # Create a new price object with the updated price
                new_price = float(new_price) * 100  # Convert to cents
                new_price_obj = stripe.Price.create(
                    product=product_id,
                    unit_amount=int(new_price),
                    currency="ALL"
                )

                for product in products_data:
                    if product['id'] == product_id:
                        product['price'] = new_price / 100

                return redirect('/produktet-e-tua')

        return render_template('produkte-fermer.html', products=products_data, current_user=current_user)

    except Exception as e:
        return f"Error: {str(e)}"


@app.route('/shto-produkt', methods=["GET", "POST"])
def add_product():
    form = AddProductForm()

    if form.validate_on_submit():
        try:
            # Create the product on Stripe
            product = stripe.Product.create(
                name=form.name.data,
                description=form.description.data,
                image=[],
                metadata={
                    'Category': form.category.data,
                    'Fermeri': current_user.name
                }
            )

            # Create a price for the product
            stripe.Price.create(
                product=product.id,
                unit_amount=form.price.data * 100,  # Stripe expects cents
                currency="ALL"
            )

            flash("Produkti u shtua me sukses në Stripe!", "success")
            return redirect(url_for('produktet_fermer'))

        except Exception as e:
            flash(f"Gabim gjatë shtimit të produktit: {str(e)}", "danger")

    return render_template('shto-produkt.html', form=form)


@app.route('/kerko', methods=['GET', 'POST'])
def search_by_name():
    try:
        search_query = request.args.get('q', '').lower()

        # Fetch products and prices from Stripe
        products = stripe.Product.list()
        prices = stripe.Price.list()

        products_data = []
        for product in products['data']:
            if not product.get('active', True):
                continue

            # Filter by search query if present
            if search_query and search_query not in product['name'].lower():
                continue

            # Find price for this product
            price_data = next((price for price in prices['data'] if price['product'] == product['id']), None)
            if price_data:
                products_data.append({
                    'id': product['id'],
                    'name': product['name'],
                    'description': product['description'],
                    'image': product['images'][0] if product['images'] else None,
                    'price': price_data['unit_amount'] / 100,
                    'category': product['metadata'].get('Category', 'Uncategorized')
                })

        return render_template('index.html', products=products_data, current_user=current_user, search_query=search_query)
    except Exception as e:
        return f"Error: {str(e)}"


# ----------------------------------------------ADMIN FUNCTIONS---------------------------------------------------------
@app.route('/perdoruesit')
def perdoruesit():
    result = db.session.execute(db.select(Perdoruesit))
    all_users = result.scalars().all()
    return render_template("perdoruesit.html", users=all_users, current_user=current_user)


@app.route('/fshi-llogarine/<int:id>')
def fshi_llogarine(id):
    user_to_delete = db.get_or_404(Perdoruesit, id)
    if user_to_delete.role == 'Fermer':
        try:
            # Fetch products and prices from Stripe
            products = stripe.Product.list()
            prices = stripe.Price.list()

            products_data = []

            # Filter products by category
            for product in products['data']:
                if not product.get('active', True):
                    continue
                    # Get all prices for this product
                product_prices = [p for p in prices['data'] if p['product'] == product['id']]

                if not product_prices:
                    continue

                # Sort prices by creation date (newest first)
                latest_price = sorted(product_prices, key=lambda p: p['created'], reverse=True)[0]

                # Check if product belongs to current farmer
                if product['metadata'].get('Fermeri', '') == user_to_delete.name:
                    products_data.append({
                        'id': product['id'],
                        'name': product['name'],
                        'description': product['description'],
                        'image': product['images'][0] if product['images'] else None,
                        'price': latest_price['unit_amount'] / 100,
                        'category': product['metadata'].get('Category', 'Uncategorized'),
                        'price_id': latest_price['id']
                    })
                    stripe.Product.modify(product.id, active=False)
        except Exception as e:
            return f"Error: {str(e)}"
    db.session.delete(user_to_delete)
    db.session.commit()
    return redirect(url_for('perdoruesit'))


@app.route('/shiko-produktet/<string:name>')
def shiko_produktet(name):
    try:
        # Fetch products and prices from Stripe
        products = stripe.Product.list()
        prices = stripe.Price.list()

        products_data = []

        # Filter products by category
        for product in products['data']:
            if not product.get('active', True):
                continue
                # Get all prices for this product
            product_prices = [p for p in prices['data'] if p['product'] == product['id']]

            if not product_prices:
                continue

            # Sort prices by creation date (newest first)
            latest_price = sorted(product_prices, key=lambda p: p['created'], reverse=True)[0]

            # Check if product belongs to current farmer
            if product['metadata'].get('Fermeri', '') == name:
                products_data.append({
                    'id': product['id'],
                    'name': product['name'],
                    'description': product['description'],
                    'image': product['images'][0] if product['images'] else None,
                    'price': latest_price['unit_amount'] / 100,
                    'category': product['metadata'].get('Category', 'Uncategorized'),
                    'price_id': latest_price['id']
                })

    except Exception as e:
        return f"Error: {str(e)}"
    return render_template("produktet-admin.html", products=products_data, farmer=name)


# ----------------------------------------------WEB MAIN PAGES----------------------------------------------------------
@app.route('/home')
def home():
    return render_template('index.html', current_user=current_user)


@app.route('/produkte_bulmeti')
def produkte_bulmeti():
    try:
        # Fetch products from Stripe
        products = stripe.Product.list()
        prices = stripe.Price.list()

        # Filter products by category
        products_data = []
        for product in products['data']:
            if not product.get('active', True):
                continue
            # Find the price for this product
            price_data = next((price for price in prices['data'] if price['product'] == product['id']), None)
            if price_data and product['metadata'].get('Category', '') == 'Bulmet':
                products_data.append({
                    'id': product['id'],
                    'name': product['name'],
                    'description': product['description'],
                    'image': product['images'][0] if product['images'] else None,
                    'price': price_data['unit_amount'] / 100,
                    'category': product['metadata'].get('Category', 'Uncategorized')
                })

        return render_template('produkte-bulmeti.html', products=products_data, current_user=current_user)
    except Exception as e:
        return f"Error: {str(e)}"


@app.route('/produkte_shtazore')
def produkte_shtazore():
    try:
        # Fetch products from Stripe
        products = stripe.Product.list()
        prices = stripe.Price.list()

        # Filter products by category
        products_data = []
        for product in products['data']:
            if not product.get('active', True):
                continue
            # Find the price for this product
            price_data = next((price for price in prices['data'] if price['product'] == product['id']), None)
            if price_data and product['metadata'].get('Category', '') == 'Shtazore':
                products_data.append({
                    'id': product['id'],
                    'name': product['name'],
                    'description': product['description'],
                    'image': product['images'][0] if product['images'] else None,
                    'price': price_data['unit_amount'] / 100,
                    'category': product['metadata'].get('Category', 'Uncategorized')
                })

        return render_template('produkte-shtazore.html', products=products_data, current_user=current_user)
    except Exception as e:
        return f"Error: {str(e)}"


@app.route('/fruta')
def fruta():
    try:
        # Fetch products from Stripe
        products = stripe.Product.list()
        prices = stripe.Price.list()

        # Filter products by category
        products_data = []
        for product in products['data']:
            if not product.get('active', True):
                continue
            # Find the price for this product
            price_data = next((price for price in prices['data'] if price['product'] == product['id']), None)
            if price_data and product['metadata'].get('Category', '') == 'Fruta':
                products_data.append({
                    'id': product['id'],
                    'name': product['name'],
                    'description': product['description'],
                    'image': product['images'][0] if product['images'] else None,
                    'price': price_data['unit_amount'] / 100,
                    'category': product['metadata'].get('Category', 'Uncategorized')
                })

        return render_template('fruta.html', products=products_data, current_user=current_user)
    except Exception as e:
        return f"Error: {str(e)}"


@app.route('/perime')
def perime():
    try:
        # Fetch products from Stripe
        products = stripe.Product.list()
        prices = stripe.Price.list()

        # Filter products by category
        products_data = []
        for product in products['data']:
            if not product.get('active', True):
                continue
            # Find the price for this product
            price_data = next((price for price in prices['data'] if price['product'] == product['id']), None)
            if price_data and product['metadata'].get('Category', '') == 'Perime':
                products_data.append({
                    'id': product['id'],
                    'name': product['name'],
                    'description': product['description'],
                    'image': product['images'][0] if product['images'] else None,
                    'price': price_data['unit_amount'] / 100,
                    'category': product['metadata'].get('Category', 'Uncategorized')
                })

        return render_template('perime.html', products=products_data, current_user=current_user)
    except Exception as e:
        return f"Error: {str(e)}"


@app.route('/pije')
def pije():
    try:
        # Fetch products from Stripe
        products = stripe.Product.list()
        prices = stripe.Price.list()

        # Filter products by category
        products_data = []
        for product in products['data']:
            if not product.get('active', True):
                continue
            # Find the price for this product
            price_data = next((price for price in prices['data'] if price['product'] == product['id']), None)
            if price_data and product['metadata'].get('Category', '') == 'Pije':
                products_data.append({
                    'id': product['id'],
                    'name': product['name'],
                    'description': product['description'],
                    'image': product['images'][0] if product['images'] else None,
                    'price': price_data['unit_amount'] / 100,
                    'category': product['metadata'].get('Category', 'Uncategorized')
                })

        return render_template('pije.html', products=products_data, current_user=current_user)
    except Exception as e:
        return f"Error: {str(e)}"


@app.route('/tjera')
def tjera():
    try:
        # Fetch products from Stripe
        products = stripe.Product.list()
        prices = stripe.Price.list()

        # Filter products by category
        products_data = []
        for product in products['data']:
            if not product.get('active', True):
                continue
            # Find the price for this product
            price_data = next((price for price in prices['data'] if price['product'] == product['id']), None)
            if price_data and product['metadata'].get('Category', '') == 'Tjera':
                products_data.append({
                    'id': product['id'],
                    'name': product['name'],
                    'description': product['description'],
                    'image': product['images'][0] if product['images'] else None,
                    'price': price_data['unit_amount'] / 100,
                    'category': product['metadata'].get('Category', 'Uncategorized')
                })

        return render_template('tjera.html', products=products_data, current_user=current_user)
    except Exception as e:
        return f"Error: {str(e)}"

# -------------------------------------------------CART-----------------------------------------------------------------
@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    # Get product details from the form
    product_id = request.form.get('product_id')
    product_name = request.form.get('name')
    product_price = float(request.form.get('price'))
    quantity = int(request.form.get('quantity', 1))

    # Initialize cart if not already in session
    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']

    # If the product is already in the cart, update the quantity and total
    if product_id in cart:
        cart[product_id]['quantity'] += quantity
        cart[product_id]['total_price'] = cart[product_id]['quantity'] * product_price
    else:
        # Add new product to the cart
        cart[product_id] = {
            'name': product_name,
            'price': product_price,
            'quantity': quantity,
            'total_price': quantity * product_price,
        }

    # Save cart back to session
    session['cart'] = cart
    return redirect('/cart')  # Redirect to the cart page


@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    total_price = sum(item['total_price'] for item in cart.values())
    return render_template('cart.html', cart=cart, total_price=total_price)


@app.route('/remove-from-cart', methods=['POST'])
def remove_from_cart():
    product_id = request.form.get('product_id')

    # Check if the cart exists in the session
    if 'cart' in session and product_id in session['cart']:
        # Remove the product from the cart
        session['cart'].pop(product_id, None)

        # Save changes back to the session
        session.modified = True  # Ensure the session updates

    return redirect('/cart')  # Redirect back to the cart page


# -------------------------------------------------STRIPE---------------------------------------------------------------
@app.route('/checkout')
def checkout():
    cart = session.get('cart', {})
    if not cart:
        return redirect('/cart')  # Redirect back to cart if it's empty
    total_price = sum(item['total_price'] for item in cart.values())
    return render_template('checkout.html', cart=cart, total_price=total_price)


def get_stripe_price_id(product_name):
    # Fetch all products from Stripe
    products = stripe.Product.list()

    # Find the product by name
    for product in products['data']:
        if product['name'] == product_name:
            # Fetch prices for the product
            prices = stripe.Price.list(product=product['id'])
            # Return the first Price ID (or match based on your logic)
            if prices['data']:
                return prices['data'][0]['id']

    return None


@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        # Fetch the cart from the session
        cart = session.get('cart', {})

        # Create line items for Stripe Checkout
        line_items = []
        for item in cart.values():
            price_id = get_stripe_price_id(item['name'])
            if not price_id:
                return jsonify({'error': f'Price ID not found for {item["name"]}'}), 400

            line_items.append({
                'price': price_id,
                'quantity': item['quantity'],
            })

            # Get farmer's name
            price_data = stripe.Price.retrieve(price_id)
            product_id = price_data['product']
            product_data = stripe.Product.retrieve(product_id)
            farmer = product_data['metadata'].get('Fermeri', 'Uncategorized')

            farmer_email = db.session.query(Perdoruesit).filter(Perdoruesit.name == farmer).first().email

            with smtplib.SMTP("smtp.gmail.com", port=587) as connection:
                connection.starttls()
                connection.login(user="admin@gmail.com", password="12345678")
                connection.sendmail(
                    from_addr="admin@gmail.com",
                    to_addrs=farmer_email,
                    msg=f"Subject: Kërkesë: Porosi e re!\n\nPërshëndetje {farmer}! Përgatisni porosinë e mëposhtme:\n{item['quantity']} {product_data['name']}\n për adresën {current_user.email}"
                )

        # Create Stripe Checkout Session
        stripe_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=DOMAIN + '/success',
            cancel_url=DOMAIN + '/cancel',
        )

        return jsonify({'url': stripe_session.url})

    except Exception as e:
        # Log the error for debugging
        print(f"Error creating Checkout Session: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/success', methods=['GET'])
def success():
    session_id = request.args.get('session_id')
    stripe_session = stripe.checkout.Session.retrieve(session_id)

    return render_template('success.html', session=stripe_session)


@app.route('/session-status', methods=['GET'])
def session_status():
  session = stripe.checkout.Session.retrieve(request.args.get('session_id'))
  return jsonify(status=session.status, customer_email=session.customer_details.email)


@app.route('/clear-cart', methods=['POST'])
def clear_cart():
    session.pop('cart', None)
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True, port=5001)