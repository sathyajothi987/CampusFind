from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    send_from_directory
)

import sqlite3
import os
import re
import secrets
import io

import qrcode

from functools import wraps

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)

app.secret_key = "campusfind_secret_key"


# ============================================================
# DATABASE
# ============================================================

DATABASE = os.path.join(
    "database",
    "campusfind.db"
)


# ============================================================
# UPLOAD FOLDERS
# ============================================================

UPLOAD_FOLDER_LOST = os.path.join(
    "uploads",
    "lost"
)

UPLOAD_FOLDER_FOUND = os.path.join(
    "uploads",
    "found"
)

os.makedirs(
    UPLOAD_FOLDER_LOST,
    exist_ok=True
)

os.makedirs(
    UPLOAD_FOLDER_FOUND,
    exist_ok=True
)


# ============================================================
# ALLOWED IMAGE TYPES
# ============================================================

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp"
}


def allowed_file(filename):

    return (
        "." in filename
        and
        filename.rsplit(
            ".",
            1
        )[1].lower()
        in ALLOWED_EXTENSIONS
    )


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_connection():

    os.makedirs(
        "database",
        exist_ok=True
    )

    connection = sqlite3.connect(
        DATABASE
    )

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# ADMIN ACCESS CHECK
# ============================================================

def admin_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        # ----------------------------------------------------
        # LOGIN CHECK
        # ----------------------------------------------------

        if "user_id" not in session:

            if request.path.startswith("/api/"):

                return jsonify({
                    "success": False,
                    "message": "Please login first."
                }), 401

            flash(
                "Please login to access the admin dashboard.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        # ----------------------------------------------------
        # ADMIN ROLE CHECK
        # ----------------------------------------------------

        if session.get("user_role") != "admin":

            if request.path.startswith("/api/"):

                return jsonify({
                    "success": False,
                    "message": "Access denied. Admins only."
                }), 403

            return (
                "Access denied. Admins only.",
                403
            )

        return function(
            *args,
            **kwargs
        )

    return decorated_function


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_database():

    connection = get_db_connection()


    # ========================================================
    # USERS TABLE
    # ========================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT NOT NULL UNIQUE,

            password TEXT NOT NULL,

            role TEXT DEFAULT 'student',

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP

        )
    """)


    # ========================================================
    # ADD ROLE COLUMN TO OLD DATABASE
    # ========================================================

    columns = connection.execute(
        "PRAGMA table_info(users)"
    ).fetchall()


    column_names = [
        column["name"]
        for column in columns
    ]


    if "role" not in column_names:

        connection.execute("""
            ALTER TABLE users
            ADD COLUMN role TEXT DEFAULT 'student'
        """)


    # ========================================================
    # OLD USERS ARE STUDENTS
    # ========================================================

    connection.execute("""
        UPDATE users

        SET role = 'student'

        WHERE role IS NULL
        OR role = ''
    """)


    # ========================================================
    # LOST AND FOUND ITEMS TABLE
    # ========================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS lost_found_items (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            item_name TEXT NOT NULL,

            description TEXT,

            category TEXT NOT NULL,

            location TEXT NOT NULL,

            status TEXT NOT NULL,

            image TEXT,

            reported_by INTEGER,

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (reported_by)
            REFERENCES users(id)

        )
    """)


    # ========================================================
    # NOTIFICATIONS TABLE
    #
    # found_item_id is allowed to be NULL.
    #
    # Why?
    # A global notification for a newly reported LOST item
    # does not have a found item yet.
    # ========================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS notifications (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            lost_item_id INTEGER,

            found_item_id INTEGER,

            message TEXT NOT NULL,

            is_read INTEGER DEFAULT 0,

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
            REFERENCES users(id),

            FOREIGN KEY (lost_item_id)
            REFERENCES lost_found_items(id),

            FOREIGN KEY (found_item_id)
            REFERENCES lost_found_items(id)

        )
    """)


    # ========================================================
    # MIGRATE OLD NOTIFICATIONS TABLE
    #
    # Older CampusFind database versions had:
    #
    # found_item_id INTEGER NOT NULL
    #
    # We need to allow NULL for global LOST notifications.
    # ========================================================

    notification_columns = connection.execute(
        "PRAGMA table_info(notifications)"
    ).fetchall()


    notification_column_info = {
        column["name"]: column
        for column in notification_columns
    }


    if (
        "found_item_id" in notification_column_info
        and
        notification_column_info["found_item_id"]["notnull"] == 1
    ):

        # ----------------------------------------------------
        # Create new compatible table
        # ----------------------------------------------------

        connection.execute("""
            CREATE TABLE IF NOT EXISTS notifications_new (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL,

                lost_item_id INTEGER,

                found_item_id INTEGER,

                message TEXT NOT NULL,

                is_read INTEGER DEFAULT 0,

                created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                REFERENCES users(id),

                FOREIGN KEY (lost_item_id)
                REFERENCES lost_found_items(id),

                FOREIGN KEY (found_item_id)
                REFERENCES lost_found_items(id)

            )
        """)


        # ----------------------------------------------------
        # Copy old notification data
        # ----------------------------------------------------

        connection.execute("""
            INSERT INTO notifications_new
            (
                id,
                user_id,
                lost_item_id,
                found_item_id,
                message,
                is_read,
                created_at
            )

            SELECT
                id,
                user_id,
                lost_item_id,
                found_item_id,
                message,
                is_read,
                created_at

            FROM notifications
        """)


        # ----------------------------------------------------
        # Remove old table
        # ----------------------------------------------------

        connection.execute("""
            DROP TABLE notifications
        """)


        # ----------------------------------------------------
        # Rename new table
        # ----------------------------------------------------

        connection.execute("""
            ALTER TABLE notifications_new
            RENAME TO notifications
        """)


    # ========================================================
    # CLAIMS TABLE
    # ========================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS claims (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            item_id INTEGER NOT NULL,

            claimant_id INTEGER NOT NULL,

            claimant_name TEXT NOT NULL,

            claimant_email TEXT NOT NULL,

            proof TEXT NOT NULL,

            reason TEXT NOT NULL,

            status TEXT DEFAULT 'Pending',

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (item_id)
            REFERENCES lost_found_items(id),

            FOREIGN KEY (claimant_id)
            REFERENCES users(id)

        )
    """)


    # ========================================================
    # QR / HANDOVER COLUMNS FOR CLAIMS
    # ========================================================

    claim_columns = connection.execute(
        "PRAGMA table_info(claims)"
    ).fetchall()

    claim_column_names = [
        column["name"]
        for column in claim_columns
    ]

    if "qr_token" not in claim_column_names:
        connection.execute("""
            ALTER TABLE claims
            ADD COLUMN qr_token TEXT
        """)

    if "handover_status" not in claim_column_names:
        connection.execute("""
            ALTER TABLE claims
            ADD COLUMN handover_status TEXT DEFAULT 'Pending'
        """)

    if "verified_at" not in claim_column_names:
        connection.execute("""
            ALTER TABLE claims
            ADD COLUMN verified_at TIMESTAMP
        """)

    if "verified_by" not in claim_column_names:
        connection.execute("""
            ALTER TABLE claims
            ADD COLUMN verified_by INTEGER
        """)

    connection.execute("""
        UPDATE claims
        SET handover_status = 'Pending'
        WHERE handover_status IS NULL
        OR handover_status = ''
    """)


    # ========================================================
    # CLAIM NOTIFICATIONS TABLE
    # ========================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS claim_notifications (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            claim_id INTEGER NOT NULL,

            message TEXT NOT NULL,

            is_read INTEGER DEFAULT 0,

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
            REFERENCES users(id),

            FOREIGN KEY (claim_id)
            REFERENCES claims(id)

        )
    """)


    connection.commit()

    connection.close()


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):

    if not text:

        return ""

    text = str(
        text
    ).lower().strip()

    text = re.sub(
        r"[^\w\s]",
        " ",
        text,
        flags=re.UNICODE
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


# ============================================================
# MATCH SCORE
# ============================================================

def calculate_match_score(
    lost_item,
    found_item
):

    score = 0


    # ========================================================
    # ITEM NAME
    # ========================================================

    lost_name = normalize_text(
        lost_item["item_name"]
    )

    found_name = normalize_text(
        found_item["item_name"]
    )


    if lost_name == found_name:

        score += 50

    else:

        lost_words = set(
            lost_name.split()
        )

        found_words = set(
            found_name.split()
        )

        common_words = (
            lost_words &
            found_words
        )

        if common_words:

            score += 30


    # ========================================================
    # CATEGORY
    # ========================================================

    if (
        normalize_text(
            lost_item["category"]
        )
        ==
        normalize_text(
            found_item["category"]
        )
    ):

        score += 20


    # ========================================================
    # LOCATION
    # ========================================================

    if (
        normalize_text(
            lost_item["location"]
        )
        ==
        normalize_text(
            found_item["location"]
        )
    ):

        score += 20


    # ========================================================
    # DESCRIPTION
    # ========================================================

    lost_description = normalize_text(
        lost_item["description"]
    )

    found_description = normalize_text(
        found_item["description"]
    )


    if (
        lost_description
        and
        found_description
    ):

        lost_words = set(
            lost_description.split()
        )

        found_words = set(
            found_description.split()
        )

        common_words = (
            lost_words &
            found_words
        )

        if common_words:

            score += 10


    return score


# ============================================================
# CREATE MATCH NOTIFICATIONS
# ============================================================

def create_match_notifications(
    found_item_id
):

    connection = get_db_connection()


    # ========================================================
    # GET FOUND ITEM
    # ========================================================

    found_item = connection.execute(
        """
        SELECT *
        FROM lost_found_items
        WHERE id = ?
        AND status = 'Found'
        """,
        (
            found_item_id,
        )
    ).fetchone()


    if not found_item:

        connection.close()

        return


    # ========================================================
    # GET LOST ITEMS
    # ========================================================

    lost_items = connection.execute(
        """
        SELECT *
        FROM lost_found_items
        WHERE status = 'Lost'
        """
    ).fetchall()


    # ========================================================
    # COMPARE ITEMS
    # ========================================================

    for lost_item in lost_items:

        # ----------------------------------------------------
        # DO NOT MATCH USER'S OWN ITEMS
        # ----------------------------------------------------

        if (
            lost_item["reported_by"]
            ==
            found_item["reported_by"]
        ):

            continue


        score = calculate_match_score(
            lost_item,
            found_item
        )


        # ----------------------------------------------------
        # MATCH THRESHOLD
        # ----------------------------------------------------

        if score >= 50:

            existing_notification = connection.execute(
                """
                SELECT id
                FROM notifications

                WHERE user_id = ?

                AND lost_item_id = ?

                AND found_item_id = ?
                """,
                (
                    lost_item["reported_by"],
                    lost_item["id"],
                    found_item["id"]
                )
            ).fetchone()


            if existing_notification:

                continue


            message = (
                f"Possible match found for your lost item "
                f"'{lost_item['item_name']}'. "
                f"A similar item was reported found at "
                f"{found_item['location']}."
            )


            connection.execute(
                """
                INSERT INTO notifications
                (
                    user_id,
                    lost_item_id,
                    found_item_id,
                    message
                )

                VALUES (?, ?, ?, ?)
                """,
                (
                    lost_item["reported_by"],
                    lost_item["id"],
                    found_item["id"],
                    message
                )
            )


    connection.commit()

    connection.close()


# ============================================================
# CREATE GLOBAL LOST ITEM NOTIFICATIONS
# ============================================================
#
# NEW FEATURE
#
# Whenever ANY user reports a LOST item:
#
#     ALL REGISTERED USERS
#
# receive a notification.
#
# The reporter also receives the notification because the
# requirement says "all users".
# ============================================================

def create_global_lost_notification(
    lost_item_id
):

    connection = get_db_connection()


    # ========================================================
    # GET LOST ITEM
    # ========================================================

    lost_item = connection.execute(
        """
        SELECT
            lost_found_items.id,
            lost_found_items.item_name,
            lost_found_items.category,
            lost_found_items.location,
            lost_found_items.reported_by,
            users.name AS reporter_name

        FROM lost_found_items

        INNER JOIN users
            ON lost_found_items.reported_by = users.id

        WHERE lost_found_items.id = ?

        AND lost_found_items.status = 'Lost'
        """,
        (
            lost_item_id,
        )
    ).fetchone()


    if not lost_item:

        connection.close()

        return


    # ========================================================
    # GET ALL REGISTERED USERS
    # ========================================================

    users = connection.execute(
        """
        SELECT id
        FROM users
        """
    ).fetchall()


    # ========================================================
    # NOTIFICATION MESSAGE
    # ========================================================

    message = (
        f"{lost_item['reporter_name']} reported a lost item: "
        f"'{lost_item['item_name']}' "
        f"at {lost_item['location']}."
    )


    # ========================================================
    # CREATE NOTIFICATION FOR EVERY USER
    # ========================================================

    for user in users:

        # ----------------------------------------------------
        # PREVENT DUPLICATE GLOBAL NOTIFICATION
        # ----------------------------------------------------

        existing_notification = connection.execute(
            """
            SELECT id

            FROM notifications

            WHERE user_id = ?

            AND lost_item_id = ?

            AND found_item_id IS NULL
            """,
            (
                user["id"],
                lost_item_id
            )
        ).fetchone()


        if existing_notification:

            continue


        connection.execute(
            """
            INSERT INTO notifications
            (
                user_id,
                lost_item_id,
                found_item_id,
                message
            )

            VALUES (?, ?, NULL, ?)
            """,
            (
                user["id"],
                lost_item_id,
                message
            )
        )


    connection.commit()

    connection.close()


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html",
        logged_in="user_id" in session,
        user_name=session.get(
            "user_name"
        ),
        is_admin=session.get(
            "user_role"
        ) == "admin"
    )


# ============================================================
# ABOUT PAGE
# ============================================================

@app.route("/about")
def about():

    return render_template(
        "about.html"
    )


# ============================================================
# FEATURES PAGE
# ============================================================

@app.route("/features")
def features():

    return render_template(
        "features.html"
    )


# ============================================================
# CONTACT PAGE
# ============================================================

@app.route("/contact")
def contact():

    return render_template(
        "contact.html"
    )


# ============================================================
# SEARCH PAGE
# ============================================================

@app.route("/search")
def search():

    return render_template(
        "search.html"
    )


# ============================================================
# SEARCH API
# ============================================================

@app.route("/api/search")
def api_search():

    item = request.args.get(
        "item",
        ""
    ).strip()

    category = request.args.get(
        "category",
        ""
    ).strip()

    location = request.args.get(
        "location",
        ""
    ).strip()

    status = request.args.get(
        "status",
        ""
    ).strip()


    connection = get_db_connection()


    query = """
        SELECT
            id,
            item_name,
            description,
            category,
            location,
            status,
            image,
            created_at

        FROM lost_found_items

        WHERE 1 = 1
    """


    parameters = []


    if item:

        query += """
            AND item_name LIKE ?
        """

        parameters.append(
            f"%{item}%"
        )


    if category:

        query += """
            AND category = ?
        """

        parameters.append(
            category
        )


    if location:

        query += """
            AND location = ?
        """

        parameters.append(
            location
        )


    if status:

        query += """
            AND status = ?
        """

        parameters.append(
            status
        )


    query += """
        ORDER BY created_at DESC
    """


    items = connection.execute(
        query,
        parameters
    ).fetchall()


    connection.close()


    results = []


    for item_row in items:

        results.append({

            "id":
                item_row["id"],

            "item_name":
                item_row["item_name"],

            "description":
                item_row["description"] or "",

            "category":
                item_row["category"],

            "location":
                item_row["location"],

            "status":
                item_row["status"],

            "image":
                item_row["image"],

            "created_at":
                item_row["created_at"]

        })


    return jsonify({

        "success": True,

        "count":
            len(results),

        "items":
            results

    })


# ============================================================
# ITEM DETAILS PAGE
# ============================================================

@app.route(
    "/item/<int:item_id>"
)
def item_details(item_id):

    connection = get_db_connection()


    item = connection.execute(
        """
        SELECT
            id,
            item_name,
            description,
            category,
            location,
            status,
            image,
            created_at

        FROM lost_found_items

        WHERE id = ?
        """,
        (
            item_id,
        )
    ).fetchone()


    connection.close()


    if item is None:

        return (
            "Item not found",
            404
        )


    return render_template(
        "item_details.html"
    )


# ============================================================
# ITEM DETAILS API
# ============================================================

@app.route(
    "/api/item/<int:item_id>"
)
def api_item(item_id):

    connection = get_db_connection()


    item = connection.execute(
        """
        SELECT
            id,
            item_name,
            description,
            category,
            location,
            status,
            image,
            created_at

        FROM lost_found_items

        WHERE id = ?
        """,
        (
            item_id,
        )
    ).fetchone()


    connection.close()


    if item is None:

        return jsonify({

            "success": False,

            "message":
                "Item not found"

        }), 404


    return jsonify({

        "success": True,

        "item": {

            "id":
                item["id"],

            "item_name":
                item["item_name"],

            "description":
                item["description"] or "",

            "category":
                item["category"],

            "location":
                item["location"],

            "status":
                item["status"],

            "image":
                item["image"],

            "created_at":
                item["created_at"]

        }

    })


# ============================================================
# SERVE UPLOADED IMAGES
# ============================================================

@app.route(
    "/uploads/<folder>/<filename>"
)
def uploaded_file(
    folder,
    filename
):

    if folder == "lost":

        return send_from_directory(
            UPLOAD_FOLDER_LOST,
            filename
        )


    if folder == "found":

        return send_from_directory(
            UPLOAD_FOLDER_FOUND,
            filename
        )


    return (
        "Invalid folder",
        404
    )
# ============================================================
# REPORT LOST ITEM
# ============================================================

@app.route(
    "/report_lost",
    methods=["GET", "POST"]
)
def report_lost():

    if "user_id" not in session:

        flash(
            "Please login to report a lost item.",
            "error"
        )

        return redirect(
            url_for("login")
        )


    if request.method == "GET":

        return render_template(
            "report_lost.html"
        )


    # ========================================================
    # GET FORM DATA
    # ========================================================

    item_name = request.form.get(
        "item_name",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    category = request.form.get(
        "category",
        ""
    ).strip()

    location = request.form.get(
        "location",
        ""
    ).strip()

    other_location = request.form.get(
        "other_location",
        ""
    ).strip()

    date_lost = request.form.get(
        "date_lost",
        ""
    ).strip()


    # ========================================================
    # OPTIONAL IMAGE
    # ========================================================

    image = request.files.get(
        "image"
    )

    image_filename = None


    if image and image.filename:

        if not allowed_file(
            image.filename
        ):

            flash(
                "Invalid image format. Please upload JPG, JPEG, PNG, GIF or WEBP.",
                "error"
            )

            return redirect(
                url_for("report_lost")
            )


        # ----------------------------------------------------
        # Create unique filename
        # ----------------------------------------------------

        original_filename = secure_filename(
            image.filename
        )

        image_filename = (
            f"{session['user_id']}_"
            f"{os.urandom(8).hex()}_"
            f"{original_filename}"
        )


        image.save(
            os.path.join(
                UPLOAD_FOLDER_LOST,
                image_filename
            )
        )


    # ========================================================
    # REQUIRED FIELDS
    # ========================================================

    if (
        not item_name
        or not category
        or not location
        or not date_lost
    ):

        flash(
            "Please fill in all required fields.",
            "error"
        )

        return redirect(
            url_for("report_lost")
        )


    # ========================================================
    # OTHER LOCATION
    # ========================================================

    if location == "Other":

        if not other_location:

            flash(
                "Please enter the other location.",
                "error"
            )

            return redirect(
                url_for("report_lost")
            )


        location = other_location


    # ========================================================
    # INSERT LOST ITEM
    # ========================================================

    connection = get_db_connection()


    cursor = connection.execute(
        """
        INSERT INTO lost_found_items
        (
            item_name,
            description,
            category,
            location,
            status,
            image,
            reported_by
        )

        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item_name,
            description,
            category,
            location,
            "Lost",
            image_filename,
            session["user_id"]
        )
    )


    lost_item_id = cursor.lastrowid


    connection.commit()

    connection.close()


    # ========================================================
    # NEW GLOBAL LOST ITEM NOTIFICATION
    # ========================================================
    #
    # IMPORTANT:
    # This runs AFTER the lost item is successfully saved.
    #
    # Every registered user receives a notification.
    # ========================================================

    create_global_lost_notification(
        lost_item_id
    )


    # ========================================================
    # SUCCESS MESSAGE
    # ========================================================

    flash(
        "Lost item reported successfully! All users have been notified.",
        "success"
    )


    return redirect(
        url_for("home")
    )


