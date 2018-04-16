from flask import Flask, render_template, make_response, flash, redirect, url_for, session, request, logging
import random
from flask_mysqldb import MySQL
from flask_wtf import Form
from wtforms import DateField, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
import pdfkit
from twilio.rest import Client
from datetime import date

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

        return redirect(url_for('add_amenity'))

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

        return redirect(url_for('edit_amenity'))

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
    form = RoomForm()

    if request.method == 'POST':
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
    check_in = DateField('Pick a Date', format="%m/%d/%Y")
    check_out = DateField('Pick a Date', format="%m/%d/%Y")
    status = StringField('Status', [validators.Length(min=1, max=1)])
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
    global x, g_id, b_id
    x = 1
    g_id = random.randint(1, 1000)
    b_id = random.randint(1001, 10000)

    cur = mysql.connection.cursor()
    
    if id[0] == 'R':
        result = cur.execute("SELECT * FROM rooms WHERE r_id=%s", [id])
    else:
        result = cur.execute("SELECT * FROM amenities WHERE a_id=%s", [id])
    
    amenity = cur.fetchone()

    form = BookingForm()

    if form.validate_on_submit():
        
        check_in = form.check_in.data.strftime('%Y-%m-%d')
        check_out = form.check_out.data
        status = form.status.data
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
            cur.execute("INSERT INTO bookings(b_id, r_id, g_id, b_status, a_id, st, et) VALUES(%s, %s, %s, %s, %s, %s, %s)", (b_id, id, g_id, status, '0', check_in, check_out))
        else:
            cur.execute("INSERT INTO bookings(b_id, r_id, g_id, b_status, a_id, st, et) VALUES(%s, %s, %s, %s, %s, %s, %s)", (b_id, '0', g_id, status, id, check_in, check_out))

        cur.execute("INSERT INTO guests(g_id, g_name, g_email, g_count, g_streetno, g_city, g_state, g_country, g_pincode) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)",(g_id, name, email, count, streetno, city, state, country, pincode))

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

    rendered = render_template('generate_bill.html', guest=guest, bookings=bookings)
    pdf = pdfkit.from_string(rendered, False)

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=output.pdf'

    return response


@app.route('/billings', methods=['GET', 'POST'])
def billings():
    form = BillForm()

    if request.method == 'POST':
        id = form.id.data
        print(id)
        return redirect(url_for('generate_bill', id=id))
    return render_template('billings.html', form=form)


@app.route('/<name>/<location>')
def pdf_template(name, location):
    rendered = render_template('pdf_template.html', name=name, location=location)
    pdf = pdfkit.from_string(rendered, False)

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=output.pdf'

    account_sid = 'AC4813fd548f065ee195b1aa2feb96c58f' # Found on Twilio Console Dashboard
    auth_token = 'cda8141ecc84ab6ae0489aacab4d3586' # Found on Twilio Console Dashboard
    myPhone = '+918130733945' # Phone number you used to verify your Twilio account
    TwilioNumber = '+12692206694' # Phone number given to you by Twilio
    client = Client(account_sid, auth_token)

    client.messages.create(
        to=myPhone,
        from_=TwilioNumber,
        body='I sent a text message from twilio! ' + u'\U0001f680')

    return response


if __name__ == '__main__':
	app.secret_key = 'xyzapp123'
	app.run(debug = True)