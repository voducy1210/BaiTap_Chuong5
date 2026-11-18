import os
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import func, or_

from forms import CheckoutForm, BookForm, CategoryForm
from models import db, Category, Book, Order, OrderItem, OrderHistory, seed_data
app = Flask(__name__)
app.config["SECRET_KEY"] = "nha-sach-song-huong-secret-2026"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///nhasach.db"
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db.init_app(app)
csrf = CSRFProtect(app)

with app.app_context():
    db.create_all()
    seed_data()


# --- CONTEXT PROCESSOR: TỰ ĐỘNG TRUYỀN BADGE GIỎ HÀNG & ĐƠN CHỜ ---
@app.context_processor
def inject_globals():
    cart = session.get("cart", {})
    cart_count = sum(cart.values())
    pending_orders_count = db.session.scalar(
        db.select(func.count(Order.id)).where(Order.status == "Chờ xác nhận")
    ) or 0
    return dict(cart_count=cart_count, pending_orders_count=pending_orders_count)


def save_cover_file(file_storage):
    ext = os.path.splitext(file_storage.filename)[1].lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    file_storage.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    return filename


def delete_cover_file(filename):
    if filename:
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        if os.path.exists(path):
            os.remove(path)


# =====================================================================
# PHẦN A: TRANG BÁN HÀNG (1 -> 5)
# =====================================================================

@app.get("/")
def index():
    return redirect(url_for("books_list"))


# MÀN HÌNH 1: DANH SÁCH SÁCH (/books)
@app.get("/books")
def books_list():
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", type=int)

    stmt = db.select(Book).order_by(Book.id.asc())
    if q:
        stmt = stmt.where(or_(Book.title.ilike(f"%{q}%"), Book.author.ilike(f"%{q}%")))
    if category_id:
        stmt = stmt.where(Book.category_id == category_id)

    books = db.session.execute(stmt).scalars().all()
    categories = db.session.execute(db.select(Category).order_by(Category.name)).scalars().all()

    return render_template(
        "books.html",
        books=books,
        categories=categories,
        q=q,
        selected_category_id=category_id
    )


# MÀN HÌNH 2: CHỌN SÁCH (/books/<id>)
@app.route("/books/<int:book_id>", methods=["GET", "POST"])
def book_detail(book_id):
    book = db.get_or_404(Book, book_id)
    cart = session.get("cart", {})
    in_cart = cart.get(str(book.id), 0)
    max_can_add = max(0, book.stock - in_cart)

    if request.method == "POST":
        try:
            qty = int(request.form.get("quantity", 1))
        except ValueError:
            qty = 0

        if qty < 1 or qty > max_can_add:
            flash(f"Số lượng không hợp lệ (chỉ có thể thêm tối đa {max_can_add} cuốn).", "danger")
            return redirect(url_for("book_detail", book_id=book.id))

        cart[str(book.id)] = in_cart + qty
        session["cart"] = cart
        flash(f"✓ Đã thêm {qty} × {book.title} vào giỏ hàng.", "success")
        return redirect(url_for("book_detail", book_id=book.id))

    return render_template(
        "book_detail.html",
        book=book,
        in_cart=in_cart,
        max_can_add=max_can_add
    )


# THÊM NHANH 1 CUỐN TỪ MÀN HÌNH 1
@app.post("/cart/add/<int:book_id>")
def add_to_cart(book_id):
    book = db.get_or_404(Book, book_id)
    cart = session.get("cart", {})
    in_cart = cart.get(str(book.id), 0)

    if in_cart + 1 > book.stock:
        flash(f"Sách '{book.title}' đã hết hàng hoặc vượt quá tồn kho!", "danger")
    else:
        cart[str(book.id)] = in_cart + 1
        session["cart"] = cart
        flash(f"✓ Đã thêm 1 × {book.title} vào giỏ hàng.", "success")

    return redirect(request.referrer or url_for("books_list"))