# ============================================================
# REPORT FOUND ITEM
# ============================================================

@app.route(
    "/report_found",
    methods=["GET", "POST"]
)
def report_found():

    if "user_id" not in session:

        flash(
            "Please login to report a found item.",
            "error"
        )

        return redirect(
            url_for("login")
        )


    if request.method == "GET":

        return render_template(
            "report_found.html"
        )


    # ========================================================
    # GET FORM DATA
    # ========================================================

    item_name = request.form.get(
        "item_name",
        ""
    ).strip()

    category = request.form.get(
        "category",
        ""
    ).strip()

    location = request.form.get(
        "location",
        ""
    ).strip()

    other_location = request.form.get(
        "other_location",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()


    # ========================================================
    # REQUIRED FIELDS
    # ========================================================

    if (
        not item_name
        or not category
        or not location
    ):

        flash(
            "Please fill in all required fields.",
            "error"
        )

        return redirect(
            url_for("report_found")
        )


    # ========================================================
    # OTHER LOCATION
    # ========================================================

    if location == "Other":

        if not other_location:

            flash(
                "Please enter the other location.",
                "error"
            )

            return redirect(
                url_for("report_found")
            )


        location = other_location


    # ========================================================
    # REQUIRED IMAGE
    # ========================================================

    image = request.files.get(
        "image"
    )


    if not image or not image.filename:

        flash(
            "Please upload an image of the found item.",
            "error"
        )

        return redirect(
            url_for("report_found")
        )


    if not allowed_file(
        image.filename
    ):

        flash(
            "Invalid image format. Please upload JPG, JPEG, PNG, GIF or WEBP.",
            "error"
        )

        return redirect(
            url_for("report_found")
        )


    # ========================================================
    # CREATE UNIQUE IMAGE FILENAME
    # ========================================================

    original_filename = secure_filename(
        image.filename
    )

    image_filename = (
        f"{session['user_id']}_"
        f"{os.urandom(8).hex()}_"
        f"{original_filename}"
    )


    image.save(
        os.path.join(
            UPLOAD_FOLDER_FOUND,
            image_filename
        )
    )


    # ========================================================
    # INSERT FOUND ITEM
    # ========================================================

    connection = get_db_connection()


    cursor = connection.execute(
        """
        INSERT INTO lost_found_items
        (
            item_name,
            description,
            category,
            location,
            status,
            image,
            reported_by
        )

        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item_name,
            description,
            category,
            location,
            "Found",
            image_filename,
            session["user_id"]
        )
    )


    found_item_id = cursor.lastrowid


    connection.commit()

    connection.close()


    # ========================================================
    # CREATE MATCH NOTIFICATIONS
    # ========================================================

    create_match_notifications(
        found_item_id
    )


    flash(
        "Found item reported successfully!",
        "success"
    )


    return redirect(
        url_for("home")
    )


# ============================================================
# NOTIFICATIONS API
# ============================================================

@app.route(
    "/api/notifications"
)
def api_notifications():

    if "user_id" not in session:

        return jsonify({

            "success": False,

            "message":
                "Login required."

        }), 401


    connection = get_db_connection()


    # ========================================================
    # NORMAL LOST / FOUND NOTIFICATIONS
    # ========================================================

    normal_notifications = connection.execute(
        """
        SELECT
            id,
            message,
            lost_item_id,
            found_item_id,
            is_read,
            created_at

        FROM notifications

        WHERE user_id = ?

        ORDER BY created_at DESC
        """,
        (
            session["user_id"],
        )
    ).fetchall()


    # ========================================================
    # CLAIM NOTIFICATIONS
    # ========================================================

    claim_notifications = connection.execute(
        """
        SELECT
            claim_notifications.id,
            claim_notifications.claim_id,
            claims.item_id,
            claim_notifications.message,
            claim_notifications.is_read,
            claim_notifications.created_at

        FROM claim_notifications

        LEFT JOIN claims
            ON claim_notifications.claim_id = claims.id

        WHERE claim_notifications.user_id = ?

        ORDER BY claim_notifications.created_at DESC
        """,
        (
            session["user_id"],
        )
    ).fetchall()


    # ========================================================
    # UNREAD COUNTS
    # ========================================================

    normal_unread = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM notifications
        WHERE user_id = ?
        AND is_read = 0
        """,
        (
            session["user_id"],
        )
    ).fetchone()["count"]


    claim_unread = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM claim_notifications
        WHERE user_id = ?
        AND is_read = 0
        """,
        (
            session["user_id"],
        )
    ).fetchone()["count"]


    connection.close()


    # ========================================================
    # COMBINE BOTH NOTIFICATION TYPES
    # ========================================================

    results = []


    for notification in normal_notifications:

        results.append({
            "id": notification["id"],
            "notification_type": "normal",
            "claim_id": None,
            "message": notification["message"],
            "lost_item_id": notification["lost_item_id"],
            "found_item_id": notification["found_item_id"],
            "is_read": notification["is_read"],
            "created_at": notification["created_at"]
        })


    for notification in claim_notifications:

        results.append({
            "id": notification["id"],
            "notification_type": "claim",
            "claim_id": notification["claim_id"],
            "item_id": notification["item_id"],
            "message": notification["message"],
            "lost_item_id": None,
            "found_item_id": None,
            "is_read": notification["is_read"],
            "created_at": notification["created_at"]
        })


    # ========================================================
    # NEWEST FIRST
    # ========================================================

    results.sort(
        key=lambda item: item["created_at"] or "",
        reverse=True
    )


    return jsonify({
        "success": True,
        "unread_count": normal_unread + claim_unread,
        "notifications": results
    })


# ============================================================
# MARK NOTIFICATION AS READ
# ============================================================

@app.route(
    "/api/notifications/<int:notification_id>/read",
    methods=["POST"]
)
def mark_notification_read(notification_id):

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Login required."
        }), 401


    data = request.get_json(silent=True) or {}

    notification_type = data.get(
        "notification_type",
        "normal"
    )


    connection = get_db_connection()


    if notification_type == "normal":

        connection.execute(
            """
            UPDATE notifications
            SET is_read = 1
            WHERE id = ?
            AND user_id = ?
            """,
            (
                notification_id,
                session["user_id"]
            )
        )


    elif notification_type == "claim":

        connection.execute(
            """
            UPDATE claim_notifications
            SET is_read = 1
            WHERE id = ?
            AND user_id = ?
            """,
            (
                notification_id,
                session["user_id"]
            )
        )


    else:

        connection.close()

        return jsonify({
            "success": False,
            "message": "Invalid notification type."
        }), 400


    connection.commit()
    connection.close()


    return jsonify({
        "success": True
    })


# ============================================================
# CLAIM ITEM PAGE
# ============================================================

@app.route(
    "/claim/<int:item_id>"
)
def claim_item(item_id):

    if "user_id" not in session:

        flash(
            "Please login to claim an item.",
            "error"
        )

        return redirect(
            url_for("login")
        )


    connection = get_db_connection()


    item = connection.execute(
        """
        SELECT
            id,
            item_name,
            category,
            location,
            status,
            image

        FROM lost_found_items

        WHERE id = ?
        """,
        (
            item_id,
        )
    ).fetchone()


    connection.close()


    if item is None:

        return (
            "Item not found",
            404
        )


    if item["status"] != "Found":

        return (
            "Only found items can be claimed.",
            400
        )


    return render_template(
        "claim_item.html"
    )


# ============================================================
# SUBMIT CLAIM API
# ============================================================

@app.route(
    "/api/claim",
    methods=["POST"]
)
def api_claim():

    if "user_id" not in session:

        return jsonify({

            "success": False,

            "message":
                "Please login first."

        }), 401


    data = request.form


    item_id = data.get(
        "item_id",
        ""
    ).strip()

    claimant_name = data.get(
        "claimant_name",
        ""
    ).strip()

    claimant_email = data.get(
        "claimant_email",
        ""
    ).strip()

    proof = data.get(
        "proof",
        ""
    ).strip()

    reason = data.get(
        "reason",
        ""
    ).strip()


    if (
        not item_id
        or not claimant_name
        or not claimant_email
        or not proof
        or not reason
    ):

        return jsonify({

            "success": False,

            "message":
                "Please fill in all required fields."

        }), 400


    connection = get_db_connection()


    item = connection.execute(
        """
        SELECT
            id,
            item_name,
            status,
            reported_by

        FROM lost_found_items

        WHERE id = ?
        """,
        (
            item_id,
        )
    ).fetchone()


    if item is None:

        connection.close()

        return jsonify({

            "success": False,

            "message":
                "Item not found."

        }), 404


    if item["status"] != "Found":

        connection.close()

        return jsonify({

            "success": False,

            "message":
                "Only found items can be claimed."

        }), 400


    if (
        item["reported_by"]
        ==
        session["user_id"]
    ):

        connection.close()

        return jsonify({

            "success": False,

            "message":
                "You cannot claim an item that you reported."

        }), 400


    existing_claim = connection.execute(
        """
        SELECT id

        FROM claims

        WHERE item_id = ?

        AND claimant_id = ?

        AND status = 'Pending'
        """,
        (
            item_id,
            session["user_id"]
        )
    ).fetchone()


    if existing_claim:

        connection.close()

        return jsonify({

            "success": False,

            "message":
                "You already have a pending claim for this item."

        }), 400


    cursor = connection.execute(
        """
        INSERT INTO claims
        (
            item_id,
            claimant_id,
            claimant_name,
            claimant_email,
            proof,
            reason,
            status
        )

        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item_id,
            session["user_id"],
            claimant_name,
            claimant_email,
            proof,
            reason,
            "Pending"
        )
    )


    claim_id = cursor.lastrowid


    connection.commit()


    # ========================================================
    # NOTIFY ADMINS
    # ========================================================

    admin_users = connection.execute(
        """
        SELECT id
        FROM users
        WHERE role = 'admin'
        """
    ).fetchall()


    for admin in admin_users:

        connection.execute(
            """
            INSERT INTO claim_notifications
            (
                user_id,
                claim_id,
                message
            )

            VALUES (?, ?, ?)
            """,
            (
                admin["id"],
                claim_id,
                f"New claim submitted for '{item['item_name']}'."
            )
        )


    connection.commit()

    connection.close()


    return jsonify({

        "success": True,

        "message":
            "Claim submitted successfully."

    })
