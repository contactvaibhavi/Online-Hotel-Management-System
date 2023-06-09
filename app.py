from flask import Flask, render_template, make_response, flash, redirect, url_for, session, request, logging
import random
from flask_mysqldb import MySQL
from flask_wtf import Form
from wtforms import DateField, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
import pdfkit
# from twilio.rest import Client
from datetime import date
import os
from os import environ

app = Flask(__name__)
app.secret_key = os.urandom(32)

# Config MySQL
app.config['MYSQL_HOST'] = environ.get('MYSQL_HOST')
app.config['MYSQL_USER'] = environ.get('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = environ.get('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = environ.get('MYSQL_DB')
app.config['MYSQL_CURSORCLASS'] = environ.get('MYSQL_CURSORCLASS')

# init MYSQL
mysql = MySQL(app)

# Index
@app.route('/')
def index():
    if session.get('secret_key'):
        print(session['secret_key'])
    else:
        session['secret_key'] = os.urandom(32)
    print("app.config['MYSQL_CURSORCLASS'] = "+ app.config['MYSQL_CURSORCLASS'])

    cur = mysql.connection.cursor()
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

@app.route('/rooms')
def rooms():
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM rooms")

    rooms = cur.fetchall()

    if result > 0:
        return render_template('rooms.html', rooms=rooms)
    else:
        msg = 'No rooms available currently'
        return render_template('rooms.html', msg=msg)

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
    # Call Parameterised Constructor to RegisterForm class 
    # with the data collected from FrontEnd Request
    form = RegisterForm(request.form)

    
    if request.method == 'POST' and form.validate():
        print(form.name.data)
        print(form.email.data)
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
    # If the Form is submitted
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        session['username'] = username

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

                # session['secret_key'] = SECRET_KEY

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
    return redirect('/')

@app.route('/dashboard')
@is_logged_in
def dashboard():
    return render_template('dashboard.html')

@app.route('/admin_amenities')
@is_logged_in
def admin_amenities():
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM amenities")

    amenities = cur.fetchall()

    if result > 0:
        return render_template('admin_amenities.html', amenities=amenities)
    else:
        msg = 'No Facilities available'
        return render_template('dashboard.html', msg=msg)

    cur.close()
    return render_template('admin_amenities.html')

class AmenityForm(Form):
    id = StringField('ID', [validators.Length(min=0, max=5)])
    type = StringField('Type', [validators.Length(min=0, max=1)])
    status = StringField('Status', [validators.Length(min=0, max=1)])
    capacity = StringField('Capacity', [validators.Length(min=0, max=5)])
    title = StringField('Title', [validators.Length(min=2, max=200)])
    description = TextAreaField('Description', [validators.Length(min=30)])


@app.route('/add_amenity', methods=['GET', 'POST'])
@is_logged_in
def add_amenity():
    form = AmenityForm()

    if form.validate_on_submit():
        print("YES")
        idd = form.id.data
        print(idd)
        type = form.type.data
        status = form.status.data
        capacity = form.capacity.data
        title = form.title.data
        description = form.description.data

        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO amenities(a_id, a_type, a_status, a_capacity, a_title, a_description) VALUES(%s, %s, %s, %s, %s, %s)", (idd, type, status, capacity, title, description))

        mysql.connection.commit()

        cur.close()

        flash('Facility Added Successfully', 'success')

        return redirect(url_for('add_amenity'))
    print(form.errors)
    return render_template('add_amenity.html', form=form)

@app.route('/edit_amenity/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_amenity(id):
    print("&&&&&FFGTHTRH")
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM amenities WHERE a_id=%s", [id])
    print(result)
    amenity = cur.fetchone()
    print(amenity)
    form = AmenityForm()
    print(form)

    form.type.data = str(amenity['a_type'])
    form.status.data = str(amenity['a_status'])
    form.capacity.data = str(amenity['a_capacity'])
    form.title.data = str(amenity['a_title'])
    form.description.data  = amenity['a_description']

    if form.validate_on_submit():
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

    print(form.errors)
    return render_template('edit_amenity.html', form=form)

@app.route('/delete_amenity/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def delete_amenity(id):
    cur=mysql.connection.cursor()

    cur.execute("DELETE FROM amenities WHERE a_id=%s", [id])

    mysql.connection.commit()

    cur.close()

    flash('Facility Deleted', 'success')

    return redirect(url_for('admin_amenities'))

@app.route('/admin_rooms')
@is_logged_in
def admin_rooms():
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM rooms")

    rooms = cur.fetchall()

    if result > 0:
        return render_template('admin_rooms.html', rooms=rooms)
    else:
        flash('No Rooms available!', 'danger')
        redirect(url_for('add_room'))

    cur.close()
    return render_template('admin_rooms.html')

class RoomForm(Form):
    id = StringField('ID', [validators.Length(min=3, max=5)])
    number = StringField('Room Number', [validators.Length(min=1, max=3)])
    type = StringField('Type', [validators.Length(min=1, max=1)])
    status = StringField('Status', [validators.Length(min=1, max=1)])
    capacity = StringField('Capacity', [validators.Length(min=1, max=2)])


@app.route('/add_room', methods=['GET', 'POST'])
@is_logged_in
def add_room():
    form = RoomForm(request.form)

    if request.method == 'POST' and form.validate():
        id = form.id.data
        number = form.number.data
        type = form.type.data
        status = form.status.data
        capacity = form.capacity.data

        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO rooms(r_id, r_number, r_type, r_capacity, r_status) VALUES(%s, %s, %s, %s, %s)", (id, number, type, capacity, status))

        mysql.connection.commit()

        cur.close()

        flash('Room Added Successfully!', 'success')

        return redirect(url_for('add_room'))

    return render_template('add_room.html', form=form)

@app.route('/edit_room/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_room(id):
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM rooms WHERE r_id=%s", [id])

    article = cur.fetchone()

    form = RoomForm()

    form.type.data = article['r_type']
    form.status.data = article['r_status']
    form.capacity.data = article['r_capacity']

    if request.method=='POST':#form.validate_on_submit():
        type = request.form['type']
        status = request.form['status']
        capacity = request.form['capacity']

        cur = mysql.connection.cursor()

        cur.execute("UPDATE rooms SET r_type=%s, r_status=%s, r_capacity=%s WHERE r_id=%s", (type, status, capacity, id))

        mysql.connection.commit()

        cur.close()

        flash('Room Updated successfully', 'success')

        return redirect(url_for('edit_room', id=id))

    return render_template('edit_room.html', form=form, id=id)

@app.route('/delete_room/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def delete_room(id):
    cur=mysql.connection.cursor()

    cur.execute("DELETE FROM rooms WHERE r_id=%s", [id])

    mysql.connection.commit()

    cur.close()

    flash('Room Deleted', 'success')

    return redirect(url_for('admin_rooms'))

class DateForm(Form):
    dt = DateField('Pick a Date', format="%m/%d/%Y")


@app.route('/date', methods=['post','get'])
def home():
    form = DateForm()
    if form.validate_on_submit():
        print(form.dt.data)
        return form.dt.data.strftime('%Y-%m-%d')
    return render_template('example.html', form=form)

class BookingForm(Form):
    g_id = StringField('Enter your unique Guest ID')
    check_in = DateField('Pick a Date', format="%m/%d/%Y")
    check_out = DateField('Pick a Date', format="%m/%d/%Y")
    status = StringField('Status')
    name = StringField('Name', [validators.Length(min=3, max=30)])
    count = StringField('No of adults', [validators.Length(min=1, max=1)])
    email = StringField('Email', [validators.Length(min=2, max=200)])
    streetno = TextAreaField('Street Address', [validators.Length(min=6)])
    city = StringField('City', [validators.Length(min=2, max=200)])
    state = StringField('State', [validators.Length(min=2, max=200)])    
    country = StringField('Country', [validators.Length(min=2, max=20)])
    pincode = StringField('Pincode', [validators.Length(min=6, max=6)])



@app.route('/bookings/<string:id>', methods=['GET', 'POST'])
def bookings(id):
    global g_id, b_id
    b_id = random.randint(1001, 10000)

    cur = mysql.connection.cursor()
    
    if id[0] == 'R':
        result = cur.execute("SELECT * FROM rooms WHERE r_id=%s", [id])
    else:
        result = cur.execute("SELECT * FROM amenities WHERE a_id=%s", [id])
    
    amenity = cur.fetchone()

    if id[0] == 'R' and amenity['r_status'] == 1:
        return redirect(url_for('rooms'))

    if id[0] != 'R' and amenity['a_status'] == 1:
        return redirect(url_for('amenities'))

    form = BookingForm()
    print("HERE2")
    if request.method=='POST':#form.g_id.validate_on_submit():
        print("HERE0")
        check_in = form.check_in.data.strftime('%Y-%m-%d')
        print(check_in)
        if id[0] == 'R':
            g_id = random.randint(1, 1000)

            result = cur.execute("SELECT r_type FROM rooms WHERE r_id=%s",[id])
            result = cur.fetchone()
            f_type = result['r_type']

            result = cur.execute("SELECT cost FROM charges WHERE code = 1 AND type=%s",[f_type])
            result = cur.fetchone()
            f_cost = result['cost']

            print(f_type, f_cost)
            
            check_out = form.check_out.data
        else:
            g_id = form.g_id.data
            
            result = cur.execute("SELECT a_type FROM amenities WHERE a_id=%s",[id])
            result = cur.fetchone()
            f_type = result['a_type']

            result = cur.execute("SELECT cost FROM charges WHERE code = 0 AND type=%s",[f_type])
            result = cur.fetchone()
            f_cost = result['cost']

            print(f_type, f_cost)
            
            check_out = check_in

        status = 1
        name = form.name.data
        count = form.count.data
        email = form.email.data
        streetno = form.streetno.data
        city = form.city.data
        state = form.state.data    
        country = form.country.data
        pincode = form.pincode.data

        print("hello "+check_in)


        if id[0] == 'R':
            cur.execute("INSERT INTO bookings(b_id, r_id, g_id, b_status, a_id, st, et, f_type, f_cost) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)", (b_id, id, g_id, status, '0', check_in, check_out, f_type, f_cost))
            cur.execute("INSERT INTO guests(g_id, g_name, g_email, g_count, g_streetno, g_city, g_state, g_country, g_pincode) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)",(g_id, name, email, count, streetno, city, state, country, pincode))
        else:
            cur.execute("INSERT INTO bookings(b_id, r_id, g_id, b_status, a_id, st, et, f_type, f_cost) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)", (b_id, '0', g_id, status, id, check_in, check_out, f_type, f_cost))
        
        mysql.connection.commit()

        cur.close()

        flash('Successfully Booked!', 'success')

        return redirect(url_for('bookings', id=id))

    return render_template('bookings.html', amenity=amenity, id=id, form=form)  

@app.route('/admin_guests')
def admin_guests():
    
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM guests")

    guests = cur.fetchall()

    if result > 0:
        return render_template('guests.html', guests=guests)
    else:
        msg = 'No guests in the Hotel currently'
        return render_template('guests.html', msg=msg)

    return render_template('guests.html')

class BillForm(Form):
    id = StringField('Guest ID', [validators.Length(min=1, max=5)])

@app.route('/generate_bill/<string:id>')
def generate_bill(id):
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM bookings WHERE  g_id = %s", [id])

    bookings = cur.fetchall()

    result = cur.execute("SELECT * FROM guests WHERE g_id = %s", [id])

    guest = cur.fetchone()

    #result = cur.execute("SELECT cost FROM charges c WHERE (c.type = (SELECT r_type FROM rooms r, bookings b2 WHERE r.r_id = b2.r_id AND b2.g_id = %s) AND code = 0) OR (c.type = (SELECT a_type FROM amenities a, bookings b2 WHERE a.a_id = b2.a_id AND b2.g_id = %s) AND code = 1)", (id, id))

    #costs = cur.fetchall()

    #print(costs)
    #print(len(bookings))

    #result = cur.execute("SELECT sum(cost) as total FROM charges c WHERE (c.type = (SELECT r_type FROM rooms r, bookings b2 WHERE r.r_id = b2.r_id AND b2.g_id = %s) AND code = 0) OR (c.type = (SELECT a_type FROM amenities a, bookings b2 WHERE a.a_id = b2.a_id AND b2.g_id = %s) AND code = 1)", (id, id))

    #total = cur.fetchone()

    total = 0

    for i in range(0, len(bookings)):
        total += bookings[i]['f_cost']

    rendered = render_template('generate_bill.html', len=len(bookings), guest=guest, bookings=bookings, total=total)
    pdf = pdfkit.from_string(rendered, False)

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=Bill.pdf'

    return response


@app.route('/billings', methods=['GET', 'POST'])
def billings():
    form = BillForm()

    if request.method == 'POST':
        id = form.id.data
        print(id)
        return redirect(url_for('generate_bill', id=id))
    return render_template('billings.html', form=form)

if __name__ == '__main__':

    # SECRET_KEY = os.urandom(32)
    # app.config['SECRET_KEY'] = SECRET_KEY

    # app.config["SESSION_TYPE"] = "filesystem"
    # Session(app)

    SECRET_KEY = os.urandom(32)
    app.config['WTF_CSRF_SECRET_KEY']=SECRET_KEY

    app.run(debug = True)
