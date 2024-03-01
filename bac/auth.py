import functools
from flask import (
    Blueprint,g,redirect,render_template,request,session,url_for
)
from werkzeug.security import check_password_hash,generate_password_hash
from bac.db import get_db

bp = Blueprint('auth',__name__,url_prefix='/auth')

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?',(user_id,)
        ).fetchone()

@bp.route('/register',methods=('GET','POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        error = None
        if not username:
            error = 'Username is required'
        elif not password:
            error = 'Password is required'

        profile = username=="admin"
        if error is None:
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO user (username,password,profile) VALUES (?,?,?)",
                    (username, generate_password_hash(password),profile),
                )
                db.commit()
            except db.IntegrityError:
                error = f"User {username} is already registered"
            else:
                return redirect(url_for('auth.login'),code=307)
        if error:
            print(error)
            #flash(error)
    return render_template('auth/register.html')

@bp.route('/login',methods=('POST',))
def login():
    username = request.form['username']
    password = request.form['password']

    db = get_db()    
    user = db.execute(
        "SELECT * FROM user WHERE username = ?",(username,)        
    ).fetchone()

    error = None
    if user is None:
        #TODO should be removed when the register page is created
        return redirect(url_for('auth.register'),code=307)
        error = 'Incorrect username'
    elif not check_password_hash(user['password'],password):
        error = 'Incorrect password'
    
    if error is None:
        session.clear()
        session['user_id'] = user['id']
    else:
        print(error)
        #flash(error)
    return redirect(url_for('index'))
    
@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view

def su_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None or g.user['profile'] != 1:
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view
