# Django E-Commerce Store

A beginner-friendly full-stack e-commerce website using Django, SQLite, HTML5, CSS3 and vanilla JavaScript.

## Features

- Registration, login, logout, profile and password change
- Product catalogue, search, filtering, sorting and pagination
- Product details, multiple images, specifications, ratings and reviews
- Persistent cart and wishlist for logged-in customers
- Coupon validation with minimum order, maximum discount and usage limits
- Address management and multi-step checkout
- Demo payment flow for COD, UPI, card and net banking
- Order history, order details, visual order tracking and cancellation
- Stock reduction and restoration on cancellation
- In-app notifications
- Staff/admin dashboard plus Django admin management
- Sample data command with 5 categories, 15 products, demo user and coupons
- Basic automated tests

## Technology

- Python 3.12+
- Django 6.1.1
- SQLite for development
- HTML5 / CSS3 / vanilla JavaScript
- Pillow for image uploads

## Installation

### Windows PowerShell

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_data
python manage.py runserver
```

### Windows CMD

```cmd
py -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_data
python manage.py runserver
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_data
python manage.py runserver
```

Open http://127.0.0.1:8000/

Admin: http://127.0.0.1:8000/admin/

## Demo customer

The `seed_data` command creates:

- Username: `demo` / Password: `Demo@12345`
- Additional sample users: `student1` and `student2` / Password: `Demo@12345`

Change the password for any real/shared environment.

## Demo payment

Online payment options are intentionally simulated for a college project. No real card, UPI or bank transaction is performed.

## Sample coupon codes

- `WELCOME10` — 10% off, minimum order 500, max discount 500
- `SAVE200` — flat 200 off, minimum order 1000
- `CAMPUS15` — 15% off, minimum order 750, max discount 600

## Project structure

```text
ecommerce_store/
├── manage.py
├── requirements.txt
├── README.md
├── ecommerce/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
└── store/
    ├── migrations/
    ├── management/commands/seed_data.py
    ├── templates/store/
    ├── static/store/css/style.css
    ├── static/store/js/app.js
    ├── admin.py
    ├── apps.py
    ├── context_processors.py
    ├── forms.py
    ├── models.py
    ├── urls.py
    ├── utils.py
    ├── views.py
    └── tests.py
```

## Production notes

Before deployment, move `SECRET_KEY` to an environment variable, set `DEBUG=False`, configure allowed hosts, HTTPS, secure cookies, a production database and a production web server.

### Demo product images
The seed command automatically assigns local product images from `media/products/` to all 15 sample products. No external image URLs are required.