# MÀN HÌNH 3: GIỎ HÀNG (/cart)
@app.get("/cart")
def cart_view():
    cart = session.get("cart", {})
    items = []
    total_amount = 0
    cleaned_cart = {}

    for book_id_str, qty in cart.items():
        book = db.session.get(Book, int(book_id_str))
        if book and book.stock > 0:
            valid_qty = min(qty, book.stock)
            cleaned_cart[book_id_str] = valid_qty
            subtotal = book.price * valid_qty
            total_amount += subtotal
            items.append({
                "book": book,
                "quantity": valid_qty,
                "subtotal": subtotal
            })

    if cleaned_cart != cart:
        session["cart"] = cleaned_cart

    return render_template("cart.html", items=items, total_amount=total_amount)


@app.post("/cart/update/<int:book_id>")
def update_cart(book_id):
    book = db.get_or_404(Book, book_id)
    action = request.form.get("action")
    cart = session.get("cart", {})
    key = str(book_id)

    if key in cart:
        if action == "inc":
            if cart[key] < book.stock:
                cart[key] += 1
            else:
                flash(f"Đã đạt giới hạn tồn kho ({book.stock} cuốn).", "warning")
        elif action == "dec":
            cart[key] -= 1
            if cart[key] <= 0:
                del cart[key]

    session["cart"] = cart
    return redirect(url_for("cart_view"))


@app.post("/cart/remove/<int:book_id>")
def remove_from_cart(book_id):
    cart = session.get("cart", {})
    cart.pop(str(book_id), None)
    session["cart"] = cart
    flash("Đã xoá sách khỏi giỏ hàng.", "info")
    return redirect(url_for("cart_view"))


@app.post("/cart/clear")
def clear_cart():
    session.pop("cart", None)
    flash("Đã xoá toàn bộ giỏ hàng.", "info")
    return redirect(url_for("cart_view"))


# MÀN HÌNH 4: THÔNG TIN KHÁCH HÀNG & ĐẶT HÀNG (/checkout)
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    cart = session.get("cart", {})
    if not cart:
        flash("Giỏ hàng đang trống, vui lòng chọn sách trước khi đặt hàng!", "warning")
        return redirect(url_for("cart_view"))

    items = []
    subtotal = 0
    for book_id_str, qty in cart.items():
        book = db.session.get(Book, int(book_id_str))
        if book:
            line_total = book.price * qty
            subtotal += line_total
            items.append({"book": book, "quantity": qty, "subtotal": line_total})

    shipping_fee = 0 if subtotal >= 200000 else 20000
    grand_total = subtotal + shipping_fee

    form = CheckoutForm()
    if form.validate_on_submit():
        # Kiểm tra lại tồn kho trước khi tạo đơn
        for item in items:
            book = db.session.get(Book, item["book"].id)
            if not book or book.stock < item["quantity"]:
                avail = book.stock if book else 0
                flash(
                    f"Sách '{item['book'].title}' không đủ hàng (chỉ còn {avail} cuốn). Vui lòng điều chỉnh giỏ!",
                    "danger"
                )
                return redirect(url_for("cart_view"))

        # Tạo đơn hàng & trừ tồn kho
        order = Order(
            customer_name=form.customer_name.data.strip(),
            phone=form.phone.data.strip(),
            email=form.email.data.strip() if form.email.data else None,
            address=form.address.data.strip(),
            note=form.note.data.strip() if form.note.data else None,
            payment_method=form.payment_method.data,
            shipping_fee=shipping_fee,
            total_amount=grand_total,
            status="Chờ xác nhận"
        )
        db.session.add(order)
        db.session.flush()

        for item in items:
            book = db.session.get(Book, item["book"].id)
            book.stock -= item["quantity"]
            db.session.add(
                OrderItem(
                    order_id=order.id,
                    book_id=book.id,
                    quantity=item["quantity"],
                    unit_price=book.price
                )
            )

        db.session.commit()
        session.pop("cart", None)
        flash("Đặt hàng thành công!", "success")
        return redirect(url_for("order_success", order_id=order.id))

    return render_template(
        "checkout.html",
        form=form,
        items=items,
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        grand_total=grand_total
    )


# MÀN HÌNH 5: ĐẶT THÀNH CÔNG (/orders/<id>)
@app.get("/orders/<int:order_id>")
def order_success(order_id):
    order = db.get_or_404(Order, order_id)
    return render_template("order_success.html", order=order)


