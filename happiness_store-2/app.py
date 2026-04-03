import os
import json
import random
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, Product, ProductImage, Variant, Order, OrderItem, Bundle, BundleItem
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "happiness-store-secret-2024")

# ── Database ──────────────────────────────────────────────────────────────────
db_url = os.getenv("DATABASE_URL", "")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url if db_url else "sqlite:///happiness.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

db.init_app(app)

# ── Cloudinary (optional) ─────────────────────────────────────────────────────
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL", "")
USE_CLOUDINARY = bool(CLOUDINARY_URL)
if USE_CLOUDINARY:
    import cloudinary
    import cloudinary.uploader
    cloudinary.config(cloudinary_url=CLOUDINARY_URL)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'images', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_image(file):
    """Upload to Cloudinary or local storage."""
    if USE_CLOUDINARY:
        result = cloudinary.uploader.upload(file, folder="happiness_store")
        return result['secure_url']
    else:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filename = secure_filename(file.filename)
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)
        return f"/static/images/uploads/{filename}"

# ── Admin credentials ─────────────────────────────────────────────────────────
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "happiness2024")

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ── Cart helpers ──────────────────────────────────────────────────────────────
def get_cart():
    return session.get('cart', {})

def save_cart(cart):
    session['cart'] = cart
    session.modified = True

def cart_total(cart):
    total = 0
    for key, item in cart.items():
        total += item['price'] * item['quantity']
    return round(total, 2)

def cart_count(cart):
    return sum(i['quantity'] for i in cart.values())

# ── Context processor ─────────────────────────────────────────────────────────
@app.context_processor
def inject_cart():
    cart = get_cart()
    return dict(cart_count=cart_count(cart), cart_total=cart_total(cart))

# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def home():
    featured = Product.query.filter_by(is_featured=True, is_available=True).limit(8).all()
    trending = Product.query.filter_by(is_trending=True, is_available=True).limit(6).all()
    bundles = Bundle.query.filter_by(is_active=True).limit(4).all()
    all_products = Product.query.filter_by(is_available=True).limit(12).all()
    return render_template('home.html',
                           featured=featured,
                           trending=trending,
                           bundles=bundles,
                           all_products=all_products)


@app.route('/product/<int:product_id>')
def product(product_id):
    p = Product.query.get_or_404(product_id)
    colors = list({v.color for v in p.variants if v.color})
    sizes = list({v.size for v in p.variants if v.size})
    related = Product.query.filter(
        Product.id != p.id,
        Product.category == p.category,
        Product.is_available == True
    ).limit(4).all()
    if len(related) < 4:
        extras = Product.query.filter(
            Product.id != p.id,
            Product.is_available == True
        ).limit(4 - len(related)).all()
        related.extend(extras)
    return render_template('product.html', product=p, colors=colors, sizes=sizes, related=related)


