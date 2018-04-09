from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
#from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'laser123'
app.config['MYSQL_DB'] = 'hotel_mgmt'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init MYSQL
mysql = MySQL(app)

#Articles = Articles()

# Index
@app.route('/')
def index():
    return render_template('home.html')

@app.route('/about')
def about():
	return render_template('about.html')

@app.route('/amenities')
def amenities():

    cur=mysql.connection.cursor()

    result=cur.execute("SELECT * FROM amenities")

    amenities = cur.fetchall()

    if result > 0:
        return render_template('amenities.html', amenities=amenities)
    else:
        msg = 'No facilites available currently'
        return render_template('amenities.html', msg=msg)

    cur.close()

@app.route('/view_amenity/<string:id>/')
def view_amenity(id):
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM amenities WHERE a_id = %s", [id])

    amenity = cur.fetchone()

    return render_template('view_amenity.html', amenity=amenity)

# Register Form Class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.Length(min=6, max=150),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')


# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # Create cursor
        cur = mysql.connection.cursor()

        cur.execute("SELECT * FROM admins")

        rows=cur.fetchall()
        #print(rows[0])

        # Execute query
        cur.execute("INSERT INTO admins(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('You are now registered and can log in', 'success')

        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute("SELECT * FROM admins WHERE username = %s", [username])


        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            print(data['username'])
            password = data['password']

            # Compare Passwords
            if sha256_crypt.verify(request.form['password'], password):
                print("matched and redirecting....")
                # Passed
                #app.logger.info('PASSWORD MATCHED')
                session['logged_in'] = True
                session['username']  = username

                flash('Successfully logged in!', 'success')

                return redirect(url_for('dashboard'))

            else:
                print("wrong password")
                error = 'Invalid login'
                app.logger.info('PASSWORD DOES NOT MATCH')
                return render_template('login.html', error=error)

            cur.close()
            
        else:
            error = 'Username not found'
            app.logger.info('NO SUCH USER')
            return render_template('login.html', error=error)

    return render_template('login.html')

def is_logged_in(f):
    @wraps(f)

    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return (f(*args, **kwargs))
        else:
            flash('Unauthorised access!', 'danger')
            return redirect(url_for('login'))
    return wrap


@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@is_logged_in
def dashboard():
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM amenities")

    amenities = cur.fetchall()

    if result > 0:
        return render_template('dashboard.html', amenities=amenities)
    else:
        masg = 'No Facilities available'
        return render_template('dashboard.html', msg=msg)

    cur.close()
    return render_template('dashboard.html')

class AmenityForm(Form):
    id = StringField('ID', [validators.Length(min=3, max=5)])
    type = StringField('Type', [validators.Length(min=1, max=1)])
    status = StringField('Status', [validators.Length(min=1, max=1)])
    capacity = StringField('Capacity', [validators.Length(min=3, max=5)])
    title = StringField('Title', [validators.Length(min=2, max=200)])
    description = TextAreaField('Description', [validators.Length(min=30)])


@app.route('/add_amenity', methods=['GET', 'POST'])
@is_logged_in
def add_amenity():
    form = AmenityForm(request.form)

    if request.method == 'POST' and form.validate():
        id = form.id.data
        type = form.type.data
        status = form.status.data
        capacity = form.capacity.data
        title = form.title.data
        description = form.description.data

        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO amenities(a_id, a_type, a_status, a_capacity, a_title, a_description) VALUES(%s, %s, %s, %s, %s, %s)", (id, type, status, capacity, title, description))

        mysql.connection.commit()

        cur.close()

        flash('Facility Added Successfully', 'success')

        return redirect(url_for('dashboard'))

    return render_template('add_amenity.html', form=form)

@app.route('/edit_amenity/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_amenity(id):
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM amenities WHERE a_id=%s", [id])

    article = cur.fetchone()

    form = AmenityForm(request.form)

    form.type.data = article['a_type']
    form.status.data = article['a_status']
    form.capacity.data = article['a_capacity']
    form.title.data = article['a_title']
    form.description.data  = article['a_description']

    if request.method == 'POST' and form.validate():
        type = request.form['type']
        status = request.form['status']
        capacity = request.form['capacity']
        title = request.form['title']
        description  = request.form['description']

        cur = mysql.connection.cursor()

        cur.execute("UPDATE amenities SET a_type=%s, a_status=%s, a_capacity=%s, a_title=%s, a_description=%s WHERE a_id=%s", (type, status, capacity, title, description, id))

        mysql.connection.commit()

        cur.close()

        flash('Facility Updated successfully', 'success')

        return redirect(url_for('dashboard'))

    return render_template('edit_amenity.html', form=form)

@app.route('/delete_amenity/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def delete_amenity(id):
    cur=mysql.connection.cursor()

    cur.execute("DELETE FROM amenities WHERE a_id=%s", [id])

    mysql.connection.commit()

    cur.close()

    flash('Facility Deleted', 'success')

    return redirect(url_for('dashboard'))

@app.route('/bookings', methods=['GET', 'POST'])
def bookings():
    return render_template('bookings.html')

if __name__ == '__main__':
	app.secret_key = 'xyzapp123'
	app.run()