# =====================================================================
# PHẦN B: TRANG QUẢN TRỊ /admin (6 -> 11)
# =====================================================================

# MÀN HÌNH 6: TỔNG QUAN (/admin)
@app.get("/admin")
def admin_dashboard():
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # 4 thẻ thống kê — mỗi số là 1 truy vấn
    total_books = db.session.scalar(db.select(func.count(Book.id))) or 0
    pending_orders = db.session.scalar(
        db.select(func.count(Order.id)).where(Order.status == "Chờ xác nhận")
    ) or 0
    monthly_revenue = db.session.scalar(
        db.select(func.sum(Order.total_amount)).where(
            Order.status == "Hoàn tất",
            Order.created_at >= month_start
        )
    ) or 0
    low_stock_count = db.session.scalar(
        db.select(func.count(Book.id)).where(Book.stock <= 5)
    ) or 0

    recent_orders = db.session.execute(
        db.select(Order).order_by(Order.id.desc()).limit(5)
    ).scalars().all()

    low_stock_books = db.session.execute(
        db.select(Book).where(Book.stock <= 5).order_by(Book.stock.asc())
    ).scalars().all()

    # Biểu đồ doanh thu 7 ngày gần nhất
    chart_data = []
    max_rev = 1
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).date()
        d_start = datetime.combine(day, datetime.min.time())
        d_end = datetime.combine(day, datetime.max.time())
        rev = db.session.scalar(
            db.select(func.sum(Order.total_amount)).where(
                Order.status != "Đã huỷ",
                Order.created_at >= d_start,
                Order.created_at <= d_end
            )
        ) or 0
        if rev > max_rev:
            max_rev = rev
        chart_data.append({"label": day.strftime("%d/%m"), "value": rev})

    return render_template(
        "admin/dashboard.html",
        current_month=now.month,
        total_books=total_books,
        pending_orders=pending_orders,
        monthly_revenue=monthly_revenue,
        low_stock_count=low_stock_count,
        recent_orders=recent_orders,
        low_stock_books=low_stock_books,
        chart_data=chart_data,
        max_rev=max_rev
    )


# MÀN HÌNH 7: QUẢN LÝ SÁCH (/admin/books)
@app.get("/admin/books")
def admin_books():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", type=int)
    stock_filter = request.args.get("stock", "")

    stmt = db.select(Book).order_by(Book.id.desc())

    if q:
        stmt = stmt.where(or_(Book.title.ilike(f"%{q}%"), Book.author.ilike(f"%{q}%")))
    if category_id:
        stmt = stmt.where(Book.category_id == category_id)
    if stock_filter == "in_stock":
        stmt = stmt.where(Book.stock > 0)
    elif stock_filter == "low_stock":
        stmt = stmt.where(Book.stock <= 5, Book.stock > 0)
    elif stock_filter == "out_of_stock":
        stmt = stmt.where(Book.stock == 0)

    pagination = db.paginate(stmt, page=page, per_page=5, error_out=False)
    categories = db.session.execute(db.select(Category).order_by(Category.name)).scalars().all()

    # Tập ID các sách đã nằm trong đơn hàng (không được xoá)
    ordered_book_ids = set(
        db.session.execute(db.select(OrderItem.book_id).distinct()).scalars().all()
    )

    return render_template(
        "admin/books.html",
        pagination=pagination,
        books=pagination.items,
        categories=categories,
        ordered_book_ids=ordered_book_ids,
        q=q,
        selected_category_id=category_id,
        stock_filter=stock_filter
    )


# MÀN HÌNH 8: THÊM & SỬA SÁCH (DÙNG CHUNG FORM VÀ TEMPLATE)
@app.route("/admin/books/new", methods=["GET", "POST"])
def admin_book_new():
    form = BookForm()
    form.category_id.choices = [
        (c.id, c.name) for c in db.session.execute(db.select(Category).order_by(Category.name)).scalars().all()
    ]

    if form.validate_on_submit():
        filename = save_cover_file(form.cover_image.data) if form.cover_image.data else None
        book = Book(
            title=form.title.data.strip(),
            author=form.author.data.strip(),
            category_id=form.category_id.data,
            publisher=form.publisher.data.strip() if form.publisher.data else "NXB Đại học Huế",
            publish_year=form.publish_year.data,
            price=form.price.data,
            stock=form.stock.data,
            description=form.description.data,
            cover_image=filename
        )
        db.session.add(book)
        db.session.commit()
        flash(f"Đã thêm sách mới: '{book.title}'.", "success")
        return redirect(url_for("admin_books"))

    return render_template("admin/book_form.html", form=form, book=None)


