from flask import Flask,render_template,request,redirect,flash,url_for,session
import mysql.connector
from otp import genotp
from itemkey import gen_id
from cmail import sendmail
import os
import stripe
stripe.api_key='sk_test_51NEwbpSGV8I6se9KORwedExAXFwLOMKImSP2IUR2kBUvA8lAhHEUXbPEuTKjPweb1V4Db1ij200j8PEx3Nsv5F2o00UtOfttxi'
app=Flask(__name__)
app.secret_key='jnjnnjskkskosiskc'
#deployment part
db=os.environ['RDS_DB_NAME']
user= os.environ['RDS_USERNAME']
password= os.environ['RDS_PASSWORD']
host= os.environ['RDS_HOSTNAME']
port=os.environ['RDS_PORT']
# mydb=mysql.connector.connect(host='localhost',user='root',password='admin',db='samuel')
mydb=mysql.connector.connect(host=host,user=user,password=password,db=db,port=port)
with mysql.connector.connect(host=host,password=password,user=user,db=db):
    cursor=mydb.cursor(buffered=True)
    cursor.execute("create table if not exists additems(itemid varchar(30) primary key,name varchar(30),description varchar(20),category enum('electronics','grocery','fashion','home&kitchen'),price integer)")
    cursor.execute("create table if not exists adminreg(username varchar(30) primary key,password varchar(20),email varchar(50))")
    cursor.execute("create table if not exists registration(username varchar(50) primary key,mobile varchar(20) unique,email varchar(50) unique,address varchar(50),password varchar(20))")
    cursor.execute("create table if not exists orders(oid int primary key,itemid varchar(9),itemname varchar(20),q int,total int,username varchar(30),foreign key (itemid) references additems(itemid) on update cascade on delete cascade,foreign key (username) references registration(username))")
#deployment part ends
@app.route('/',methods=['GET','POST'])
def home():
    return render_template('base.html')
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        name=request.form['Username']
        password=request.form['Password']
        print(name)
        print(password)
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from registration where username=%s && password=%s',[name,password])
        #c=cursor.fetchall()
        data=cursor.fetchone()[0]
        # print(data)
        print(c)
        cursor.close()
        if data == 1:
            session['user']=name
            if not session.get(session['user']):
                session[session['user']]={}
            return redirect(url_for('home'))
        else:
            return 'Invalid Username or Password'
    return render_template('login.html')
@app.route('/cart/<itemid>/<name>/<int:price>',methods=['POST'])
def cart(itemid,name,price):
    if session.get('user'):
        quantity=int(request.form['quantity'])
        if itemid not in session.get(session.get('user')):
            session[session.get('user')][itemid]=[name,quantity,price]
            session.modified=True
            flash(f'{name} added to cart')
            return redirect(url_for('cartview'))
        else:
            session[session.get('user')][itemid][1]+=quantity
            flash(f'Quantity increased to +{quantity}')
            return redirect(url_for('cartview'))
    else:
        return redirect(url_for('login'))
@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        username=request.form['username']
        mobile=request.form['mobile']
        #cofirmpassword=request.form['confirmpassword']
        email=request.form['email']
        address=request.form['address']
        password=request.form['password']
        otp=genotp()
        email=request.form['email']
        sendmail(to=email,subject='Thanks for registration',body=f'otp is:{otp}')
        return render_template('verification.html',username=username,password=password,email=email,mobile=mobile,address=address,otp=otp)
    return render_template('register.html')
@app.route('/otp/<username>/<mobile>/<email>/<address>/<password>/<otp>',methods=['GET','POST'])
def otp(username,mobile,email,address,password,otp):
    if request.method=='POST':
        uotp=request.form['uotp']
        if otp==uotp:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('insert into registration values(%s,%s,%s,%s,%s)',[username,mobile,email,address,password])
            mydb.commit()
            cursor.close()
            flash('details registered')
            return redirect(url_for('login'))
    return render_template('verification.html',username=username,mobile=mobile,email=email,address=address,password=password,otp=otp)
@app.route('/logout')
def logout():
    if session.get('user'):
        session.pop('user')
    return redirect(url_for('login'))
@app.route('/adminreg',methods=['GET','POST'])
def adminreg():
    if request.method=='POST':
        username=request.form['username']
        email=request.form['email']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from adminreg where username=%s',[username])
        count=cursor.fetchone()[0]
        if count!=1:
            cursor.execute('insert into adminreg values(%s,%s,%s)',[username,email,password])
            mydb.commit()
            cursor.close()
            return redirect(url_for('adminlogin'))
        else:
            return "only one admin is allowed to operate this application" 
    return render_template('admin_register.html')
@app.route('/adminlogin',methods=['GET','POST'])
def adminlogin():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from adminreg where username=%s && password=%s',[username,password])
        data=cursor.fetchone()[0]
        if data == 1:
            session['admin']=username
            return redirect(url_for('admindashboard'))
        else:
            return 'Invalid Username or Password'
   
        cursor.close()
    return render_template('admin_login.html') 
@app.route('/viewcart')
def cartview():
    if session.get('user'):
        items=session.get(session.get('user')) if session.get(session.get('user')) else 'empty'
        return render_template('cartview.html',items=items)
    else:
        return redirect(url_for('login'))
