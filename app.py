from flask import Flask, render_template, request

app = Flask(__name__)

def parse_number(val_str):
    if not val_str or not val_str.strip():
        return None, "Vui lòng nhập một số."
    clean_str = val_str.strip().replace(",", ".")
    try:
        return float(clean_str), None
    except ValueError:
        return None, "Vui lòng nhập một số."


def format_num(n):
    return str(int(n)) if n.is_integer() else str(n)


def validate_score(val_str):
    if not val_str or not val_str.strip():
        return None, "Vui lòng nhập một số."
    clean_str = val_str.strip().replace(",", ".")
    try:
        score = float(clean_str)
    except ValueError:
        return None, "Vui lòng nhập một số."

    if score < 0 or score > 10:
        return None, "Điểm phải từ 0 đến 10."
    return score, None


def validate_height(val_str):
    if not val_str or not val_str.strip():
        return None, "Vui lòng nhập một số."
    clean_str = val_str.strip().replace(",", ".")
    try:
        h = float(clean_str)
    except ValueError:
        return None, "Vui lòng nhập một số."

    if h < 50 or h > 250:
        return None, "Giá trị phải từ 50 đến 250. (nhập mét thay vì cm)"
    return h, None


def validate_weight(val_str):
    if not val_str or not val_str.strip():
        return None, "Vui lòng nhập một số."
    clean_str = val_str.strip().replace(",", ".")
    try:
        w = float(clean_str)
    except ValueError:
        return None, "Vui lòng nhập một số."

    if w < 10 or w > 300:
        return None, "Giá trị phải từ 10 đến 300."
    return w, None

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/bai1", methods=["GET", "POST"])
def bai1():
    a_str, b_str, op = "", "", "+"
    error_a, error_b, error_general, result_str = None, None, None, None

    if request.method == "POST":
        a_str = request.form.get("a", "")
        b_str = request.form.get("b", "")
        op = request.form.get("op", "+")

        val_a, error_a = parse_number(a_str)
        val_b, error_b = parse_number(b_str)

        if op not in ["+", "-", "*", "/"]:
            error_general = "Phép toán không hợp lệ."

        if val_b == 0 and op == "/":
            error_b = "Không thể chia cho 0."

        if not error_a and not error_b and not error_general:
            if op == "+":
                res = val_a + val_b
            elif op == "-":
                res = val_a - val_b
            elif op == "*":
                res = val_a * val_b
            elif op == "/":
                res = val_a / val_b
            result_str = f"{format_num(val_a)} {op} {format_num(val_b)} = {format_num(res)}"

    return render_template(
        "bai1.html",
        a=a_str,
        b=b_str,
        op=op,
        error_a=error_a,
        error_b=error_b,
        error_general=error_general,
        result=result_str,
    )


@app.route("/bai2", methods=["GET", "POST"])
def bai2():
    cc_str, gk_str, ck_str = "", "", ""
    error_cc, error_gk, error_ck, result_str = None, None, None, None

    if request.method == "POST":
        cc_str = request.form.get("cc", "")
        gk_str = request.form.get("gk", "")
        ck_str = request.form.get("ck", "")

        cc, error_cc = validate_score(cc_str)
        gk, error_gk = validate_score(gk_str)
        ck, error_ck = validate_score(ck_str)

        if error_cc is None and error_gk is None and error_ck is None:
            total_score = round(cc * 0.1 + gk * 0.3 + ck * 0.6, 1)
            if ck < 1.0:
                letter_grade = "F (điểm thi dưới 1)"
            else:
                if total_score >= 8.5:
                    letter_grade = "A"
                elif total_score >= 7.0:
                    letter_grade = "B"
                elif total_score >= 5.5:
                    letter_grade = "C"
                elif total_score >= 4.0:
                    letter_grade = "D"
                else:
                    letter_grade = "F"
            result_str = f"{total_score} - {letter_grade}"

    return render_template(
        "bai2.html",
        cc=cc_str,
        gk=gk_str,
        ck=ck_str,
        error_cc=error_cc,
        error_gk=error_gk,
        error_ck=error_ck,
        result=result_str,
    )


@app.route("/bai3", methods=["GET", "POST"])
def bai3():
    cao_str, nang_str = "", ""
    error_cao, error_nang = None, None
    bmi_res, category, alert_class, weight_range = None, None, None, None

    if request.method == "POST":
        cao_str = request.form.get("cao", "")
        nang_str = request.form.get("nang", "")

        cao_cm, error_cao = validate_height(cao_str)
        nang_kg, error_nang = validate_weight(nang_str)

        if error_cao is None and error_nang is None:
            height_m = cao_cm / 100
            bmi_res = round(nang_kg / (height_m**2), 1)
            if bmi_res < 18.5:
                category = "Thiếu cân"
                alert_class = "warning"  
            elif bmi_res < 23:
                category = "Bình thường"
                alert_class = "success"  
            elif bmi_res < 25:
                category = "Thừa cân"
                alert_class = "warning"  
            else:
                category = "Béo phì"
                alert_class = "danger"  

            min_w = round(18.5 * (height_m**2), 1)
            max_w = round(22.9 * (height_m**2), 1)
            weight_range = f"{min_w} – {max_w} kg"

    return render_template(
        "bai3.html",
        cao=cao_str,
        nang=nang_str,
        error_cao=error_cao,
        error_nang=error_nang,
        bmi=bmi_res,
        category=category,
        alert_class=alert_class,
        weight_range=weight_range,
    )


if __name__ == "__main__":
    app.run(debug=True)