@app.route("/admin/books/<int:book_id>/edit", methods=["GET", "POST"])
def admin_book_edit(book_id):
    book = db.get_or_404(Book, book_id)
    form = BookForm(book_id=book.id, obj=book)
    form.category_id.choices = [
        (c.id, c.name) for c in db.session.execute(db.select(Category).order_by(Category.name)).scalars().all()
    ]

    if form.validate_on_submit():
        book.title = form.title.data.strip()
        book.author = form.author.data.strip()
        book.category_id = form.category_id.data
        book.publisher = form.publisher.data.strip() if form.publisher.data else "NXB Đại học Huế"
        book.publish_year = form.publish_year.data
        book.price = form.price.data
        book.stock = form.stock.data
        book.description = form.description.data

        if form.cover_image.data:
            delete_cover_file(book.cover_image)
            book.cover_image = save_cover_file(form.cover_image.data)

        db.session.commit()
        flash(f"Đã cập nhật sách: '{book.title}'.", "success")
        return redirect(url_for("admin_books"))

    return render_template("admin/book_form.html", form=form, book=book)


@app.post("/admin/books/<int:book_id>/delete")
def admin_book_delete(book_id):
    book = db.get_or_404(Book, book_id)
    has_orders = db.session.scalar(
        db.select(func.count(OrderItem.id)).where(OrderItem.book_id == book.id)
    ) or 0

    if has_orders > 0:
        flash(f"Không thể xoá '{book.title}' vì sách đã có trong đơn hàng!", "danger")
        return redirect(url_for("admin_books"))

    delete_cover_file(book.cover_image)
    db.session.delete(book)
    db.session.commit()
    flash(f"Đã xoá sách '{book.title}'.", "success")
    return redirect(url_for("admin_books"))


# MÀN HÌNH 9: DANH MỤC SÁCH (/admin/categories)
@app.route("/admin/categories", methods=["GET", "POST"])
def admin_categories():
    edit_id = request.args.get("edit_id", type=int) or request.form.get("edit_id", type=int)
    edit_cat = db.session.get(Category, edit_id) if edit_id else None

    form = CategoryForm(category_id=edit_id, obj=edit_cat if request.method == "GET" else None)

    if form.validate_on_submit():
        if edit_cat:
            edit_cat.name = form.name.data.strip()
            edit_cat.description = form.description.data.strip() if form.description.data else None
            db.session.commit()
            flash("Cập nhật danh mục thành công!", "success")
        else:
            new_cat = Category(
                name=form.name.data.strip(),
                description=form.description.data.strip() if form.description.data else None
            )
            db.session.add(new_cat)
            db.session.commit()
            flash("Đã thêm danh mục mới!", "success")
        return redirect(url_for("admin_categories"))

    # Một truy vấn group_by lấy cả danh mục chưa có sách (0 sách)
    rows = db.session.execute(
        db.select(Category, func.count(Book.id).label("book_count"))
        .outerjoin(Book, Category.id == Book.category_id)
        .group_by(Category.id)
        .order_by(Category.id.asc())
    ).all()

    return render_template(
        "admin/categories.html",
        rows=rows,
        form=form,
        edit_cat=edit_cat
    )


@app.post("/admin/categories/<int:cat_id>/delete")
def admin_category_delete(cat_id):
    cat = db.get_or_404(Category, cat_id)
    book_count = db.session.scalar(
        db.select(func.count(Book.id)).where(Book.category_id == cat.id)
    ) or 0

    if book_count > 0:
        flash(f'Không thể xoá "{cat.name}": còn {book_count} sách.', "danger")
        return redirect(url_for("admin_categories"))

    db.session.delete(cat)
    db.session.commit()
    flash(f'Đã xoá danh mục "{cat.name}".', "success")
    return redirect(url_for("admin_categories"))


