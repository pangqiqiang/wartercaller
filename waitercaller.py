from flask import Flask
from flask import render_template
from flask_login import LoginManager
from flask_login import login_required
from flask_login import login_user
from flask_login import logout_user
from flask_login import current_user
from flask import url_for
from flask import redirect
from flask import request
from passwordhelper import PasswordHelper
from bitlyhelper import BitlyHelper
from forms import CreateTableForm
from forms import RegistrationForm
from forms import LoginForm
from user import User
import config
if config.test:
    from mockdbhelper import MockDBHelper as DBHelper
else:
    from dbhelper import DBHelper
import datetime


app = Flask(__name__)
login_manager = LoginManager(app)
DB = DBHelper()
PH = PasswordHelper()
BH = BitlyHelper()

app.secret_key = 'tPXJY3X37Qybz4QykV+hOyUxVQeEXf1Ao2C8upz+fGQXKsM'


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/account")
@login_required
def account():
    tables = DB.get_tables(current_user.get_id())
    return render_template("account.html",
                           createtableform=CreateTableForm(), tables=tables)


@app.route("/account/createtable", methods=["POST"])
@login_required
def account_createtable():
    form = CreateTableForm(request.form)
    if form.validate():
        tableid = DB.add_table(form.tablenumber.data,
                               current_user.get_id())
        new_url = BH.shorten_url(
            config.base_url + "newrequest/" + str(tableid))
        DB.update_table(tableid, new_url)
        return redirect(url_for('account'))
    return render_template("account.html", createtableform=form,
                           tables=DB.get_tables(current_user.get_id()))


@app.route("/account/deletetable", methods=["POST", "GET"])
@login_required
def account_deletetable():
    tableid = request.args.get("tableid")
    print(tableid)
    DB.delete_table(tableid)
    return redirect(url_for("account"))


@app.route("/register", methods=["POST"])
def register():
    email = request.form.get("email")
    pw1 = request.form.get("pw1")
    pw2 = request.form.get("pw2")
    if not pw1 == pw2:
        return redirect(url_for("home"))
    if DB.get_user(email):
        return redirect(url_for("home"))
    salt = PH.get_salt()
    hashed = PH.get_hash(pw1 + salt)
    DB.add_user(email, salt, hashed)
    return redirect(url_for('home'))


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")
    stored_user = DB.get_user(email)
    if stored_user and PH.validate_password(password,
                                            stored_user['salt'],
                                            stored_user['hashed']):
        user = User(email)
        login_user(user, remember=True)
        return redirect(url_for('account'))
    return home()


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required
def dashboard():
    now = datetime.datetime.now()
    requests = DB.get_requests(current_user.get_id())
    for req in requests:
        deltaseconds = (now - req['time']).seconds
        req["wait_minutes"] = "{}.{}".format(deltaseconds // 60,
                                             str(deltaseconds % 60).zfill(2))
    return render_template("dashboard.html", requests=requests)


@app.route("/dashboard/resolve")
@login_required
def dashboard_resolve():
    request_id = request.args.get("request_id")
    DB.delete_request(request_id)
    return redirect(url_for('dashboard'))


@app.route("/newrequest/<tid>")
def newRequest(tid):
    if DB.add_request(tid, datetime.datetime.now()):
        return 'Your request has been logged and a  waiter will be with you shortly'
    return 'There is already a request pending for this table. Please be patient, a waiter will be there ASAP'


@login_manager.user_loader
def load_user(user_id):
    user_password = DB.get_user(user_id)
    if user_password:
        return User(user_id)


if __name__ == "__main__":
    app.run(port=5000, debug=True)