@app.route('/shop')
def shop():
    category = request.args.get('category', '')
    search = request.args.get('q', '')
    sort = request.args.get('sort', 'newest')
    query = Product.query.filter_by(is_available=True)
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    if sort == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.created_at.desc())
    products = query.all()
    categories = db.session.query(Product.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    return render_template('shop.html', products=products, categories=categories,
                           current_category=category, search=search, sort=sort)


@app.route('/surprise')
def surprise():
    items = Product.query.filter_by(is_available=True, is_surprise=True).all()
    if not items:
        items = Product.query.filter_by(is_available=True).all()
    pick = random.choice(items) if items else None
    return render_template('surprise.html', product=pick)


@app.route('/bundles')
def bundles_page():
    bundles = Bundle.query.filter_by(is_active=True).all()
    return render_template('bundles.html', bundles=bundles)


@app.route('/mix-match')
def mix_match():
    products = Product.query.filter_by(is_available=True).all()
    return render_template('mix_match.html', products=products)

# ── Cart routes ───────────────────────────────────────────────────────────────

@app.route('/cart')
def cart():
    raw = get_cart()
    items = []
    for key, data in raw.items():
        items.append({
            'key': key,
            'id': data['id'],
            'name': data['name'],
            'price': data['price'],
            'quantity': data['quantity'],
            'image': data.get('image', ''),
            'color': data.get('color', ''),
            'size': data.get('size', ''),
            'subtotal': round(data['price'] * data['quantity'], 2)
        })
    total = cart_total(raw)
    return render_template('cart.html', items=items, total=total)


@app.route('/cart/add', methods=['POST'])
def cart_add():
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', 1, type=int)
    color = request.form.get('color', '')
    size = request.form.get('size', '')
    p = Product.query.get_or_404(product_id)
    cart = get_cart()
    key = f"{product_id}_{color}_{size}"
    if key in cart:
        cart[key]['quantity'] += quantity
    else:
        cart[key] = {
            'id': p.id,
            'name': p.name,
            'price': p.price,
            'quantity': quantity,
            'image': p.primary_image(),
            'color': color,
            'size': size
        }
    save_cart(cart)
    flash(f'"{p.name}" added to cart! 🛍️', 'success')
    return redirect(request.referrer or url_for('cart'))


@app.route('/cart/update', methods=['POST'])
def cart_update():
    key = request.form.get('key')
    qty = request.form.get('quantity', 1, type=int)
    cart = get_cart()
    if key in cart:
        if qty <= 0:
            del cart[key]
        else:
            cart[key]['quantity'] = qty
    save_cart(cart)
    return redirect(url_for('cart'))


@app.route('/cart/remove/<key>')
def cart_remove(key):
    cart = get_cart()
    cart.pop(key, None)
    save_cart(cart)
    return redirect(url_for('cart'))


@app.route('/cart/clear')
def cart_clear():
    save_cart({})
    return redirect(url_for('cart'))

# ── Checkout ──────────────────────────────────────────────────────────────────

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = get_cart()
    if not cart:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('cart'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        notes = request.form.get('notes', '').strip()
        if not name or not address:
            flash('Please fill all required fields.', 'error')
            return redirect(url_for('checkout'))
        total = cart_total(cart)
        order = Order(customer_name=name, customer_email=email,
                      customer_phone=phone, address=address,
                      total_price=total, notes=notes)
        db.session.add(order)
        db.session.flush()
        for key, item in cart.items():
            oi = OrderItem(
                order_id=order.id,
                product_id=item['id'],
                quantity=item['quantity'],
                price_at_time=item['price'],
                variant_color=item.get('color', ''),
                variant_size=item.get('size', '')
            )
            db.session.add(oi)
        db.session.commit()
        save_cart({})
        flash(f'Order #{order.id} placed successfully! 🎉', 'success')
        return redirect(url_for('order_success', order_id=order.id))
    total = cart_total(cart)
    items = list(cart.values())
    return render_template('checkout.html', items=items, total=total)


@app.route('/order/success/<int:order_id>')
def order_success(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('order_success.html', order=order)

# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash('Welcome back! ✨', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials.', 'error')
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


@app.route('/admin')
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    total_products = Product.query.count()
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='Pending').count()
    total_revenue = db.session.query(db.func.sum(Order.total_price)).scalar() or 0
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html',
                           total_products=total_products,
                           total_orders=total_orders,
                           pending_orders=pending_orders,
                           total_revenue=round(total_revenue, 2),
                           recent_orders=recent_orders)


@app.route('/admin/products')
@admin_required
def admin_products():
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('admin/products.html', products=products)


@app.route('/admin/products/add', methods=['GET', 'POST'])
@admin_required
def admin_add_product():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price = request.form.get('price', 0, type=float)
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'general').strip()
        is_featured = bool(request.form.get('is_featured'))
        is_trending = bool(request.form.get('is_trending'))
        is_surprise = bool(request.form.get('is_surprise'))
        if not name or price <= 0:
            flash('Name and valid price required.', 'error')
            return redirect(request.url)
        product = Product(name=name, price=price, description=description,
                          category=category, is_featured=is_featured,
                          is_trending=is_trending, is_surprise=is_surprise)
        db.session.add(product)
        db.session.flush()

        # Images
        images = request.files.getlist('images')
        for img in images:
            if img and allowed_file(img.filename):
                url = upload_image(img)
                db.session.add(ProductImage(url=url, product_id=product.id))

        # Image URLs
        image_urls = request.form.get('image_urls', '').strip()
        for url in image_urls.splitlines():
            url = url.strip()
            if url:
                db.session.add(ProductImage(url=url, product_id=product.id))

        # Variants
        colors = [c.strip() for c in request.form.get('colors', '').split(',') if c.strip()]
        sizes = [s.strip() for s in request.form.get('sizes', '').split(',') if s.strip()]
        for color in colors:
            for size in sizes:
                db.session.add(Variant(color=color, size=size, product_id=product.id))
        if colors and not sizes:
            for color in colors:
                db.session.add(Variant(color=color, product_id=product.id))
        if sizes and not colors:
            for size in sizes:
                db.session.add(Variant(size=size, product_id=product.id))

        db.session.commit()
        flash(f'Product "{name}" added! ✨', 'success')
        return redirect(url_for('admin_products'))
    return render_template('admin/product_form.html', product=None)