# MÀN HÌNH 10: DANH SÁCH ĐƠN HÀNG (/admin/orders)
@app.get("/admin/orders")
def admin_orders():
    status_filter = request.args.get("status", "")
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)

    # Một truy vấn group_by đếm số đơn theo từng trạng thái
    status_counts_raw = db.session.execute(
        db.select(Order.status, func.count(Order.id)).group_by(Order.status)
    ).all()
    counts_map = dict(status_counts_raw)
    total_all_orders = sum(counts_map.values())

    stmt = db.select(Order).order_by(Order.id.desc())
    if status_filter:
        stmt = stmt.where(Order.status == status_filter)
    if q:
        clean_id = q.lstrip("#")
        conditions = [
            Order.customer_name.ilike(f"%{q}%"),
            Order.phone.ilike(f"%{q}%")
        ]
        if clean_id.isdigit():
            conditions.append(Order.id == int(clean_id))
        stmt = stmt.where(or_(*conditions))

    # Tổng số đơn và tổng giá trị của bộ lọc hiện tại
    filtered_orders_all = db.session.execute(stmt).scalars().all()
    filtered_count = len(filtered_orders_all)
    filtered_total_value = sum(o.total_amount for o in filtered_orders_all)

    pagination = db.paginate(stmt, page=page, per_page=10, error_out=False)

    return render_template(
        "admin/orders.html",
        pagination=pagination,
        orders=pagination.items,
        status_filter=status_filter,
        q=q,
        counts_map=counts_map,
        total_all_orders=total_all_orders,
        filtered_count=filtered_count,
        filtered_total_value=filtered_total_value
    )


# MÀN HÌNH 11: CHI TIẾT ĐƠN HÀNG (/admin/orders/<id>)
@app.route("/admin/orders/<int:order_id>", methods=["GET", "POST"])
def admin_order_detail(order_id):
    order = db.get_or_404(Order, order_id)

    # Quy tắc chuyển trạng thái hợp lệ:
    # Chờ xác nhận -> Đang giao -> Hoàn tất
    # Chờ xác nhận, Đang giao -> Đã huỷ
    next_status_map = {
        "Chờ xác nhận": "Đang giao",
        "Đang giao": "Hoàn tất",
    }

    if request.method == "POST":
        # Hoàn tất hoặc Đã huỷ thì không cho đổi nữa
        if order.status in ["Hoàn tất", "Đã huỷ"]:
            flash("Đơn hàng đã kết thúc, không thể thay đổi trạng thái.", "danger")
            return redirect(url_for("admin_order_detail", order_id=order.id))

        action = request.form.get("action")

        if action == "advance":
            target_status = request.form.get("status")
            expected_next = next_status_map.get(order.status)

            if target_status != expected_next:
                flash("Chuyển trạng thái không hợp lệ!", "danger")
                return redirect(url_for("admin_order_detail", order_id=order.id))

            order.status = target_status
            db.session.add(
                OrderHistory(
                    order_id=order.id,
                    status=target_status,
                    label=target_status,
                    created_at=datetime.now()
                )
            )
            db.session.commit()
            flash(f"Đã cập nhật trạng thái đơn #{order.id} sang '{target_status}'.", "success")

        elif action == "cancel":
            # Hoàn lại tồn kho các sách trong đơn
            for item in order.items:
                item.book.stock += item.quantity

            order.status = "Đã huỷ"
            db.session.add(
                OrderHistory(
                    order_id=order.id,
                    status="Đã huỷ",
                    label="Đã huỷ",
                    created_at=datetime.now()
                )
            )
            db.session.commit()
            flash(f"Đã huỷ đơn hàng #{order.id} và hoàn lại tồn kho.", "warning")

        return redirect(url_for("admin_order_detail", order_id=order.id))

    next_status = next_status_map.get(order.status)
    reached_statuses = {h.status for h in order.histories}

    return render_template(
        "admin/order_detail.html",
        order=order,
        next_status=next_status,
        reached_statuses=reached_statuses
    )


if __name__ == "__main__":
    app.run(debug=True)