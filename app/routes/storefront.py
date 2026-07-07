from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user, login_required
from sqlalchemy import or_
from app import db
from app.models import Product, Category, Cart, CartItem, Order, OrderItem, Inventory
from app.utils.events import log_event

storefront_bp = Blueprint("storefront", __name__)


@storefront_bp.route("/")
def home():
    categories = Category.query.filter(Category.parent_id.is_(None)).all()
    featured = Product.query.filter_by(is_active=True).order_by(Product.created_at.desc()).limit(8).all()
    log_event("page_view", page_url="/")
    return render_template("home.html", categories=categories, featured=featured)


@storefront_bp.route("/products")
def product_list():
    category_slug = request.args.get("category")
    search_q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)

    query = Product.query.filter_by(is_active=True)

    if category_slug:
        category = Category.query.filter_by(slug=category_slug).first()
        if category:
            query = query.filter_by(category_id=category.id)

    if search_q:
        query = query.filter(or_(
            Product.name.ilike(f"%{search_q}%"),
            Product.description.ilike(f"%{search_q}%"),
        ))
        log_event("search", metadata={"query": search_q})

    pagination = query.order_by(Product.id.desc()).paginate(page=page, per_page=24, error_out=False)
    categories = Category.query.all()

    return render_template(
        "products.html",
        products=pagination.items,
        pagination=pagination,
        categories=categories,
        current_category=category_slug,
        search_q=search_q,
    )


@storefront_bp.route("/product/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    related = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product.id,
        Product.is_active.is_(True),
    ).limit(4).all()
    log_event("product_view", page_url=f"/product/{product_id}", metadata={"product_id": product_id})
    return render_template("product_detail.html", product=product, related=related)


def _get_or_create_cart():
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)
        db.session.commit()
    return cart


@storefront_bp.route("/cart")
@login_required
def view_cart():
    cart = _get_or_create_cart()
    total = sum(item.product.price * item.quantity for item in cart.items)
    return render_template("cart.html", cart=cart, total=total)


@storefront_bp.route("/cart/add/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = request.form.get("quantity", 1, type=int)

    cart = _get_or_create_cart()
    item = CartItem.query.filter_by(cart_id=cart.id, product_id=product.id).first()
    if item:
        item.quantity += quantity
    else:
        item = CartItem(cart_id=cart.id, product_id=product.id, quantity=quantity)
        db.session.add(item)
    db.session.commit()

    log_event("add_to_cart", metadata={"product_id": product_id, "quantity": quantity})
    flash(f"Added {product.name} to cart.", "success")
    return redirect(request.referrer or url_for("storefront.product_list"))


@storefront_bp.route("/cart/remove/<int:item_id>", methods=["POST"])
@login_required
def remove_from_cart(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.cart.user_id != current_user.id:
        flash("Not authorized.", "error")
        return redirect(url_for("storefront.view_cart"))
    product_id = item.product_id
    db.session.delete(item)
    db.session.commit()
    log_event("remove_from_cart", metadata={"product_id": product_id})
    return redirect(url_for("storefront.view_cart"))


@storefront_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart = _get_or_create_cart()
    if not cart.items:
        flash("Your cart is empty.", "error")
        return redirect(url_for("storefront.product_list"))

    if request.method == "POST":
        log_event("checkout_start", metadata={"item_count": len(cart.items)})

        total = sum(item.product.price * item.quantity for item in cart.items)
        order = Order(user_id=current_user.id, status="paid", total_amount=total)
        db.session.add(order)
        db.session.flush()  # get order.id before commit

        for item in cart.items:
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.product.price,
            ))
            inv = Inventory.query.get(item.product_id)
            if inv:
                inv.stock_qty = max(0, inv.stock_qty - item.quantity)
            db.session.delete(item)

        db.session.commit()
        log_event("purchase", metadata={"order_id": order.id, "total": float(total)})
        flash(f"Order #{order.id} placed successfully (this is a mock checkout, no real payment).", "success")
        return redirect(url_for("storefront.order_confirmation", order_id=order.id))

    total = sum(item.product.price * item.quantity for item in cart.items)
    return render_template("checkout.html", cart=cart, total=total)


@storefront_bp.route("/order/<int:order_id>")
@login_required
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash("Not authorized.", "error")
        return redirect(url_for("storefront.home"))
    return render_template("order_confirmation.html", order=order)


@storefront_bp.route("/orders")
@login_required
def order_history():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("order_history.html", orders=orders)
