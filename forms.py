from datetime import datetime
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, IntegerField, TextAreaField, SelectField, RadioField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp, Optional, Email, NumberRange, ValidationError
from sqlalchemy import func
from models import db, Book, Category


class CheckoutForm(FlaskForm):
    customer_name = StringField(
        "Họ tên *",
        validators=[DataRequired("Vui lòng nhập họ tên."), Length(max=100)]
    )
    phone = StringField(
        "Số điện thoại *",
        validators=[
            DataRequired("Vui lòng nhập số điện thoại."),
            Regexp(r"^0\d{9}$", message="Số điện thoại gồm 10 chữ số, bắt đầu bằng 0.")
        ]
    )
    email = StringField(
        "Email",
        validators=[Optional(), Email("Email không đúng định dạng.")]
    )
    address = TextAreaField(
        "Địa chỉ giao hàng *",
        validators=[DataRequired("Vui lòng nhập địa chỉ giao hàng."), Length(max=255)]
    )
    note = StringField("Ghi chú", validators=[Optional(), Length(max=255)])
    payment_method = RadioField(
        "Thanh toán *",
        choices=[("Tiền mặt khi nhận hàng", "Tiền mặt khi nhận hàng"), ("Chuyển khoản", "Chuyển khoản")],
        default="Tiền mặt khi nhận hàng",
        validators=[DataRequired()]
    )
    submit = SubmitField("Xác nhận đặt hàng")


class BookForm(FlaskForm):
    title = StringField(
        "Tên sách *",
        validators=[DataRequired("Tên sách không được để trống."), Length(max=200)]
    )
    author = StringField(
        "Tác giả *",
        validators=[DataRequired("Tác giả không được để trống."), Length(max=100)]
    )
    category_id = SelectField("Danh mục *", coerce=int, validators=[DataRequired()])
    publisher = StringField("Nhà xuất bản", default="NXB Đại học Huế", validators=[Optional(), Length(max=100)])
    publish_year = IntegerField(
        "Năm xuất bản *",
        default=datetime.now().year,
        validators=[
            DataRequired("Vui lòng nhập năm xuất bản."),
            NumberRange(min=1900, max=datetime.now().year, message=f"Năm từ 1900 đến {datetime.now().year}.")
        ]
    )
    price = IntegerField(
        "Giá (đồng) *",
        validators=[
            DataRequired("Vui lòng nhập giá bán."),
            NumberRange(min=1000, message="Giá bán tối thiểu 1.000 đ.")
        ]
    )
    stock = IntegerField(
        "Tồn kho *",
        default=0,
        validators=[
            NumberRange(min=0, message="Tồn kho không âm.")
        ]
    )
    description = TextAreaField("Mô tả", validators=[Optional()])
    cover_image = FileField(
        "Ảnh bìa (JPG, PNG, WEBP ≤ 2MB)",
        validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Chỉ chấp nhận file JPG, PNG, WEBP!")]
    )
    submit = SubmitField("Lưu")

    def __init__(self, book_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.book_id = book_id

    def validate_title(self, field):
        stmt = db.select(Book).where(func.lower(Book.title) == field.data.strip().lower())
        if self.book_id:
            stmt = stmt.where(Book.id != self.book_id)
        if db.session.scalar(stmt):
            raise ValidationError("Tên sách này đã tồn tại.")

    def validate_cover_image(self, field):
        if field.data:
            field.data.seek(0, 2)
            size = field.data.tell()
            field.data.seek(0)
            if size > 2 * 1024 * 1024:
                raise ValidationError("Dung lượng ảnh tối đa 2 MB.")


class CategoryForm(FlaskForm):
    name = StringField(
        "Tên *",
        validators=[DataRequired("Tên danh mục không được để trống."), Length(max=100)]
    )
    description = TextAreaField("Mô tả", validators=[Optional(), Length(max=255)])
    submit = SubmitField("+ Thêm")

    def __init__(self, category_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category_id = category_id

    def validate_name(self, field):
        stmt = db.select(Category).where(func.lower(Category.name) == field.data.strip().lower())
        if self.category_id:
            stmt = stmt.where(Category.id != self.category_id)
        if db.session.scalar(stmt):
            raise ValidationError("Danh mục đã tồn tại.")