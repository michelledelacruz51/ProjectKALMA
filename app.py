import os
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kalma-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kalma.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False