@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        product.name = request.form.get('name', '').strip()
        product.price = request.form.get('price', 0, type=float)
        product.description = request.form.get('description', '').strip()
        product.category = request.form.get('category', 'general').strip()
        product.is_featured = bool(request.form.get('is_featured'))
        product.is_trending = bool(request.form.get('is_trending'))
        product.is_surprise = bool(request.form.get('is_surprise'))
        product.is_available = bool(request.form.get('is_available'))

        images = request.files.getlist('images')
        for img in images:
            if img and allowed_file(img.filename):
                url = upload_image(img)
                db.session.add(ProductImage(url=url, product_id=product.id))

        image_urls = request.form.get('image_urls', '').strip()
        for url in image_urls.splitlines():
            url = url.strip()
            if url:
                db.session.add(ProductImage(url=url, product_id=product.id))

        db.session.commit()
        flash('Product updated! ✨', 'success')
        return redirect(url_for('admin_products'))
    colors = ', '.join({v.color for v in product.variants if v.color})
    sizes = ', '.join({v.size for v in product.variants if v.size})
    return render_template('admin/product_form.html', product=product,
                           colors=colors, sizes=sizes)


@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted.', 'success')
    return redirect(url_for('admin_products'))


@app.route('/admin/products/toggle/<int:product_id>')
@admin_required
def admin_toggle_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_available = not product.is_available
    db.session.commit()
    status = 'available' if product.is_available else 'unavailable'
    flash(f'Product marked as {status}.', 'success')
    return redirect(url_for('admin_products'))


@app.route('/admin/products/image/delete/<int:image_id>', methods=['POST'])
@admin_required
def admin_delete_image(image_id):
    img = ProductImage.query.get_or_404(image_id)
    product_id = img.product_id
    db.session.delete(img)
    db.session.commit()
    return redirect(url_for('admin_edit_product', product_id=product_id))


@app.route('/admin/orders')
@admin_required
def admin_orders():
    status = request.args.get('status', '')
    query = Order.query.order_by(Order.created_at.desc())
    if status:
        query = query.filter_by(status=status)
    orders = query.all()
    return render_template('admin/orders.html', orders=orders, current_status=status)


@app.route('/admin/orders/<int:order_id>')
@admin_required
def admin_order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_detail.html', order=order)


@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
@admin_required
def admin_update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status', 'Pending')
    order.status = new_status
    db.session.commit()
    flash(f'Order #{order.id} marked as {new_status}.', 'success')
    return redirect(url_for('admin_orders'))


@app.route('/admin/bundles')
@admin_required
def admin_bundles():
    bundles = Bundle.query.order_by(Bundle.created_at.desc()).all()
    return render_template('admin/bundles.html', bundles=bundles)


@app.route('/admin/bundles/add', methods=['GET', 'POST'])
@admin_required
def admin_add_bundle():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        discount = request.form.get('discount_percent', 0, type=float)
        product_ids = request.form.getlist('product_ids')
        if not name:
            flash('Bundle name required.', 'error')
            return redirect(request.url)
        bundle = Bundle(name=name, description=description, discount_percent=discount)
        db.session.add(bundle)
        db.session.flush()
        for pid in product_ids:
            db.session.add(BundleItem(bundle_id=bundle.id, product_id=int(pid)))
        db.session.commit()
        flash('Bundle created! 🎁', 'success')
        return redirect(url_for('admin_bundles'))
    products = Product.query.filter_by(is_available=True).all()
    return render_template('admin/bundle_form.html', bundle=None, products=products)