# ============================================================
# ADMIN DASHBOARD PAGE
# ============================================================

@app.route(
    "/admin"
)
@admin_required
def admin_dashboard():

    return render_template(
        "admin.html"
    )


# ============================================================
# ADMIN DASHBOARD API
# ============================================================

@app.route(
    "/api/admin/dashboard"
)
@admin_required
def api_admin_dashboard():

    connection = get_db_connection()


    # ========================================================
    # TOTAL REGISTERED USERS
    # ========================================================

    total_users = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM users
        """
    ).fetchone()["count"]


    # ========================================================
    # TOTAL STUDENTS
    # ========================================================

    total_students = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM users
        WHERE role = 'student'
        """
    ).fetchone()["count"]


    # ========================================================
    # TOTAL ADMINS
    # ========================================================

    total_admins = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM users
        WHERE role = 'admin'
        """
    ).fetchone()["count"]


    # ========================================================
    # LOST ITEMS
    # ========================================================

    total_lost = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM lost_found_items
        WHERE status = 'Lost'
        """
    ).fetchone()["count"]


    # ========================================================
    # FOUND ITEMS
    # ========================================================

    total_found = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM lost_found_items
        WHERE status = 'Found'
        """
    ).fetchone()["count"]


    # ========================================================
    # CLAIMED ITEMS
    # ========================================================

    total_claimed = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM lost_found_items
        WHERE status = 'Claimed'
        """
    ).fetchone()["count"]


    # ========================================================
    # TOTAL CLAIMS
    # ========================================================

    total_claims = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM claims
        """
    ).fetchone()["count"]


    # ========================================================
    # PENDING CLAIMS
    # ========================================================

    pending_claims = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM claims
        WHERE status = 'Pending'
        """
    ).fetchone()["count"]


    # ========================================================
    # APPROVED CLAIMS
    # ========================================================

    approved_claims = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM claims
        WHERE status = 'Approved'
        """
    ).fetchone()["count"]


    # ========================================================
    # REJECTED CLAIMS
    # ========================================================

    rejected_claims = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM claims
        WHERE status = 'Rejected'
        """
    ).fetchone()["count"]


    # ========================================================
    # RECENT USERS
    # ========================================================

    recent_users = connection.execute(
        """
        SELECT
            id,
            name,
            email,
            role,
            created_at

        FROM users

        ORDER BY created_at DESC

        LIMIT 20
        """
    ).fetchall()


    user_list = []


    for user in recent_users:

        user_list.append({

            "id":
                user["id"],

            "name":
                user["name"],

            "email":
                user["email"],

            "role":
                user["role"],

            "created_at":
                user["created_at"]

        })


    # ========================================================
    # RECENT ITEMS
    # ========================================================

    recent_items = connection.execute(
        """
        SELECT

            lost_found_items.id,

            lost_found_items.item_name,

            lost_found_items.category,

            lost_found_items.location,

            lost_found_items.status,

            lost_found_items.created_at,

            users.name AS reporter_name

        FROM lost_found_items

        LEFT JOIN users

        ON lost_found_items.reported_by =
           users.id

        ORDER BY
            lost_found_items.created_at DESC

        LIMIT 10
        """
    ).fetchall()


    item_list = []


    for item in recent_items:

        item_list.append({

            "id":
                item["id"],

            "item_name":
                item["item_name"],

            "category":
                item["category"],

            "location":
                item["location"],

            "status":
                item["status"],

            "reporter_name":
                item["reporter_name"]
                or "Unknown",

            "created_at":
                item["created_at"]

        })


    connection.close()


    # ========================================================
    # RETURN DASHBOARD DATA
    # ========================================================

    return jsonify({

        "success": True,

        "stats": {

            "total_users":
                total_users,

            "total_students":
                total_students,

            "total_admins":
                total_admins,

            "total_lost":
                total_lost,

            "total_found":
                total_found,

            "total_claimed":
                total_claimed,

            "total_claims":
                total_claims,

            "pending_claims":
                pending_claims,

            "approved_claims":
                approved_claims,

            "rejected_claims":
                rejected_claims

        },

        "users":
            user_list,

        "recent_items":
            item_list

    })


