import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
import time
from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    username = db.execute("SELECT username FROM users WHERE id=?",session["user_id"])[0]['username']
    stocks = db.execute("SELECT DISTINCT(symbol) FROM buy_info WHERE username=?",username)
    compilation = stocks
    in_stocks = 0
    for i in range(len(compilation)):
        dummy = compilation[i]
        print(db.execute("SELECT company_name FROM buy_info WHERE symbol=?",dummy['symbol']))
        dummy['company_name'] = db.execute("SELECT company_name FROM buy_info WHERE symbol=?",dummy['symbol'])[0]['company_name']
        print(db.execute("SELECT SUM(stock_number) FROM buy_info WHERE symbol=? AND username=?",dummy['symbol'],username)[0])
        dummy['total_stocks'] = db.execute("SELECT SUM(stock_number) FROM buy_info WHERE symbol=? AND username=?",dummy['symbol'],username)[0]['SUM(stock_number)']
        dummy['price_stocks'] = lookup(dummy['symbol'])['price']
        dummy['total_value'] = dummy['total_stocks'] * dummy['price_stocks']
        in_stocks += dummy['total_value']
        dummy['total_value'] = usd(dummy['total_value'])
        dummy['price_stocks'] = usd(dummy['price_stocks'])
        if dummy['total_stocks'] > 0:
            compilation[i] = dummy
        else:
            compilation[i] = {}
    balance = db.execute("SELECT cash FROM users WHERE username=?",username)[0]['cash']
    total = balance + in_stocks
    balance = usd(balance)
    total = usd(total)
    return render_template("index.html", all = compilation, balance = balance, total = total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    elif request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        if shares.isnumeric() != True:
            return apology("Invalid Shares")
        shares = int(shares)
        if (shares) <= 0:
            return apology("Invalid Shares")
        if symbol == "":
            return apology("Invalid Symbol")
        price = lookup(symbol)
        if price == None:
            return apology("Invalid Symbol")
        company_name = price['name']
        price = price['price']
        username = db.execute("SELECT username FROM users WHERE id=?",session["user_id"])[0]['username']
        print(username)
        current_cash = db.execute("SELECT cash FROM users WHERE id=?",session["user_id"])
        current_cash = current_cash[0]['cash']
        required_cash = price * shares;
        if current_cash < required_cash:
            return apology("Thats outside your budget")
        else:
            try:
                prev = db.execute("SELECT * FROM buy_info")
            except:
                code = "CREATE TABLE buy_info ( ide INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, username TEXT, symbol TEXT, company_name TEXT, cash_before FLOAT ,stock_price FLOAT, stock_number INT, time TEXT)"
                db.execute(code)
            values = [username, symbol, company_name, current_cash, price, shares, time.ctime(time.time())]
            db.execute("INSERT INTO buy_info (username, symbol, company_name,cash_before,stock_price,stock_number,time) VALUES (?)",values)
            db.execute("UPDATE users SET cash=? WHERE username=? ",current_cash-required_cash,username)
        return index()
    return apology("TODO")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    username = db.execute("SELECT username FROM users WHERE id=?",session["user_id"])[0]['username']
    ids = db.execute("SELECT ide FROM buy_info WHERE username=?",username)
    for i in range(len(ids)):
        dummy = ids[i]
        id = dummy['ide']
        #print(db.execute("SELECT company_name FROM buy_info WHERE symbol=?",dummy['symbol']))
        symbol = db.execute("SELECT symbol FROM buy_info WHERE ide=?",id)[0]['symbol']
        dummy['symbol'] = symbol
        dummy['company_name'] = db.execute("SELECT company_name FROM buy_info WHERE ide=?",id)[0]['company_name']
        #print(db.execute("SELECT SUM(stock_number) FROM buy_info WHERE symbol=? AND username=?",dummy['symbol'],username)[0])
        dummy['stock_number'] = db.execute("SELECT stock_number FROM buy_info WHERE ide=?",id)[0]['stock_number']
        if dummy['stock_number'] > 0:
            dummy['nature'] = "Bought"
        else:
            dummy['stock_number'] *= -1
            dummy['nature'] = "Sold"
        dummy['price_stocks'] = lookup(symbol)['price']
        dummy['total_value'] = dummy['stock_number'] * dummy['price_stocks']
        dummy['total_value'] = usd(dummy['total_value'])
        dummy['price_stocks'] = usd(dummy['price_stocks'])
        dummy['time'] = db.execute("SELECT time FROM buy_info WHERE ide=?",id)[0]['time']
        ids[i] = dummy
    return render_template("history.html",all=ids)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "GET":
        needed= True
        return render_template("quote.html",needed=needed)
    elif request.method == "POST":
        needed = False
        symbol = request.form.get("symbol")
        print(symbol)
        price = lookup(symbol)
        if price == None:
            return apology("The symbol does not exist")
            #return apology("Invalid Username")return render_template("quote.html",needed=needed,price=price,symbol=symbol,exist=False)
        else:
            price = price['price']
            return render_template("quote.html",needed=needed,price=price,symbol=symbol,exist=True)
    """Get stock quote."""
    return apology("TODO")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template('register.html')
    elif request.method == "POST":
        username = request.form.get("username")
        passw = request.form.get("password")
        conf = request.form.get("confirmation")
        users = db.execute("SELECT username FROM users")
        if username == "":
            return apology("Invalid Username")
        for i in users:
            if username == i['username']:
                return apology("Invalid Username")
        if passw == "":
            return apology("Issue with password")
        if passw != conf:
            return apology("Issue with password")
        hashed = generate_password_hash(passw)
        db.execute("INSERT INTO users (username,hash) VALUES (:username,:hashed)",username=username,hashed=hashed)
        return render_template("login.html")
    """Register user"""
    return apology("issue in registration")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    username = db.execute("SELECT username FROM users WHERE id=?",session["user_id"])[0]['username']
    if request.method == "GET":
        symbols = db.execute("SELECT DISTINCT(symbol) from buy_info WHERE username=?",username)
        print(symbols)
        final = []
        for i in range(len(symbols)):
            symbols[i] = symbols[i]['symbol']
            if db.execute("SELECT SUM(stock_number) FROM buy_info WHERE username=? and symbol=?",username,symbols[0])[0]['SUM(stock_number)']>0:
                final.append(symbols[i])
        return render_template("sell.html",symbols=final)
    elif request.method == "POST":
        symbol = request.form.get('symbol')
        cost = lookup(symbol)['price']
        stocks = db.execute("SELECT SUM(stock_number) FROM buy_info WHERE username=? and symbol=?",username,symbol)[0]['SUM(stock_number)']
        shares = int(request.form.get('shares'))
        if shares > stocks or shares <= 0:
            return apology("Invalid no of stocks")
        tot_cost = int(cost) * shares
        tot_cost = float(tot_cost)
        current_cash = db.execute("SELECT cash FROM users WHERE id=?",session["user_id"])
        current_cash = current_cash[0]['cash']
        print("Here")
        print(current_cash,tot_cost)
        company_name = lookup(symbol)['name']
        price = cost
        values = [username, symbol, company_name, current_cash, price, -1*shares, time.ctime(time.time())]
        db.execute("INSERT INTO buy_info (username, symbol, company_name,cash_before,stock_price,stock_number,time) VALUES (?)",values)
        db.execute("UPDATE users SET cash=? WHERE username=? ",current_cash+tot_cost,username)
        return index()
    return apology("TODO")

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    """Sell shares of stock"""
    username = db.execute("SELECT username FROM users WHERE id=?",session["user_id"])[0]['username']
    if request.method == "GET":
        return render_template("add.html")
    elif request.method == "POST":
        print("HI")
        amount = float(request.form.get("amount"))
        if amount <= 0:
            return aplolgy("Invalid Amount")
        else:
            current_cash = db.execute("SELECT cash FROM users WHERE username=?",username)[0]['cash']
            db.execute("UPDATE users SET cash=? WHERE username=? ",current_cash+amount,username)
        return index()
    return apology("TODO")
