from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from ..models import Usuario
from .. import db

bp = Blueprint('auth_routes', __name__)

@bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = Usuario.query.filter_by(email=email).first()
        if user and user.password_hash == password:
            login_user(user)
            flash('Login bem-sucedido!', 'success')
            return redirect(url_for('admin_routes.admin_dashboard')) if current_user.role == 'admin' else redirect(url_for('cliente_routes.cliente_dashboard'))
        else:
            flash('Login ou senha incorretos.', 'danger')
    return render_template('login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu com sucesso.', 'success')
    return redirect(url_for('auth_routes.login'))