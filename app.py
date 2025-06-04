from flask import Flask, render_template, request, redirect, url_for, session
import pymysql
from config import Config
# import pyotp
from steam_guard import generate_steam_guard_code
from cryptography.fernet import Fernet
import datetime
from account_manager import AccountManager
from order_manager import OrderManager
import datetime as dt

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']

# 初始化加密器
cipher_suite = Fernet(app.config['ENCRYPTION_KEY'])

# 初始化管理器
account_mgr = AccountManager()
order_mgr = OrderManager()


def get_db_connection():
    return pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        db=app.config['MYSQL_DB'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


def encrypt_data(data):
    """加密敏感数据"""
    return cipher_suite.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data):
    """解密数据"""
    return cipher_suite.decrypt(encrypted_data.encode()).decode()


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        order_id = request.form['order_id'].strip()
        client_ip = request.remote_addr

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 查询订单及关联账号
                sql = """
                SELECT o.*, a.steam_username, a.steam_password, a.steam_shared_secret 
                FROM orders o
                JOIN steam_accounts a ON o.account_id = a.account_id
                WHERE o.order_id = %s
                """
                cursor.execute(sql, (order_id,))
                order = cursor.fetchone()

                if not order:
                    return render_template('error.html', message="订单号不存在，请检查输入")

                # 检查订单状态
                current_time = datetime.datetime.now()
                if current_time > order['expire_time']:
                    # 更新订单状态为过期
                    update_sql = "UPDATE orders SET status = 'expired' WHERE order_id = %s"
                    cursor.execute(update_sql, (order_id,))
                    conn.commit()
                    return render_template('error.html', message="订单已过期")

                if order['status'] != 'active':
                    return render_template('error.html', message="订单状态无效")

                # 检查访问次数
                if order['access_count'] >= app.config['MAX_ACCESS']:
                    return render_template('error.html', message="超过最大访问次数限制")

                # 更新访问记录
                new_count = order['access_count'] + 1
                update_sql = """
                UPDATE orders 
                SET access_count = %s, last_access_ip = %s 
                WHERE order_id = %s
                """
                cursor.execute(update_sql, (new_count, client_ip, order_id))

                # 更新账号最后使用时间
                account_update = "UPDATE steam_accounts SET last_used = %s WHERE account_id = %s"
                cursor.execute(account_update, (current_time, order['account_id']))

                conn.commit()

                # 生成动态令牌
                totp = generate_steam_guard_code(order['steam_shared_secret'])
                auth_code = totp

                # 解密账号密码
                username = decrypt_data(order['steam_username'])
                password = decrypt_data(order['steam_password'])

                return render_template('result.html',
                                       username=username,
                                       password=password,
                                       auth_code=auth_code,
                                       expire_time=order['expire_time'],
                                       access_count=new_count,
                                       max_access=app.config['MAX_ACCESS'])
        except Exception as e:
            print(f"处理订单时出错: {str(e)}")
            return render_template('error.html', message="系统错误，请稍后再试")
        finally:
            conn.close()

    return render_template('index.html')


# 管理员登录
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == app.config['ADMIN_USER'] and password == app.config['ADMIN_PASS']:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin/login.html', error="用户名或密码错误")

    return render_template('admin/login.html')


# 管理员登出
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


# 管理仪表盘
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 获取统计信息
            cursor.execute("SELECT COUNT(*) AS total_orders FROM orders")
            total_orders = cursor.fetchone()['total_orders']

            cursor.execute("SELECT COUNT(*) AS active_orders FROM orders WHERE status = 'active'")
            active_orders = cursor.fetchone()['active_orders']

            cursor.execute("SELECT COUNT(*) AS total_accounts FROM steam_accounts")
            total_accounts = cursor.fetchone()['total_accounts']

            # 添加当前时间
            current_time = dt.datetime.now()

            return render_template('admin/dashboard.html',
                                   total_orders=total_orders,
                                   active_orders=active_orders,
                                   total_accounts=total_accounts,
                                   now=current_time,  # 传递当前时间
                                   RENTAL_DAYS=app.config['RENTAL_DAYS'],
                                   MAX_ACCESS=app.config['MAX_ACCESS'])
    finally:
        conn.close()


# 账号管理
@app.route('/admin/accounts')
def admin_accounts():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    accounts = account_mgr.get_accounts()
    return render_template('admin/accounts.html', accounts=accounts)


# 订单管理
@app.route('/admin/orders')
def admin_orders():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    orders = order_mgr.get_orders()
    return render_template('admin/orders.html', orders=orders)


# 添加账号
@app.route('/admin/add_account', methods=['POST'])
def admin_add_account():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    username = request.form['username']
    password = request.form['password']
    shared_secret = request.form['shared_secret']

    if account_mgr.add_account(username, password, shared_secret):
        return redirect(url_for('admin_accounts'))
    else:
        return render_template('admin/accounts.html',
                               accounts=account_mgr.get_accounts(),
                               error="添加账号失败")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