@app.route('/admindashboard')
def admindashboard():
    if session.get('admin'):
        return render_template('admindashboard.html')
    else:
        return redirect(url_for('adminlogin'))

@app.route('/adminlogout')
def adminlogout():
    if session.get('admin'):
        session.pop('admin')
    return redirect(url_for('adminlogin'))

@app.route('/additems',methods=['GET','POST'])
def additems():
    if session.get('admin'):
        if request.method=='POST':
            name=request.form['name']
            description=request.form['description']
            quantity=request.form['quantity']
            price=request.form['price']
            file_data=request.files['file']
            #filedata is an image
            filename=file_data.filename.split('.')
            if filename[-1]!='jpg':
                flash('please upload jpg files only')
                return render_template('additems.html')
            enum=request.form['enum']
            path=os.path.dirname(os.path.abspath(__file__))
            print(path)
            static_path=os.path.join(path,'static')
            itemid=gen_id()
            filename=itemid+'.jpg'
            #last .jpg included and itemid will be the filename for the img saved in static folder
            file_data.save(os.path.join(static_path,filename))
            cursor=mydb.cursor(buffered=True)
            cursor.execute('insert into additems values(%s,%s,%s,%s,%s,%s)',[itemid,name,
            description,quantity,enum,price])
            mydb.commit()
            cursor.close()
            flash('item added succesfully')
            return render_template('additems.html')
        return render_template('additems.html')
    return redirect(url_for('adminlogin'))
@app.route('/addcart')
def addcart():
    return render_template('addcart.html')

@app.route('/status')
def status():
    if session.get('admin'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select * from additems')
        data=cursor.fetchall()
        return render_template('status.html',data=data)
    else:
        return redirect(url_for('adminlogin'))

@app.route('/update/<itemid>',methods=['GET','POST'])
def update(itemid):
    if session.get('admin'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select  * from additems where itemid=%s',[itemid])
        data=cursor.fetchone()
        cursor.close()
        print(data)
        if request.method=='POST':
            print(request.form)
            name=request.form['name']
            description=request.form['description']
            quantity=request.form['quantity']
            category=request.form['category']
            price=request.form['price']
            cursor=mydb.cursor(buffered=True)
            cursor.execute('update additems set name=%s,description=%s,quantity=%s,category=%s,price=%s \
            where itemid=%s',[name,description,quantity,category,price,itemid] )
            mydb.commit()
            flash('item updated successfully')
            return redirect(url_for('status'))
        return render_template('updateproducts.html',data=data)
    else:
        return redirect(url_for('adminlogin'))

@app.route('/delete/<itemid>')
def delete(itemid):
    if session.get('admin'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('delete from additems where itemid=%s',[itemid])
        mydb.commit()
        path=os.path.dirname(os.path.abspath(__file__))
        print(path)
        static_path=os.path.join(path,'static')
        os.remove(os.path.join(static_path,itemid+'.jpg'))
        flash('items deleted successfully')
        return redirect(url_for('status'))
    else:
        return redirect(url_for('adminlogin'))
@app.route('/pay/<itemid>/<name>/<int:price>',methods=['POST'])
def pay(itemid,price,name):
    if session.get('user'):
        q=int(request.form['quantity'])
        username=session.get('user')
        total=price*q
        checkout_session=stripe.checkout.Session.create(
            success_url=url_for('success',itemid=itemid,name=name,q=q,total=total,_external=True),
            line_items=[
                {
                    'price_data': {
                        'product_data': {
                            'name': name,
                        },
                        'unit_amount': price*100,
                        'currency': 'inr',
                    },
                    'quantity': q,
                },
                ],
            mode="payment",)
        return redirect(checkout_session.url)
    else:
        return redirect(url_for('login'))
@app.route('/success/<itemid>/<name>/<q>/<total>')
def success(itemid,name,q,total):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('insert into orders(itemid,itemname,q,total,username) values(%s,%s,%s,%s,%s)',[itemid,name,q,total,session.get('user')])
        mydb.commit()
        cursor.close()
        return redirect(url_for('orderplaced'))
    else:
        return redirect(url_for('login'))

@app.route('/category/<category>')
def category(category):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select * from additems where category=%s',[category])
        data=cursor.fetchall()
        return render_template('items.html',data=data)
    else:
        return redirect(url_for('login'))
@app.route('/item/<itemid>')
def detail(itemid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select * from additems where itemid=%s',[itemid])
    items=cursor.fetchone()
    cursor.close()
    return render_template('detailedview.html',items=items)

@app.route('/orderplaced')
def orderplaced():
    return render_template('orderplaced.html')
@app.route('/cartpop/<itemid>')
def cartpop(itemid):
    if session.get('user'):
        session[session.get('user')].pop(itemid)
        session.modified=True
        flash('item removed')
        return redirect(url_for('cartview'))
    else:
        return redirect(url_for('login'))
@app.route('/orders')
def orders():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select * from orders where username=%s',[username])
        data=cursor.fetchall()
        cursor.close()
        return render_template('ordersdisplay.html',data=data)
    else:
        return redirect(url_for('login'))
if __name__=='__main__':
    app.run(debug=True,use_reloader=True)