# ============================================================
# ADMIN CLAIMS API
# ============================================================

@app.route(
    "/api/admin/claims"
)
@admin_required
def api_admin_claims():

    connection = get_db_connection()


    claims = connection.execute(
        """
        SELECT

            claims.id AS claim_id,

            claims.item_id,

            claims.claimant_id,

            claims.claimant_name,

            claims.claimant_email,

            claims.proof,

            claims.reason,

            claims.status AS claim_status,

            claims.created_at AS claim_created_at,

            lost_found_items.item_name,

            lost_found_items.category,

            lost_found_items.location,

            lost_found_items.status AS item_status,

            lost_found_items.image,

            lost_found_items.reported_by

        FROM claims

        INNER JOIN lost_found_items
        ON claims.item_id = lost_found_items.id

        ORDER BY

            CASE

                WHEN claims.status = 'Pending'
                THEN 0

                WHEN claims.status = 'Approved'
                THEN 1

                ELSE 2

            END,

            claims.created_at DESC
        """
    ).fetchall()


    # ========================================================
    # CLAIM COUNTS
    # ========================================================

    pending_count = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM claims
        WHERE status = 'Pending'
        """
    ).fetchone()["count"]


    approved_count = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM claims
        WHERE status = 'Approved'
        """
    ).fetchone()["count"]


    rejected_count = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM claims
        WHERE status = 'Rejected'
        """
    ).fetchone()["count"]


    total_count = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM claims
        """
    ).fetchone()["count"]


    connection.close()


    results = []


    for claim in claims:

        results.append({

            "claim_id":
                claim["claim_id"],

            "item_id":
                claim["item_id"],

            "claimant_id":
                claim["claimant_id"],

            "claimant_name":
                claim["claimant_name"],

            "claimant_email":
                claim["claimant_email"],

            "proof":
                claim["proof"],

            "reason":
                claim["reason"],

            "claim_status":
                claim["claim_status"],

            "claim_created_at":
                claim["claim_created_at"],

            "item_name":
                claim["item_name"],

            "category":
                claim["category"],

            "location":
                claim["location"],

            "item_status":
                claim["item_status"],

            "image":
                claim["image"],

            "reported_by":
                claim["reported_by"]

        })


    return jsonify({

        "success": True,

        "counts": {

            "pending":
                pending_count,

            "approved":
                approved_count,

            "rejected":
                rejected_count,

            "total":
                total_count

        },

        "claims":
            results

    })


