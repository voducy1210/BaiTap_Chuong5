from typing import List, Optional
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

app = Flask(__name__)
app.config["SECRET_KEY"] = "quan-ly-sach-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bookstore.db"

db.init_app(app)


class Category(db.Model):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    books: Mapped[List["Book"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Category {self.name}>"


class Book(db.Model):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[float] = mapped_column(default=0.0)
    quantity: Mapped[int] = mapped_column(default=1)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)

    category: Mapped["Category"] = relationship(back_populates="books")

    def __repr__(self):
        return f"<Book {self.title}>"



with app.app_context():
    db.create_all()

    if db.session.scalar(db.select(func.count(Category.id))) == 0:
        c1 = Category(name="Công nghệ thông tin", description="Lập trình, CSDL, Trí tuệ nhân tạo")
        c2 = Category(name="Kinh tế & Quản trị", description="Tài chính, Marketing, Khởi nghiệp")
        c3 = Category(name="Văn học", description="Tiểu thuyết, Truyện ngắn trong và ngoài nước")
        db.session.add_all([c1, c2, c3])
        db.session.flush()

        db.session.add_all([
            Book(title="Lập trình Python cơ bản", author="Nguyễn Văn An", price=120000, quantity=15, category_id=c1.id),
            Book(title="Cơ sở dữ liệu SQL & NoSQL", author="Trần Thị Bình", price=145000, quantity=10, category_id=c1.id),
            Book(title="Nguyên lý Kinh tế học", author="N. Gregory Mankiw", price=210000, quantity=8, category_id=c2.id),
            Book(title="Nhà Giả Kim", author="Paulo Coelho", price=79000, quantity=25, category_id=c3.id),
        ])
        db.session.commit()



@app.get("/")
def dashboard():
    total_categories = db.session.scalar(db.select(func.count(Category.id))) or 0
    total_books = db.session.scalar(db.select(func.count(Book.id))) or 0
    total_stock = db.session.scalar(db.select(func.sum(Book.quantity))) or 0
    total_value = db.session.scalar(db.select(func.sum(Book.price * Book.quantity))) or 0.0

    categories = db.session.execute(
        db.select(Category).order_by(Category.name)
    ).scalars().all()

    recent_books = db.session.execute(
        db.select(Book).order_by(Book.id.desc()).limit(5)
    ).scalars().all()

    return render_template(
        "dashboard.html",
        total_categories=total_categories,
        total_books=total_books,
        total_stock=total_stock,
        total_value=total_value,
        categories=categories,
        recent_books=recent_books,
    )



@app.get("/categories")
def categories():
    all_categories = db.session.execute(
        db.select(Category).order_by(Category.id.desc())
    ).scalars().all()
    return render_template("categories.html", categories=all_categories)


@app.post("/categories/add")
def add_category():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        flash("Tên danh mục không được để trống!", "danger")
        return redirect(url_for("categories"))

    exists = db.session.scalar(db.select(Category).where(Category.name == name))
    if exists:
        flash(f"Danh mục '{name}' đã tồn tại!", "warning")
        return redirect(url_for("categories"))

    new_cat = Category(name=name, description=description)
    db.session.add(new_cat)
    db.session.commit()
    flash("Đã thêm danh mục mới thành công!", "success")
    return redirect(url_for("categories"))


@app.post("/categories/edit/<int:id>")
def edit_category(id):
    cat = db.session.get(Category, id)
    if not cat:
        flash("Không tìm thấy danh mục!", "danger")
        return redirect(url_for("categories"))

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        flash("Tên danh mục không được để trống!", "danger")
        return redirect(url_for("categories"))

    duplicate = db.session.scalar(
        db.select(Category).where(Category.name == name, Category.id != id)
    )
    if duplicate:
        flash(f"Tên danh mục '{name}' đã được sử dụng!", "warning")
        return redirect(url_for("categories"))

    cat.name = name
    cat.description = description
    db.session.commit()
    flash("Cập nhật danh mục thành công!", "success")
    return redirect(url_for("categories"))


@app.post("/categories/delete/<int:id>")
def delete_category(id):
    cat = db.session.get(Category, id)
    if not cat:
        flash("Không tìm thấy danh mục!", "danger")
        return redirect(url_for("categories"))

    if len(cat.books) > 0:
        flash(
            f"Không thể xóa '{cat.name}' vì đang có {len(cat.books)} đầu sách thuộc danh mục này!",
            "danger",
        )
        return redirect(url_for("categories"))

    db.session.delete(cat)
    db.session.commit()
    flash("Đã xóa danh mục!", "success")
    return redirect(url_for("categories"))



@app.get("/books")
def books():
    category_id = request.args.get("category_id", type=int)
    keyword = request.args.get("q", "").strip()

    stmt = db.select(Book).order_by(Book.id.desc())

    if category_id:
        stmt = stmt.where(Book.category_id == category_id)
    if keyword:
        stmt = stmt.where(
            Book.title.ilike(f"%{keyword}%") | Book.author.ilike(f"%{keyword}%")
        )

    all_books = db.session.execute(stmt).scalars().all()
    all_categories = db.session.execute(
        db.select(Category).order_by(Category.name)
    ).scalars().all()

    return render_template(
        "books.html",
        books=all_books,
        categories=all_categories,
        selected_category_id=category_id,
        keyword=keyword,
    )


@app.post("/books/add")
def add_book():
    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    category_id = request.form.get("category_id", type=int)

    if not title or not author or not category_id:
        flash("Vui lòng nhập đầy đủ tên sách, tác giả và chọn danh mục!", "danger")
        return redirect(url_for("books"))

    try:
        price = float(request.form.get("price", 0))
        quantity = int(request.form.get("quantity", 1))
        if price < 0 or quantity < 0:
            raise ValueError
    except ValueError:
        flash("Giá bán và số lượng phải là số không âm hợp lệ!", "danger")
        return redirect(url_for("books"))

    new_book = Book(
        title=title,
        author=author,
        price=price,
        quantity=quantity,
        category_id=category_id,
    )
    db.session.add(new_book)
    db.session.commit()
    flash("Đã thêm sách mới thành công!", "success")
    return redirect(url_for("books", category_id=category_id))


@app.post("/books/edit/<int:id>")
def edit_book(id):
    book = db.session.get(Book, id)
    if not book:
        flash("Không tìm thấy sách!", "danger")
        return redirect(url_for("books"))

    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    category_id = request.form.get("category_id", type=int)

    if not title or not author or not category_id:
        flash("Vui lòng điền đầy đủ thông tin sách!", "danger")
        return redirect(url_for("books"))

    try:
        price = float(request.form.get("price", 0))
        quantity = int(request.form.get("quantity", 0))
        if price < 0 or quantity < 0:
            raise ValueError
    except ValueError:
        flash("Giá bán và số lượng không hợp lệ!", "danger")
        return redirect(url_for("books"))

    book.title = title
    book.author = author
    book.price = price
    book.quantity = quantity
    book.category_id = category_id

    db.session.commit()
    flash("Cập nhật thông tin sách thành công!", "success")
    return redirect(url_for("books"))


@app.post("/books/delete/<int:id>")
def delete_book(id):
    book = db.session.get(Book, id)
    if not book:
        flash("Không tìm thấy sách!", "danger")
        return redirect(url_for("books"))

    db.session.delete(book)
    db.session.commit()
    flash("Đã xóa sách khỏi hệ thống!", "success")
    return redirect(url_for("books"))


if __name__ == "__main__":
    app.run(debug=True)