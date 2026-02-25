from flask import g, current_app
from db_interface import RouteService


def get_db():
    if 'db_session' not in g:
        session_factory = current_app.config['SESSION_FACTORY']
        g.db_session = session_factory()
    return g.db_session


def get_route_service() -> RouteService:
    return RouteService(get_db())