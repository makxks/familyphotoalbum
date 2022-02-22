import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from flaskr.db import get_db

#from helpers import error_message

bp = Blueprint('auth', __name__, url_prefix='/auth')

def error_message(message, code=400):
    """Render error message display to the user"""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        #for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
        #                 ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
        #    s = s.replace(old, new)
        return s
    return render_template("error_display.html", code=code, message=escape(message))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # add checks for form input
        # show in a view

        username = request.form['username']
        password = request.form['password']
        confirmation = request.form['confirm']

        db = get_db()

        error = None

        usercheck = db.execute("SELECT * FROM user WHERE username = ?", (username,))

        print(len(usercheck.fetchall()))

        if (not username) or (len(usercheck.fetchall()) > 0) or (not password) or (not confirmation) or (password != confirmation):
            return error_message("registration error - check that all fields have been entered and that password and confirmation match", 400)

        if error is None:
            try:
                db.execute(
                    "INSERT INTO user (username, hash) VALUES (?, ?)", (username, generate_password_hash(password))
                )
                db.commit()
                return redirect(url_for('index'))
            except db.IntegrityError:
                error = f"User {username} is already registered."
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template("auth/register.html")


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # add checks for form input
        # show in a view

        username = request.form['username']
        password = request.form['password']

        db = get_db()

        error = None

        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        if not username:
            return error_message("must provide username", 403)

        # Ensure password was submitted
        elif not password:
            return error_message("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM user WHERE username = ?", (request.form["username"],)).fetchall()

        if len(rows) != 1:
            return error_message("invalid username and/or password", 403)

        # Ensure username exists and password is correct
        if not check_password_hash(rows[0]["hash"], request.form["password"]):
            return error_message("invalid username and/or password", 403)

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/login.html')


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()