# ============================================================
# ADMIN APPROVE CLAIM
# ============================================================

@app.route(
    "/api/admin/claim/<int:claim_id>/approve",
    methods=["POST"]
)
@admin_required
def approve_claim(claim_id):

    connection = get_db_connection()


    claim = connection.execute(
        """
        SELECT

            claims.id,

            claims.item_id,

            claims.claimant_id,

            claims.claimant_name,

            claims.claimant_email,

            claims.status,

            lost_found_items.item_name,

            lost_found_items.status AS item_status

        FROM claims

        INNER JOIN lost_found_items
        ON claims.item_id = lost_found_items.id

        WHERE claims.id = ?
        """,
        (
            claim_id,
        )
    ).fetchone()


    if claim is None:

        connection.close()

        return jsonify({

            "success": False,

            "message":
                "Claim not found."

        }), 404


    if claim["status"] != "Pending":

        connection.close()

        return jsonify({

            "success": False,

            "message":
                "This claim has already been processed."

        }), 400


    if claim["item_status"] != "Found":

        connection.close()

        return jsonify({

            "success": False,

            "message":
                "This item is no longer available for claiming."

        }), 400


    # ========================================================
    # OTHER PENDING CLAIMS
    # ========================================================

    other_pending_claims = connection.execute(
        """
        SELECT
            id,
            claimant_id

        FROM claims

        WHERE item_id = ?

        AND id != ?

        AND status = 'Pending'
        """,
        (
            claim["item_id"],
            claim_id
        )
    ).fetchall()


    # ========================================================
    # APPROVE CLAIM
    # ========================================================

    # ========================================================
    # GENERATE UNIQUE QR TOKEN
    # ========================================================

    qr_token = secrets.token_urlsafe(32)

    connection.execute(
        """
        UPDATE claims

        SET
            status = 'Approved',
            qr_token = ?,
            handover_status = 'Pending',
            verified_at = NULL,
            verified_by = NULL

        WHERE id = ?
        """,
        (
            qr_token,
            claim_id,
        )
    )


    # ========================================================
    # MARK ITEM AS CLAIMED
    # ========================================================

    connection.execute(
        """
        UPDATE lost_found_items

        SET status = 'Claimed'

        WHERE id = ?
        """,
        (
            claim["item_id"],
        )
    )


    # ========================================================
    # REJECT OTHER PENDING CLAIMS
    # ========================================================

    connection.execute(
        """
        UPDATE claims

        SET status = 'Rejected'

        WHERE item_id = ?

        AND id != ?

        AND status = 'Pending'
        """,
        (
            claim["item_id"],
            claim_id
        )
    )


    # ========================================================
    # NOTIFY APPROVED CLAIMANT
    # ========================================================

    approval_message = (
        f"Your claim for '{claim['item_name']}' "
        f"has been approved by the admin. "
        f"Your QR code is now ready for handover verification."
    )


    connection.execute(
        """
        INSERT INTO claim_notifications
        (
            user_id,
            claim_id,
            message
        )

        VALUES (?, ?, ?)
        """,
        (
            claim["claimant_id"],
            claim_id,
            approval_message
        )
    )


    # ========================================================
    # NOTIFY REJECTED CLAIMANTS
    # ========================================================

    for rejected_claim in other_pending_claims:

        rejection_message = (
            f"Your claim for '{claim['item_name']}' "
            f"was not approved because another claim "
            f"was approved for this item."
        )


        connection.execute(
            """
            INSERT INTO claim_notifications
            (
                user_id,
                claim_id,
                message
            )

            VALUES (?, ?, ?)
            """,
            (
                rejected_claim["claimant_id"],
                rejected_claim["id"],
                rejection_message
            )
        )


    connection.commit()

    connection.close()


    return jsonify({

        "success": True,

        "message":
            "Claim approved successfully."

    })


