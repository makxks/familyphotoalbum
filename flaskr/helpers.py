import functools

from flask import g, redirect, render_template, url_for, request

def login_required(f):
    """
    Decorate routes to require login.
    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @functools.wraps(f)
    def decorated_function(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return f(**kwargs)
    return decorated_function

def error_message(message, code=400):
    """Render error message display to the user"""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("error_display.html", code=code, message=escape(message))
