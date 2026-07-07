# Practice E-commerce Store

Built with Flask + SQLAlchemy. Ships with a synthetic data generator, GA4 tracking, and a custom event-logging table for your own analytics dashboard.

## Run locally

    python -m venv venv
    . venv/bin/activate          # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    cp .env.example .env         # already has your GA4 ID filled in
    python seed.py --reset --products 300
    python run.py

Then open http://localhost:5000

Admin login: admin@ledgerco.test / admin123

## Bulk-load your own products later
Admin panel -> Products -> Bulk upload -> upload a CSV with columns:
name, description, price, category_name, stock_qty, image_url
(sample_products.csv included as a template)

## Regenerate synthetic data anytime

    python seed.py --reset --products 500 --users 200 --reviews 800 --orders 600 --events 8000
