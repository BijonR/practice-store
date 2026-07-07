import csv
import io
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Product, Category, Inventory, Order, Event, Review

admin_bp = Blueprint("admin", __name__)


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash("Admin access required.", "error")
            return redirect(url_for("storefront.home"))
        return f(*args, **kwargs)
    return wrapper


@admin_bp.route("/")
@login_required
@admin_required
def dashboard():
    product_count = Product.query.count()
    order_count = Order.query.count()
    low_stock = Inventory.query.filter(Inventory.stock_qty <= Inventory.reorder_level).count()
    event_count = Event.query.count()
    return render_template(
        "admin/dashboard.html",
        product_count=product_count,
        order_count=order_count,
        low_stock=low_stock,
        event_count=event_count,
    )


@admin_bp.route("/products")
@login_required
@admin_required
def product_list():
    products = Product.query.order_by(Product.id.desc()).all()
    return render_template("admin/products.html", products=products)


@admin_bp.route("/products/new", methods=["GET", "POST"])
@login_required
@admin_required
def product_new():
    categories = Category.query.all()
    if request.method == "POST":
        product = Product(
            name=request.form["name"],
            description=request.form.get("description", ""),
            price=float(request.form["price"]),
            category_id=int(request.form["category_id"]),
            image_url=request.form.get("image_url", ""),
            is_active=True,
        )
        db.session.add(product)
        db.session.flush()
        db.session.add(Inventory(
            product_id=product.id,
            stock_qty=int(request.form.get("stock_qty", 0)),
            reorder_level=int(request.form.get("reorder_level", 10)),
        ))
        db.session.commit()
        flash(f"Created product: {product.name}", "success")
        return redirect(url_for("admin.product_list"))

    return render_template("admin/product_form.html", categories=categories, product=None)


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def product_edit(product_id):
    product = Product.query.get_or_404(product_id)
    categories = Category.query.all()

    if request.method == "POST":
        product.name = request.form["name"]
        product.description = request.form.get("description", "")
        product.price = float(request.form["price"])
        product.category_id = int(request.form["category_id"])
        product.image_url = request.form.get("image_url", "")
        product.is_active = bool(request.form.get("is_active"))

        if product.inventory:
            product.inventory.stock_qty = int(request.form.get("stock_qty", 0))
            product.inventory.reorder_level = int(request.form.get("reorder_level", 10))

        db.session.commit()
        flash("Product updated.", "success")
        return redirect(url_for("admin.product_list"))

    return render_template("admin/product_form.html", categories=categories, product=product)


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@login_required
@admin_required
def product_delete(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted.", "success")
    return redirect(url_for("admin.product_list"))


@admin_bp.route("/products/bulk-upload", methods=["GET", "POST"])
@login_required
@admin_required
def bulk_upload():
    """CSV bulk upload. Expected columns:
    name, description, price, category_name, stock_qty, image_url
    Unknown category_name values are auto-created."""
    if request.method == "POST":
        file = request.files.get("csv_file")
        if not file or file.filename == "":
            flash("Please choose a CSV file.", "error")
            return redirect(url_for("admin.bulk_upload"))

        try:
            stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
            reader = csv.DictReader(stream)

            created, errors = 0, []
            category_cache = {c.name.lower(): c for c in Category.query.all()}

            for i, row in enumerate(reader, start=2):  # row 1 is the header
                try:
                    cat_name = row["category_name"].strip()
                    cat_key = cat_name.lower()
                    if cat_key not in category_cache:
                        new_cat = Category(name=cat_name, slug=cat_name.lower().replace(" ", "-"))
                        db.session.add(new_cat)
                        db.session.flush()
                        category_cache[cat_key] = new_cat
                    category = category_cache[cat_key]

                    product = Product(
                        name=row["name"].strip(),
                        description=row.get("description", "").strip(),
                        price=float(row["price"]),
                        category_id=category.id,
                        image_url=row.get("image_url", "").strip(),
                        is_active=True,
                    )
                    db.session.add(product)
                    db.session.flush()
                    db.session.add(Inventory(
                        product_id=product.id,
                        stock_qty=int(row.get("stock_qty", 0) or 0),
                        reorder_level=10,
                    ))
                    created += 1
                except Exception as e:
                    errors.append(f"Row {i}: {e}")

            db.session.commit()
            flash(f"Imported {created} products." + (f" {len(errors)} rows failed." if errors else ""), "success")
            if errors:
                flash("; ".join(errors[:10]), "error")

        except Exception as e:
            db.session.rollback()
            flash(f"Upload failed: {e}", "error")

        return redirect(url_for("admin.product_list"))

    return render_template("admin/bulk_upload.html")


@admin_bp.route("/orders")
@login_required
@admin_required
def order_list():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin/orders.html", orders=orders)
