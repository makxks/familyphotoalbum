import os
import datetime
import functools

from flask import Flask, redirect, g, url_for, render_template, request
from PIL import Image
from flask_session import Session
from tempfile import mkdtemp
from flaskr.db import get_db
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

#from helpers import error_message

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass


    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["IMAGE_UPLOADS"] = os.path.join(app.instance_path,'/images')
    app.config["IMAGE_LOADS"] = ""
    app.config["ALLOWED_IMAGE_EXTENSIONS"] = ["JPEG", "JPG", "PNG", "GIF"]

    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response


    app.config["SESSION_FILE_DIR"] = mkdtemp()
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_TYPE"] = "filesystem"
    Session(app)

    from . import db
    db.init_app(app)

    from . import auth
    app.register_blueprint(auth.bp)

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
            #for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
            #                 ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            #    s = s.replace(old, new)
            return s
        return render_template("error_display.html", code=code, message=escape(message))


    def allowed_image(filename):

        # We only want files with a . in the filename
        if not "." in filename:
            return False

        # Split the extension from the filename
        ext = filename.rsplit(".", 1)[1]

        # Check if the extension is in ALLOWED_IMAGE_EXTENSIONS
        if ext.upper() in app.config["ALLOWED_IMAGE_EXTENSIONS"]:
            return True
        else:
            return False


    @app.route('/')
    def index():
        database = db.get_db()

        if g.user is None:
            return redirect(url_for('auth.login'))
        else:
            #get albums
            #render index with the list of albums
            received_albums = database.execute(
                """SELECT *
                FROM album
                JOIN user_album ON album.id = user_album.album_id
                JOIN user ON user_album.user_id = user.id
                WHERE user.id = ? AND album.created_by != ?""", (g.user['id'], g.user['id'])
            ).fetchall()

            received = []

            your_albums = database.execute(
                """SELECT *
                FROM album
                JOIN user_album ON album.id = user_album.album_id
                JOIN user ON user_album.user_id = user.id
                WHERE user.id = ? AND album.created_by = ?""", (g.user['id'], g.user['id'])
            ).fetchall()

            your = []

            ### get 1st image of each album as display / list image ?? ###
            for album in received_albums:
                album = dict(album)
                first_photo = database.execute(
                    """SELECT *
                    FROM photo
                    JOIN album_photo ON photo.id = album_photo.photo_id
                    JOIN album ON album_photo.album_id = album.id
                    WHERE album.id = ?
                    LIMIT 1""", (album['id'],)
                ).fetchone()

                album['first_photo'] = first_photo

                received.append(album)

            for album in your_albums:
                album = dict(album)
                first_photo = database.execute(
                    """SELECT *
                    FROM photo
                    JOIN album_photo ON photo.id = album_photo.photo_id
                    JOIN album ON album_photo.album_id = album.id
                    WHERE album.id = ?
                    LIMIT 1""", (album['id'],)
                ).fetchone()

                album['first_photo'] = first_photo

                your.append(album)

            return render_template('index.html', received_albums = received, your_albums = your)


    @app.route('/addAlbum', methods=['GET', 'POST'])
    @login_required
    def addAlbum():
        database = db.get_db()
        if request.method == 'POST':
            if not request.form['albumtitle']:
                return error_message("Please enter a title for the new photo album", 403)

            if not request.form['albumsharepassword']:
                return error_message("Please enter a password for link sharing", 403)

            album_title = request.form['albumtitle']
            created_on = datetime.datetime.now()
            created_by = g.user['id']
            hash = generate_password_hash(request.form['albumsharepassword'])
            album_id = database.execute(
                """INSERT INTO album (title, created_on, created_by, hash) VALUES (?, ?, ?, ?) RETURNING *""", (album_title, created_on, created_by, hash)
            )
            album = album_id.fetchone()
            database.execute(
                """INSERT INTO user_album (user_id, album_id) VALUES (?, ?)""", (g.user['id'], album['id'])
            )
            database.commit()
            return redirect(url_for('index'))
        else:
            return render_template('add-album.html')


    @app.route('/addComment', methods=['POST'])
    @login_required
    def addComment():
        database = db.get_db()
        if request.method == 'POST':
            comment = request.form['comment']
            album_id = request.form['album']
            user_id = g.user['id']

            comment = database.execute(
                """INSERT INTO comment (comment, user_id) VALUES (?, ?) RETURNING *""", (comment, user_id)
            )

            comment_id = comment.fetchone()['id']

            database.execute(
                """INSERT INTO album_comment (album_id, comment_id) VALUES (?, ?)""", (album_id, comment_id)
            )
            database.commit()

            return redirect(url_for("album", album_id = album_id))


    @app.route('/addPhoto/<album>', methods=['GET', 'POST'])
    @login_required
    def addPhoto(album):
        database = db.get_db()
        if request.method == 'POST':

            image = request.files['photo']
            title = request.form['photoname']

            if not allowed_image(image.filename):
                return error_message("Image type / filename not allowed", 403)

            if title == "":
                return error_message("Image must have a title", 403)

            save_title = title.replace(' ','')

            extension = os.path.splitext(image.filename)[1]

            save_title = save_title + extension

            init_filename = secure_filename(image.filename)

            filename = secure_filename(save_title)

            image.save(os.path.join(app.config["IMAGE_UPLOADS"], init_filename))

            with Image.open(os.path.join(app.config["IMAGE_UPLOADS"], init_filename)) as im:

                width = im.size[0]
                height = im.size[1]

                print ("before resize image width: " + str(width) + " image height: " + str(height))

                ### resize to max 640px (if dimensions are greater)

                if width > 640 or height > 640:
                    if width > height:
                        factor = 640/width
                        im = im.resize((int(width * factor), int(height * factor)))
                    else:
                        ### else ok here as factor will work the same for square case as well
                        factor = 640/height
                        im = im.resize((int(width * factor), int(height * factor)))

                location = os.path.join(app.config["IMAGE_UPLOADS"], save_title)

                im.save(location)

                created_on = datetime.datetime.now()
                created_by = g.user['id']

                photo = database.execute(
                    """INSERT INTO photo (title, created_on, created_by, location) VALUES (?, ?, ?, ?) RETURNING *""", (title, created_on, created_by, save_title)
                )

                photo_id = photo.fetchone()['id']

                database.execute(
                    """INSERT INTO album_photo (album_id, photo_id) VALUES (?, ?)""", (album, photo_id)
                )
                database.commit()

            os.remove(os.path.join(app.config["IMAGE_UPLOADS"], init_filename))

            return redirect(url_for("album", album_id = album))
        else:
            action = "/addPhoto/" + album
            return render_template('add-photo.html', action = action)


    @app.route('/album/<album_id>')
    @login_required
    def album(album_id):
        database = db.get_db()
        album = database.execute(
            """SELECT *
            FROM album
            JOIN user_album ON album.id = user_album.album_id
            JOIN user ON user_album.user_id = user.id
            WHERE user.id = ? AND album.id = ?""", (g.user['id'], album_id)
        ).fetchall()

        if album == None:
            return error_message("No album here, or no access granted yet", 403)

        # get photos
        photos = database.execute(
            """SELECT *
            FROM photo
            JOIN album_photo ON photo.id = album_photo.photo_id
            JOIN album ON album_photo.album_id = album.id
            WHERE album.id = ?""", (album_id,)
        ).fetchall()

        # get comments
        comments = database.execute(
            """SELECT *
            FROM comment
            JOIN album_comment ON comment.id = album_comment.comment_id
            JOIN album ON album_comment.album_id = album.id
            JOIN user ON comment.user_id = user.id
            WHERE album.id = ?""", (album_id,)
        ).fetchall()

        username = database.execute(
            """SELECT * FROM user WHERE id = ?""", (album[0]['created_by'],)
        ).fetchone()

        return render_template('album.html', album_title = album[0]['title'], album_id = album[0]['id'], album_photos = photos, comments = comments, user = g.user['id'], created_id = album[0]['created_by'], created_by = username['username'], created_on = album[0]['created_on'])


    @app.route('/albumPassword/<album_id>/<album_password>')
    def albumPassword(album_id, album_password):
        database = db.get_db()
        album = database.execute(
            """SELECT * FROM album WHERE id = ?""", (album_id,)
        ).fetchall()

        if album == None:
            return error_message("No album here", 403)

        if check_password_hash(album[0]["hash"], album_password):
            # get photos
            photos = database.execute(
                """SELECT *
                FROM photo
                JOIN album_photo ON photo.id = album_photo.photo_id
                JOIN album ON album_photo.album_id = album.id
                WHERE album.id = ?""", (album_id,)
            ).fetchall()

            # get comments
            comments = database.execute(
                """SELECT *
                FROM comment
                JOIN album_comment ON comment.id = album_comment.comment_id
                JOIN album ON album_comment.album_id = album.id
                WHERE album.id = ?""", (album_id,)
            ).fetchall()

            username = database.execute(
                """SELECT * FROM user WHERE id = ?""", (album[0]['created_by'],)
            ).fetchone()

            user = None

            if g.user is not None:
                user = g.user['id']

            return render_template('album.html', album_title = album[0]['title'], album_id = album_id, album_photos = photos, comments = comments, user = user, created_id = album[0]['created_by'], created_by = username['username'], created_on = album[0]['created_on'])

        else:
            return error_message("Link incorrect", 403)

    @app.route('/albumPasswordTwo/<album_id>/<hash1>/<hash2>')
    def albumPasswordTwo(album_id, hash1, hash2):
        database = db.get_db()
        album = database.execute(
            """SELECT * FROM album WHERE id = ?""", (album_id,)
        ).fetchall()

        if album == None:
            return error_message("No album here", 403)

        if check_password_hash(hash2, album[0]["created_on"]) and hash1 == album[0]["hash"]:
            # get photos
            photos = database.execute(
                """SELECT *
                FROM photo
                JOIN album_photo ON photo.id = album_photo.photo_id
                JOIN album ON album_photo.album_id = album.id
                WHERE album.id = ?""", (album_id,)
            ).fetchall()

            # get comments
            comments = database.execute(
                """SELECT *
                FROM comment
                JOIN album_comment ON comment.id = album_comment.comment_id
                JOIN album ON album_comment.album_id = album.id
                WHERE album.id = ?""", (album_id,)
            ).fetchall()

            username = database.execute(
                """SELECT * FROM user WHERE id = ?""", (album[0]['created_by'],)
            ).fetchone()

            user = None

            if g.user is not None:
                user = g.user['id']

            return render_template('album.html', album_title = album[0]['title'], album_id = album_id, album_photos = photos, comments = comments, user = user, created_id = album[0]['created_by'], created_by = username['username'], created_on = album[0]['created_on'])

        else:
            return error_message("Link incorrect", 403)


    @app.route('/photo/<photo_id>')
    @login_required
    def photo(photo_id):
        database = db.get_db()
        # Get photo
        photo_data = database.execute(
            """SELECT * FROM photo WHERE id = ?""", (photo_id,)
        ).fetchall()

        return render_template('photo.html', photo = photo_data)


    @app.route('/deleteAlbum/<album>', methods=["GET", "POST"])
    @login_required
    def deleteAlbum(album):
        database = db.get_db()
        if request.method == 'POST':
            ## get photo ids
            album_photos = database.execute(
                """SELECT *
                FROM photo
                JOIN album_photo ON photo.id = album_photo.photo_id
                JOIN album ON album_photo.album_id = album.id
                WHERE album.id = ?""", (album,)
            ).fetchall()

            for photo in album_photos:
                database.execute(
                    """DELETE FROM photo WHERE id = ?""", (photo['id'],)
                )
                os.remove(os.path.join(app.config["IMAGE_UPLOADS"], photo['location']))

            album_comments = database.execute(
                """SELECT *
                FROM comment
                JOIN album_comment ON comment.id = album_comment.comment_id
                JOIN album ON album_comment.album_id = album.id
                WHERE album.id = ?""", (album,)
            ).fetchall()

            for comment in album_comments:
                database.execute(
                    """DELETE FROM photo WHERE id = ?""", (comment['id'],)
                )

            database.execute(
                """DELETE FROM user_album WHERE album_id = ?""", (album,)
            )

            database.execute(
                """DELETE FROM album WHERE id = ?""", (album,)
            )
            database.commit()

            return redirect(url_for("index"))
        else:
            action = '/deleteAlbum/' + album
            return render_template('delete-album.html', action = action)


    @app.route('/deletePhoto/<photo>', methods=["GET", "POST"])
    @login_required
    def deletePhoto(photo):
        database = db.get_db()
        if request.method == 'POST':
            filename = database.execute(
                """SELECT * FROM photo WHERE photo.id = ?""", (photo,)
            ).fetchone()

            database.execute(
                """DELETE FROM photo WHERE photo.id = ?""", (photo,)
            )

            database.execute(
                """DELETE FROM album_photo WHERE album_photo.photo_id = ?""", (photo,)
            )
            database.commit()

            os.remove(os.path.join(app.config["IMAGE_UPLOADS"], filename['location']))

            return redirect(url_for("index"))
        else:
            action = '/deletePhoto/' + photo
            return render_template('delete-photo.html', action = action)


    @app.route('/editAlbum/<album>', methods=['GET', 'POST'])
    @login_required
    def editAlbum(album):
        database = db.get_db()
        if request.method == 'POST':
            if not request.form['albumtitle'] and not request.form['albumpassword']:
                return error_message("No information provided for edit", 403)

            album_id = album

            album = database.execute(
                """SELECT * from album WHERE id = ?""", (album_id,)
            ).fetchall()

            new_album_title = album[0]['title']

            new_hash = album[0]['hash']

            if request.form['albumtitle']:
                new_album_title = request.form['albumtitle']

            if request.form['albumpassword']:
                new_hash = generate_password_hash(request.form['albumpassword'])

            database.execute(
                """UPDATE album
                SET title = ?, hash = ?
                WHERE id = ?""", (new_album_title, new_hash, album_id)
            )
            database.commit()

            return redirect(url_for("album", album_id = album_id))
        else:
            action = '/editAlbum/' + album
            return render_template('edit-album.html', action = action, album_id = album)


    @app.route('/editPhoto/<album>/<photo>', methods=['GET', 'POST'])
    @login_required
    def editPhoto(album, photo):
        database = db.get_db()
        if request.method == 'POST':
            if not request.form['phototitle']:
                return error_message("No information provided for edit", 403)

            photo_id = photo

            photo = database.execute(
                """SELECT * FROM photo WHERE id = ?""", (photo_id,)
            ).fetchall()

            new_photo_title = photo[0]['title']

            if request.form['phototitle']:
                new_photo_title = request.form['phototitle']

            database.execute(
                """UPDATE photo
                SET title = ?
                WHERE id = ?""", (new_photo_title, photo_id)
            )
            database.commit()

            return redirect(url_for("album", album_id = album))
        else:
            action = '/editPhoto/' + album + '/' + photo
            action2 = '/rotatePhoto/' + album + '/' + photo
            return render_template('edit-photo.html', action = action, action2 = action2, photo_id = photo)


    @app.route('/rotatePhoto/<album>/<photo>', methods=['POST'])
    @login_required
    def rotatePhoto(album, photo):
        database = db.get_db()
        if request.method == 'POST':
            angle = -1 * int(request.form['photorotation'])

            if not isinstance(angle, (int, float)):
                return error_message("Rotation angle must be a number value", 403)

            photo = database.execute(
                """SELECT * FROM photo WHERE id = ?""", (photo,)
            ).fetchall()

            with Image.open(os.path.join(app.config["IMAGE_UPLOADS"], photo[0]['location'])) as im:

                im = im.rotate(angle, expand=True)

                im.save(os.path.join(app.config["IMAGE_UPLOADS"], photo[0]['location']))

                return redirect(url_for("album", album_id = album))

        else:
            return error_message("Request not allowed", 403)


    @app.route('/sharePhoto', methods=['POST'])
    @login_required
    def sharePhoto():
        database = db.get_db()
        # share-to by form
        share_to = request.form['share-to']
        photo_id = request.form['photo']

        user = database.execute(
            """SELECT * FROM user WHERE username = ?""", (share-to,)
        ).fetchall()

        photo = database.execute(
            """SELECT * FROM photo WHERE id = ?""", (photo_id,)
        ).fetchall()

        if not user:
            return error_message("No user found", 403)

        created_on = datetime.datetime.now()
        created_by = g.user['id']

        hash_string = string(created_by) + string(created_on) + string(photo[0]['title'])

        hash = generate_password_hash(hash_string)

        new_album = database.execute(
            """INSERT INTO album (title, created_on, created_by, hash) VALUES (?, ?, ?, ?) RETURNING id""", (photo[0]['title'], created_on, created_by, hash)
        )

        database.execute(
            """INSERT INTO user_album (user_id, album_id) VALUES (?, ?)""", (user[0]['id'], new_album)
        )
        database.commit()

        return redirect('/')


    @app.route('/sharePhotoForm/<photo>', methods=['GET'])
    @login_required
    def sharePhotoForm(photo):
        return render_template('share-photo.html', photo = photo)


    @app.route('/shareAlbum', methods=['POST'])
    @login_required
    def shareAlbum():
        database = db.get_db()

        # share-to by form
        share_to = request.form['share-to']
        album_id = request.form['album']

        user = database.execute(
            """SELECT * FROM user WHERE username = ?""", (share_to,)
        ).fetchall()

        if not user:
            return error_message("No user found", 403)

        database.execute(
            """INSERT INTO user_album (user_id, album_id) VALUES (?, ?)""", (user[0]['id'], album_id)
        )
        database.commit()

        return redirect('/')

    @app.route('/shareAlbumForm/<album>', methods=['GET'])
    @login_required
    def shareAlbumForm(album):
        database = db.get_db()
        album_id = album

        album_data = database.execute(
            """SELECT * FROM album WHERE id = ?""", (album,)
        ).fetchall()

        album_hash_1 = album_data[0]["hash"]
        album_hash_2 = generate_password_hash(album_data[0]["created_on"])

        album_link = url_for("albumPasswordTwo", album_id = album_id, hash1 = album_hash_1, hash2 = album_hash_2, _external = True)
        password_link = url_for("albumPassword", album_id = album_id, album_password = 'CHANGE_THIS', _external = True)

        return render_template('share-album.html', album = album_id, album_link = album_link, password_link = password_link)


    def errorhandler(e):
        """Handle error"""
        if not isinstance(e, HTTPException):
            e = InternalServerError()
        return error_message(e.name, e.code)


    for code in default_exceptions:
        app.errorhandler(code)(errorhandler)


    return app
