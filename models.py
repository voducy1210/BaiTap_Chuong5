from datetime import datetime, timedelta
from typing import List, Optional
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


class Category(db.Model):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    books: Mapped[List["Book"]] = relationship(back_populates="category")


class Book(db.Model):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    publisher: Mapped[Optional[str]] = mapped_column(String(100), default="NXB Đại học Huế")
    publish_year: Mapped[int] = mapped_column(default=2024)
    price: Mapped[int] = mapped_column(nullable=False)
    stock: Mapped[int] = mapped_column(default=0)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cover_image: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    category: Mapped["Category"] = relationship(back_populates="books")
    order_items: Mapped[List["OrderItem"]] = relationship(back_populates="book")


class Order(db.Model):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(15), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    payment_method: Mapped[str] = mapped_column(String(50), default="COD")
    shipping_fee: Mapped[int] = mapped_column(default=0)
    total_amount: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="Chờ xác nhận")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    items: Mapped[List["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    histories: Mapped[List["OrderHistory"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderHistory.id.asc()"
    )


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price: Mapped[int] = mapped_column(nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
    book: Mapped["Book"] = relationship(back_populates="order_items")


class OrderHistory(db.Model):
    __tablename__ = "order_histories"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    order: Mapped["Order"] = relationship(back_populates="histories")


def seed_data():
    """Khởi tạo dữ liệu mẫu nếu CSDL trống."""
    if db.session.scalar(db.select(func.count(Category.id))) > 0:
        return

    c1 = Category(name="Lập trình", description="Sách lập trình căn bản và nâng cao")
    c2 = Category(name="Cơ sở dữ liệu", description="Thiết kế và quản trị CSDL")
    c3 = Category(name="Công cụ", description="Git, Docker và công cụ phát triển")
    c4 = Category(name="Mạng", description="Mạng máy tính và bảo mật")
    c5 = Category(name="Kỹ năng lập trình", description="Clean Code, kiến trúc phần mềm")
    c6 = Category(name="Thiết kế", description="UI/UX và thiết kế đồ họa")
    db.session.add_all([c1, c2, c3, c4, c5, c6])
    db.session.flush()

    b1 = Book(
        title="Lập trình Python cơ bản", author="Nguyễn Văn A",
        publisher="NXB Đại học Huế", publish_year=2024, price=95000, stock=30,
        description="Giáo trình nhập môn lập trình Python dành cho sinh viên CNTT.",
        category_id=c1.id
    )
    b2 = Book(
        title="Giáo trình Flask", author="Miguel Grinberg",
        publisher="NXB Khoa học", publish_year=2023, price=120000, stock=20,
        description="Xây dựng ứng dụng web thực tế với Python Flask.",
        category_id=c1.id
    )
    b3 = Book(
        title="Cơ sở dữ liệu", author="Trần Văn B",
        publisher="NXB Giáo dục", publish_year=2022, price=85000, stock=0,
        description="Nguyên lý hệ quản trị cơ sở dữ liệu quan hệ.",
        category_id=c2.id
    )
    b4 = Book(
        title="Pro Git", author="Scott Chacon",
        publisher="Apress", publish_year=2021, price=150000, stock=15,
        description="Quản lý mã nguồn phân tán chuyên sâu với Git.",
        category_id=c3.id
    )
    b5 = Book(
        title="Mạng máy tính", author="Lê Văn C",
        publisher="NXB Đại học Huế", publish_year=2023, price=110000, stock=12,
        description="Kiến trúc phân tầng TCP/IP và quản trị mạng.",
        category_id=c4.id
    )
    b6 = Book(
        title="Clean Code", author="Robert C. Martin",
        publisher="Prentice Hall", publish_year=2008, price=180000, stock=5,
        description="Cẩm nang viết mã sạch và tái cấu trúc phần mềm.",
        category_id=c5.id
    )
    db.session.add_all([b1, b2, b3, b4, b5, b6])
    db.session.flush()

    now = datetime.now()
    o1 = Order(
        customer_name="Lê Hoàng Cường", phone="0912345670", email="cuong@example.com",
        address="25 Nguyễn Huệ, Huế", payment_method="Tiền mặt khi nhận hàng",
        shipping_fee=20000, total_amount=180000, status="Hoàn tất",
        created_at=now - timedelta(days=2, hours=3)
    )
    o2 = Order(
        customer_name="Trần Thị Bình", phone="0987654321",
        address="10 Lê Lợi, Huế", payment_method="Chuyển khoản",
        shipping_fee=0, total_amount=215000, status="Đang giao",
        created_at=now - timedelta(days=1, hours=2)
    )
    o3 = Order(
        customer_name="Nguyễn Văn An", phone="0912345678",
        address="12 Lê Lợi, phường Thuận Hoá, Huế", note="Giao giờ hành chính",
        payment_method="Tiền mặt khi nhận hàng",
        shipping_fee=0, total_amount=460000, status="Chờ xác nhận",
        created_at=now - timedelta(hours=1)
    )
    db.session.add_all([o1, o2, o3])
    db.session.flush()

    db.session.add_all([
        OrderItem(order_id=o1.id, book_id=b2.id, quantity=1, unit_price=120000),
        OrderItem(order_id=o2.id, book_id=b5.id, quantity=1, unit_price=110000),
        OrderItem(order_id=o3.id, book_id=b1.id, quantity=2, unit_price=95000),
        OrderItem(order_id=o3.id, book_id=b2.id, quantity=1, unit_price=120000),
        OrderItem(order_id=o3.id, book_id=b4.id, quantity=1, unit_price=150000),
    ])

    db.session.add_all([
        OrderHistory(order_id=o1.id, status="Chờ xác nhận", label="Đặt hàng", created_at=o1.created_at),
        OrderHistory(order_id=o1.id, status="Đang giao", label="Đang giao", created_at=o1.created_at + timedelta(hours=1)),
        OrderHistory(order_id=o1.id, status="Hoàn tất", label="Hoàn tất", created_at=o1.created_at + timedelta(days=1)),

        OrderHistory(order_id=o2.id, status="Chờ xác nhận", label="Đặt hàng", created_at=o2.created_at),
        OrderHistory(order_id=o2.id, status="Đang giao", label="Đang giao", created_at=o2.created_at + timedelta(hours=1)),

        OrderHistory(order_id=o3.id, status="Chờ xác nhận", label="Đặt hàng", created_at=o3.created_at),
    ])
    db.session.commit()