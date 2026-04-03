# 🌸 Happiness Store

A full-featured kawaii e-commerce web application built with Flask, PostgreSQL, and TailwindCSS. Deployable on Render in minutes.

---

## 🚀 Quick Start (Local)

```bash
# 1. Clone & enter directory
cd happiness_store

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run locally (uses SQLite)
python app.py
# Visit: http://localhost:10000
```

**Default Admin credentials:**
- URL: `http://localhost:10000/admin`
- Username: `admin`
- Password: `happiness2024`

---

## ☁️ Deploy on Render

### Option A — Using render.yaml (Recommended)

1. Push this project to a GitHub repository
2. Go to [render.com](https://render.com) → New → Blueprint
3. Connect your GitHub repo — Render auto-reads `render.yaml`
4. Done! Render creates both the web service and PostgreSQL DB.

### Option B — Manual Setup

**Step 1: Create PostgreSQL Database**
- Render Dashboard → New → PostgreSQL
- Name: `happiness-db`, Plan: Free
- Copy the **Internal Database URL**

**Step 2: Create Web Service**
- New → Web Service → Connect your GitHub repo
- Settings:
  - **Environment:** Python 3
  - **Build Command:** `pip install -r requirements.txt`
  - **Start Command:** `gunicorn app:app`

**Step 3: Environment Variables**
Add these in your web service's Environment tab:

| Variable | Value |
|---|---|
| `DATABASE_URL` | (paste your PostgreSQL Internal URL) |
| `SECRET_KEY` | (any long random string) |
| `ADMIN_USERNAME` | `admin` |
| `ADMIN_PASSWORD` | `your_secure_password` |

**Optional — Cloudinary Image Hosting:**
| Variable | Value |
|---|---|
| `CLOUDINARY_URL` | `cloudinary://api_key:api_secret@cloud_name` |

---

## 📁 Project Structure

```
happiness_store/
├── app.py                  # Main Flask application
├── models.py               # SQLAlchemy database models
├── requirements.txt        # Python dependencies
├── render.yaml             # Render deployment config
├── Procfile                # Gunicorn start command
├── templates/
│   ├── base.html           # Base layout with navbar & footer
│   ├── home.html           # Homepage with hero, featured, trending
│   ├── product.html        # Product detail with gallery & variants
│   ├── shop.html           # Full shop with filters
│   ├── cart.html           # Shopping cart
│   ├── checkout.html       # Checkout form
│   ├── order_success.html  # Order confirmation
│   ├── surprise.html       # Surprise Box feature
│   ├── bundles.html        # Bundles listing
│   ├── mix_match.html      # Mix & Match feature
│   └── admin/
│       ├── base_admin.html # Admin sidebar layout
│       ├── login.html      # Admin login
│       ├── dashboard.html  # Stats & recent orders
│       ├── products.html   # Product list
│       ├── product_form.html  # Add/Edit product
│       ├── orders.html     # Order management
│       ├── order_detail.html  # Order detail view
│       ├── bundles.html    # Bundle management
│       └── bundle_form.html   # Create bundle
└── static/
    └── images/
        └── placeholder.svg
```

---

## 🛍️ Features

### Customer-Facing
- 🏠 **Homepage** — Hero, featured products, trending, bundles
- 🔍 **Live Search** — Instant product search in navbar
- 🛍️ **Shop** — Filter by category, search, sort by price/newest
- 📦 **Product Pages** — Image gallery, color/size variants, quantity
- 🛒 **Cart** — Add/remove/update items, free shipping threshold
- ✅ **Checkout** — Customer info form, order confirmation
- 🎁 **Bundles** — Curated product sets with discounts
- ✨ **Surprise Box** — Random product discovery
- 🎨 **Mix & Match** — Select multiple items interactively

### Admin Panel (`/admin`)
- 📊 **Dashboard** — Revenue, orders, product stats
- 📦 **Products** — Add/Edit/Delete, toggle availability
- 🖼️ **Images** — Upload files or paste URLs (Cloudinary optional)
- 🎨 **Variants** — Color & size combinations
- 📋 **Orders** — Status management (Pending/Shipped/Delivered/Cancelled)
- 🎁 **Bundles** — Create product bundles with discount %

---

## 🔐 Security Notes

- Change `ADMIN_PASSWORD` before deploying to production
- Set a strong random `SECRET_KEY`  
- Admin routes are protected with session-based authentication
- Use environment variables — never hardcode secrets

---

## 🗄️ Database Models

| Model | Description |
|---|---|
| `Product` | Main product with flags (featured, trending, surprise) |
| `ProductImage` | Multiple images per product |
| `Variant` | Color/size combinations |
| `Order` | Customer order with status tracking |
| `OrderItem` | Line items with price snapshot |
| `Bundle` | Grouped products with discount |
| `BundleItem` | Products in each bundle |

---

## 🎨 Customization

**Change the color theme** — Edit CSS variables in `base.html`:
```css
:root {
  --pink: #FF6B9D;
  --lavender: #C77DFF;
  --yellow: #FFD93D;
  --mint: #6BCB77;
}
```

**Change admin credentials** — Set environment variables:
```
ADMIN_USERNAME=myadmin
ADMIN_PASSWORD=my_secure_password_123
```

**Enable Cloudinary** — Set `CLOUDINARY_URL` env var and images auto-upload to cloud instead of local disk.