# ============================================================
# ADMIN REJECT CLAIM
# ============================================================

@app.route(
    "/api/admin/claim/<int:claim_id>/reject",
    methods=["POST"]
)
@admin_required
def reject_claim(claim_id):

    connection = get_db_connection()


    claim = connection.execute(
        """
        SELECT

            claims.id,

            claims.item_id,

            claims.claimant_id,

            claims.status,

            lost_found_items.item_name,

            lost_found_items.status AS item_status

        FROM claims

        INNER JOIN lost_found_items
        ON claims.item_id = lost_found_items.id

        WHERE claims.id = ?
        """,
        (
            claim_id,
        )
    ).fetchone()


    if claim is None:

        connection.close()

        return jsonify({

            "success": False,

            "message":
                "Claim not found."

        }), 404


    if claim["status"] != "Pending":

        connection.close()

        return jsonify({

            "success": False,

            "message":
                "This claim has already been processed."

        }), 400


    # ========================================================
    # REJECT CLAIM
    # ========================================================

    connection.execute(
        """
        UPDATE claims

        SET status = 'Rejected'

        WHERE id = ?
        """,
        (
            claim_id,
        )
    )


    # ========================================================
    # NOTIFY CLAIMANT
    # ========================================================

    rejection_message = (
        f"Your claim for '{claim['item_name']}' "
        f"has been rejected by the admin."
    )


    connection.execute(
        """
        INSERT INTO claim_notifications
        (
            user_id,
            claim_id,
            message
        )

        VALUES (?, ?, ?)
        """,
        (
            claim["claimant_id"],
            claim_id,
            rejection_message
        )
    )


    connection.commit()

    connection.close()


    return jsonify({

        "success": True,

        "message":
            "Claim rejected successfully."

    })
