import os

from flask import Flask, g
from sqlalchemy import create_engine, pool
from sqlalchemy.orm import sessionmaker

from routes.station_routes import station_bp
from routes.map_routes import map_bp
from routes.train_routes import train_bp

DB_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'EuroTicket_2.db')

engine = create_engine(
    f'sqlite:///{DB_PATH}',
    poolclass=pool.QueuePool,
    pool_size=10,
    max_overflow=20
)
SessionLocal = sessionmaker(bind=engine)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config['DB_ENGINE'] = engine
    app.config['SESSION_FACTORY'] = SessionLocal

    app.register_blueprint(station_bp)
    app.register_blueprint(map_bp)
    app.register_blueprint(train_bp)

    @app.teardown_appcontext
    def close_db(error):
        db_session = g.pop('db_session', None)
        if db_session is not None:
            db_session.close()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
    #dummy comment for testing purposes of auto update
