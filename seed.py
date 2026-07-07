"""
Bulk synthetic data generator.

Run this once to populate the database with fake but realistic-looking
categories, products, inventory, users, reviews, orders, and events —
so the store has real data to browse and the dashboard has real data to chart.

Usage:
    python seed.py                     # default: 300 products
    python seed.py --products 1000     # generate a bigger catalog
    python seed.py --reset             # wipe existing data first
"""
import argparse
import random
from datetime import timedelta
from faker import Faker

from app import create_app, db
from app.models import User, Category, Product, Inventory, Review, Order, OrderItem, Event
from app.models import now_utc

fake = Faker()

CATEGORY_TEMPLATES = {
    "Electronics": ["Headphones", "Bluetooth Speaker", "Smartwatch", "Laptop Stand",
                    "USB-C Hub", "Wireless Mouse", "Mechanical Keyboard", "Webcam",
                    "Power Bank", "Monitor"],
    "Home & Kitchen": ["Coffee Maker", "Blender", "Cast Iron Pan", "Knife Set",
                       "Air Fryer", "Toaster", "Cutting Board", "Dish Rack",
                       "Food Storage Container", "Electric Kettle"],
    "Books": ["Novel", "Cookbook", "Biography", "Self-Help Guide", "History Book",
              "Poetry Collection", "Science Textbook", "Graphic Novel", "Travel Guide", "Memoir"],
    "Clothing": ["T-Shirt", "Jeans", "Hoodie", "Jacket", "Sneakers",
                 "Dress", "Formal Shirt", "Shorts", "Cap", "Scarf"],
    "Sports & Outdoors": ["Yoga Mat", "Dumbbell Set", "Running Shoes", "Water Bottle",
                          "Camping Tent", "Backpack", "Bicycle Helmet", "Resistance Bands",
                          "Hiking Boots", "Sleeping Bag"],
    "Toys & Games": ["Board Game", "Puzzle", "Action Figure", "Building Blocks",
                     "Remote Control Car", "Card Game", "Plush Toy", "Toy Drone",
                     "Chess Set", "Model Kit"],
}

PLACEHOLDER_COLORS = ["2E6B5E", "C98A3B", "1C2430", "A6402F", "5B6472"]


def get_or_create_categories():
    categories = {}
    for name in CATEGORY_TEMPLATES:
        slug = name.lower().replace(" & ", "-").replace(" ", "-")
        cat = Category.query.filter_by(slug=slug).first()
        if not cat:
            cat = Category(name=name, slug=slug)
            db.session.add(cat)
            db.session.flush()
        categories[name] = cat
    db.session.commit()
    return categories


def make_products(n, categories):
    created = []
    for i in range(n):
        cat_name = random.choice(list(CATEGORY_TEMPLATES.keys()))
        product_type = random.choice(CATEGORY_TEMPLATES[cat_name])
        brand = fake.company().split(",")[0].split(" ")[0]  # short fake brand word
        name = f"{brand} {product_type}"
        color = random.choice(PLACEHOLDER_COLORS)

        product = Product(
            name=name,
            description=fake.paragraph(nb_sentences=3),
            price=round(random.uniform(5.99, 499.99), 2),
            category_id=categories[cat_name].id,
            image_url=f"https://placehold.co/400x300/{color}/F6F3EC?text={product_type.replace(' ', '+')}",
            is_active=True,
        )
        db.session.add(product)
        db.session.flush()

        stock = random.choices([0, random.randint(1, 9), random.randint(10, 200)],
                                weights=[0.05, 0.15, 0.80])[0]
        db.session.add(Inventory(product_id=product.id, stock_qty=stock, reorder_level=10))
        created.append(product)

        if i % 100 == 0:
            db.session.commit()
            print(f"  ...{i}/{n} products created")

    db.session.commit()
    print(f"Created {len(created)} products across {len(categories)} categories.")
    return created


def make_users(n):
    users = []
    for _ in range(n):
        email = fake.unique.email()
        user = User(email=email, role="customer")
        user.set_password("password123")  # fine for a practice/test dataset only
        db.session.add(user)
        users.append(user)
    db.session.flush()

    admin = User.query.filter_by(email="admin@ledgerco.test").first()
    if not admin:
        admin = User(email="admin@ledgerco.test", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)

    db.session.commit()
    print(f"Created {len(users)} customer users + 1 admin (admin@ledgerco.test / admin123).")
    return users


def make_reviews(products, users, n):
    comments = [
        "Works exactly as described, happy with this purchase.",
        "Good value for the price, would buy again.",
        "Quality is fine but shipping took a while.",
        "Exceeded my expectations, very well made.",
        "Decent, nothing special but does the job.",
        "Not quite what I expected, but usable.",
    ]
    for _ in range(n):
        product = random.choice(products)
        user = random.choice(users)
        rating = random.choices([5, 4, 3, 2, 1], weights=[0.4, 0.3, 0.15, 0.1, 0.05])[0]
        db.session.add(Review(
            user_id=user.id,
            product_id=product.id,
            rating=rating,
            comment=random.choice(comments),
        ))
    db.session.commit()
    print(f"Created {n} reviews.")


def make_orders_and_events(products, users, n_orders, n_events):
    for _ in range(n_orders):
        user = random.choice(users)
        days_ago = random.randint(0, 90)
        created_at = now_utc() - timedelta(days=days_ago)
        n_items = random.randint(1, 4)
        chosen = random.sample(products, min(n_items, len(products)))

        total = 0
        order = Order(user_id=user.id, status=random.choice(
            ["paid", "paid", "paid", "shipped", "delivered", "cancelled"]
        ), created_at=created_at, total_amount=0)
        db.session.add(order)
        db.session.flush()

        for product in chosen:
            qty = random.randint(1, 3)
            db.session.add(OrderItem(order_id=order.id, product_id=product.id,
                                      quantity=qty, unit_price=product.price))
            total += float(product.price) * qty

        order.total_amount = round(total, 2)
    db.session.commit()
    print(f"Created {n_orders} orders.")

    event_types = ["page_view", "product_view", "add_to_cart", "search", "checkout_start", "purchase"]
    for _ in range(n_events):
        days_ago = random.randint(0, 90)
        created_at = now_utc() - timedelta(days=days_ago, hours=random.randint(0, 23))
        user = random.choice(users) if random.random() > 0.3 else None  # some anonymous
        db.session.add(Event(
            user_id=user.id if user else None,
            session_id=fake.uuid4(),
            event_type=random.choices(event_types, weights=[0.4, 0.25, 0.15, 0.1, 0.06, 0.04])[0],
            page_url=random.choice(["/", "/products", f"/product/{random.choice(products).id}"]),
            event_metadata={},
            created_at=created_at,
        ))
    db.session.commit()
    print(f"Created {n_events} historical events (for dashboard trend charts).")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--products", type=int, default=300)
    parser.add_argument("--users", type=int, default=150)
    parser.add_argument("--reviews", type=int, default=600)
    parser.add_argument("--orders", type=int, default=400)
    parser.add_argument("--events", type=int, default=5000)
    parser.add_argument("--reset", action="store_true", help="Wipe all existing data first")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        db.create_all()

        if args.reset:
            print("Resetting database...")
            db.drop_all()
            db.create_all()

        categories = get_or_create_categories()
        products = make_products(args.products, categories)
        users = make_users(args.users)
        make_reviews(products, users, args.reviews)
        make_orders_and_events(products, users, args.orders, args.events)

        print("\nDone. Log in as admin@ledgerco.test / admin123 to manage the store.")


if __name__ == "__main__":
    main()