# ============================================================
# MY CLAIMS / QR CODE API
# ============================================================

@app.route(
    "/api/my-claims"
)
def api_my_claims():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    connection = get_db_connection()

    claims = connection.execute(
        """
        SELECT
            claims.id AS claim_id,
            claims.item_id,
            claims.status AS claim_status,
            claims.handover_status,
            claims.verified_at,
            claims.created_at,
            lost_found_items.item_name,
            lost_found_items.category,
            lost_found_items.location,
            lost_found_items.image

        FROM claims

        INNER JOIN lost_found_items
            ON claims.item_id = lost_found_items.id

        WHERE claims.claimant_id = ?

        ORDER BY claims.created_at DESC
        """,
        (session["user_id"],)
    ).fetchall()

    connection.close()

    results = []

    for claim in claims:

        qr_url = None

        if (
            claim["claim_status"] == "Approved"
            and claim["handover_status"] != "Handed Over"
        ):
            qr_url = url_for(
                "claim_qr_code",
                claim_id=claim["claim_id"]
            )

        results.append({
            "claim_id": claim["claim_id"],
            "item_id": claim["item_id"],
            "item_name": claim["item_name"],
            "category": claim["category"],
            "location": claim["location"],
            "image": claim["image"],
            "claim_status": claim["claim_status"],
            "handover_status": claim["handover_status"],
            "verified_at": claim["verified_at"],
            "created_at": claim["created_at"],
            "qr_url": qr_url
        })

    return jsonify({
        "success": True,
        "claims": results
    })


# ============================================================
# CLAIM QR CODE IMAGE
# ============================================================

@app.route(
    "/api/claim/<int:claim_id>/qr"
)
def claim_qr_code(claim_id):

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    connection = get_db_connection()

    claim = connection.execute(
        """
        SELECT
            id,
            claimant_id,
            status,
            handover_status,
            qr_token

        FROM claims

        WHERE id = ?
        """,
        (claim_id,)
    ).fetchone()

    if claim is None:
        connection.close()
        return jsonify({
            "success": False,
            "message": "Claim not found."
        }), 404

    is_owner = claim["claimant_id"] == session["user_id"]
    is_admin = session.get("user_role") == "admin"

    if not is_owner and not is_admin:
        connection.close()
        return jsonify({
            "success": False,
            "message": "Access denied."
        }), 403

    if claim["status"] != "Approved":
        connection.close()
        return jsonify({
            "success": False,
            "message": "QR code is available only for approved claims."
        }), 400

    if claim["handover_status"] == "Handed Over":
        connection.close()
        return jsonify({
            "success": False,
            "message": "This QR code has already been used."
        }), 400

    qr_token = claim["qr_token"]

    connection.close()

    if not qr_token:
        return jsonify({
            "success": False,
            "message": "QR code is not available for this claim."
        }), 400

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4
    )

    verification_url = url_for(
        "qr_handover_verification",
        qr_token=qr_token,
        _external=True
    )

    qr.add_data(verification_url)
    qr.make(fit=True)

    image = qr.make_image()

    image_buffer = io.BytesIO()
    image.save(image_buffer, format="PNG")
    image_buffer.seek(0)

    return send_from_directory(
        os.path.dirname(image_buffer.name) if image_buffer.name else ".",
        os.path.basename(image_buffer.name) if image_buffer.name else "",
    ) if False else app.response_class(
        image_buffer.getvalue(),
        mimetype="image/png"
    )


# ============================================================
# QR HANDOVER VERIFICATION PAGE
# ============================================================

@app.route("/verify-handover/<qr_token>")
@admin_required
def qr_handover_verification(qr_token):

    connection = get_db_connection()

    claim = connection.execute(
        """
        SELECT
            claims.id,
            claims.claimant_id,
            claims.status,
            claims.handover_status,
            lost_found_items.item_name,
            lost_found_items.category,
            lost_found_items.location,
            users.name AS claimant_name

        FROM claims

        INNER JOIN lost_found_items
            ON claims.item_id = lost_found_items.id

        INNER JOIN users
            ON claims.claimant_id = users.id

        WHERE claims.qr_token = ?
        """,
        (qr_token,)
    ).fetchone()

    connection.close()

    if claim is None:
        return render_template(
            "qr_verify.html",
            valid=False
        )

    return render_template(
        "qr_verify.html",
        valid=True,
        claim_id=claim["id"],
        claimant_name=claim["claimant_name"],
        item_name=claim["item_name"],
        category=claim["category"],
        location=claim["location"],
        claim_status=claim["status"],
        handover_status=claim["handover_status"],
        qr_token=qr_token
    )


# ============================================================
# ADMIN VERIFY HANDOVER
# ============================================================

