# -*- coding: utf-8 -*-
"""Extensions module. Each extension is initialized in the app factory located in app.py."""
import os
from flask_login import LoginManager
from flask_marshmallow import Marshmallow
from flask_principal import Principal
from flask_sqlalchemy import SQLAlchemy
from redis import Redis
from flask_session import Session
from flask_migrate import Migrate

db = SQLAlchemy()
login_manager = LoginManager()
ma = Marshmallow()
principal = Principal()
session = Session()
migrate = Migrate()
redis = Redis.from_url(url=os.environ.get('REDIS_URL', 'redis://localhost:6379'))