@app.route('/admin/bundles/delete/<int:bundle_id>', methods=['POST'])
@admin_required
def admin_delete_bundle(bundle_id):
    bundle = Bundle.query.get_or_404(bundle_id)
    db.session.delete(bundle)
    db.session.commit()
    flash('Bundle deleted.', 'success')
    return redirect(url_for('admin_bundles'))

# ── API endpoints (JSON) ──────────────────────────────────────────────────────

@app.route('/api/cart/count')
def api_cart_count():
    return jsonify({'count': cart_count(get_cart())})


@app.route('/api/products/search')
def api_search():
    q = request.args.get('q', '')
    products = Product.query.filter(
        Product.name.ilike(f'%{q}%'),
        Product.is_available == True
    ).limit(5).all()
    return jsonify([p.to_dict() for p in products])

# ── DB Init ───────────────────────────────────────────────────────────────────

def seed_db():
    """Seed sample products if DB is empty."""
    if Product.query.count() > 0:
        return
    samples = [
        {"name": "Rainbow Plushie Bear", "price": 24.99, "category": "plushies",
         "description": "Super soft rainbow bear plushie, perfect for cuddles and gifting!", "is_featured": True, "is_trending": True},
        {"name": "Pastel Star Lamp", "price": 39.99, "category": "decor",
         "description": "LED star lamp in soft pastel colors. Creates a magical ambiance.", "is_featured": True},
        {"name": "Kawaii Notebook Set", "price": 14.99, "category": "stationery",
         "description": "Set of 3 adorable notebooks with kawaii illustrations.", "is_trending": True},
        {"name": "Bubble Tea Keychain", "price": 8.99, "category": "accessories",
         "description": "Cute resin bubble tea keychain in assorted flavors.", "is_surprise": True},
        {"name": "Cloud Pillow", "price": 29.99, "category": "home",
         "description": "Fluffy cloud-shaped pillow in dreamy white.", "is_featured": True},
        {"name": "Mini Cactus Pot Set", "price": 19.99, "category": "plants",
         "description": "Set of 3 mini ceramic cactus pots. No watering needed!", "is_trending": True},
        {"name": "Strawberry Hair Clips", "price": 6.99, "category": "accessories",
         "description": "Pack of 5 cute strawberry hair clips in pastel colors.", "is_surprise": True},
        {"name": "Glow Moon Jar", "price": 34.99, "category": "decor",
         "description": "Hand-crafted moon jar that glows softly in the dark.", "is_featured": True},
    ]
    image_urls = [
        "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400",
        "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400",
        "https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=400",
        "https://images.unsplash.com/photo-1577563908411-5077b6dc7624?w=400",
        "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=400",
        "https://images.unsplash.com/photo-1509909756405-be0199881695?w=400",
        "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=400",
        "https://images.unsplash.com/photo-1484704849700-f032a568e944?w=400",
    ]
    colors = [['Pink', 'Yellow', 'Blue'], ['Purple', 'White'], ['Mint', 'Lavender', 'Peach'],
              [], ['White', 'Cream'], [], ['Red', 'Pink', 'Yellow'], ['Gold', 'Silver']]
    sizes = [[], [], ['A5', 'A6'], [], [], [], [], []]

    for i, s in enumerate(samples):
        p = Product(**s)
        db.session.add(p)
        db.session.flush()
        db.session.add(ProductImage(url=image_urls[i % len(image_urls)], product_id=p.id))
        for color in colors[i]:
            for size in (sizes[i] if sizes[i] else ['']):
                db.session.add(Variant(color=color, size=size or None, product_id=p.id))
        for size in sizes[i]:
            if not colors[i]:
                db.session.add(Variant(size=size, product_id=p.id))

    # Sample bundle
    db.session.flush()
    bundle = Bundle(name="Happy Home Bundle", description="Everything you need for a cozy, kawaii home!", discount_percent=15)
    db.session.add(bundle)
    db.session.flush()
    for pid in [1, 2, 5, 8]:
        p = Product.query.get(pid)
        if p:
            db.session.add(BundleItem(bundle_id=bundle.id, product_id=p.id))

    db.session.commit()


with app.app_context():
    db.create_all()
    seed_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=False)