@app.route(
    "/api/admin/claim/<int:claim_id>/verify-handover",
    methods=["POST"]
)
@admin_required
def verify_claim_handover(claim_id):

    data = request.get_json(silent=True) or request.form

    qr_token = data.get(
        "qr_token",
        ""
    ).strip()

    if not qr_token:
        return jsonify({
            "success": False,
            "message": "Please provide the QR verification code."
        }), 400

    connection = get_db_connection()

    claim = connection.execute(
        """
        SELECT
            claims.id,
            claims.item_id,
            claims.claimant_id,
            claims.status,
            claims.handover_status,
            claims.qr_token,
            lost_found_items.item_name,
            lost_found_items.status AS item_status

        FROM claims

        INNER JOIN lost_found_items
            ON claims.item_id = lost_found_items.id

        WHERE claims.id = ?
        """,
        (claim_id,)
    ).fetchone()

    if claim is None:
        connection.close()
        return jsonify({
            "success": False,
            "message": "Claim not found."
        }), 404

    if claim["status"] != "Approved":
        connection.close()
        return jsonify({
            "success": False,
            "message": "Only approved claims can be verified."
        }), 400

    if claim["handover_status"] == "Handed Over":
        connection.close()
        return jsonify({
            "success": False,
            "message": "This QR code has already been used."
        }), 400

    if not claim["qr_token"] or not secrets.compare_digest(
        claim["qr_token"],
        qr_token
    ):
        connection.close()
        return jsonify({
            "success": False,
            "message": "Invalid QR verification code."
        }), 400

    connection.execute(
        """
        UPDATE claims

        SET
            handover_status = 'Handed Over',
            verified_at = CURRENT_TIMESTAMP,
            verified_by = ?

        WHERE id = ?
        """,
        (
            session["user_id"],
            claim_id
        )
    )

    connection.execute(
        """
        INSERT INTO claim_notifications
        (
            user_id,
            claim_id,
            message
        )

        VALUES (?, ?, ?)
        """,
        (
            claim["claimant_id"],
            claim_id,
            f"Handover completed for '{claim['item_name']}'. "
            f"Your claim has been successfully verified by the admin."
        )
    )

    connection.commit()
    connection.close()

    return jsonify({
        "success": True,
        "message": "Handover verified successfully. The QR code cannot be reused.",
        "claim_id": claim_id,
        "handover_status": "Handed Over"
    })


# ============================================================
# CLAIM NOTIFICATIONS API
# ============================================================

@app.route(
    "/api/claim-notifications"
)
def api_claim_notifications():

    if "user_id" not in session:

        return jsonify({

            "success": False,

            "message":
                "Login required."

        }), 401


    connection = get_db_connection()


    notifications = connection.execute(
        """
        SELECT

            claim_notifications.id,

            claim_notifications.claim_id,

            claim_notifications.message,

            claim_notifications.is_read,

            claim_notifications.created_at

        FROM claim_notifications

        WHERE claim_notifications.user_id = ?

        ORDER BY
            claim_notifications.created_at DESC
        """,
        (
            session["user_id"],
        )
    ).fetchall()


    unread_count = connection.execute(
        """
        SELECT COUNT(*) AS count

        FROM claim_notifications

        WHERE user_id = ?

        AND is_read = 0
        """,
        (
            session["user_id"],
        )
    ).fetchone()["count"]


    connection.close()


    results = []


    for notification in notifications:

        results.append({

            "id":
                notification["id"],

            "claim_id":
                notification["claim_id"],

            "message":
                notification["message"],

            "is_read":
                notification["is_read"],

            "created_at":
                notification["created_at"]

        })


    return jsonify({

        "success": True,

        "unread_count":
            unread_count,

        "notifications":
            results

    })


# ============================================================
# MARK CLAIM NOTIFICATION AS READ
# ============================================================

@app.route(
    "/api/claim-notifications/<int:notification_id>/read",
    methods=["POST"]
)
def mark_claim_notification_read(
    notification_id
):

    if "user_id" not in session:

        return jsonify({

            "success": False,

            "message":
                "Login required."

        }), 401


    connection = get_db_connection()


    connection.execute(
        """
        UPDATE claim_notifications

        SET is_read = 1

        WHERE id = ?

        AND user_id = ?
        """,
        (
            notification_id,
            session["user_id"]
        )
    )


    connection.commit()

    connection.close()


    return jsonify({

        "success": True

    })


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )


        # ====================================================
        # VALIDATE LOGIN FORM
        # ====================================================

        if not email or not password:

            flash(
                "Please enter your email and password.",
                "error"
            )

            return redirect(
                url_for("login")
            )


        connection = get_db_connection()


        user = connection.execute(
            """
            SELECT *
            FROM users

            WHERE email = ?
            """,
            (
                email,
            )
        ).fetchone()


        connection.close()


        # ====================================================
        # CHECK PASSWORD
        # ====================================================

        if (
            user
            and
            check_password_hash(
                user["password"],
                password
            )
        ):

            # ------------------------------------------------
            # SAVE SESSION
            # ------------------------------------------------

            session["user_id"] = user["id"]

            session["user_name"] = user["name"]

            session["user_email"] = user["email"]

            session["user_role"] = (
                user["role"]
                if user["role"]
                else "student"
            )


            flash(
                f"Welcome back, {user['name']}!",
                "success"
            )


            # =================================================
            # ADMIN REDIRECT
            # =================================================

            if session["user_role"] == "admin":

                return redirect(
                    url_for("admin_dashboard")
                )


            # =================================================
            # STUDENT REDIRECT
            # =================================================

            return redirect(
                url_for("home")
            )


        # ====================================================
        # INVALID LOGIN
        # ====================================================

        flash(
            "Invalid email or password.",
            "error"
        )


        return redirect(
            url_for("login")
        )


    return render_template(
        "login.html"
    )


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm-password",
            ""
        )


        # ====================================================
        # REQUIRED FIELDS
        # ====================================================

        if (
            not name
            or not email
            or not password
            or not confirm_password
        ):

            flash(
                "Please fill in all fields.",
                "error"
            )

            return redirect(
                url_for("register")
            )


        # ====================================================
        # PASSWORD MATCH
        # ====================================================

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return redirect(
                url_for("register")
            )


        connection = get_db_connection()


        # ====================================================
        # CHECK EXISTING USER
        # ====================================================

        existing_user = connection.execute(
            """
            SELECT id

            FROM users

            WHERE email = ?
            """,
            (
                email,
            )
        ).fetchone()


        if existing_user:

            connection.close()

            flash(
                "An account with this email already exists.",
                "error"
            )

            return redirect(
                url_for("register")
            )


        # ====================================================
        # HASH PASSWORD
        # ====================================================

        hashed_password = generate_password_hash(
            password
        )


        # ====================================================
        # NEW USERS ARE STUDENTS
        # ====================================================

        connection.execute(
            """
            INSERT INTO users
            (
                name,
                email,
                password,
                role
            )

            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                email,
                hashed_password,
                "student"
            )
        )


        connection.commit()

        connection.close()


        flash(
            "Registration successful! Please login.",
            "success"
        )


        return redirect(
            url_for("login")
        )


    return render_template(
        "register.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route(
    "/logout"
)
def logout():

    session.clear()


    flash(
        "You have been logged out successfully.",
        "success"
    )


    return redirect(
        url_for("home")
    )


# ============================================================
# INITIALIZE DATABASE
# ============================================================

init_database()


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )