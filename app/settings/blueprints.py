from flask import Flask


def register_blueprints(app: Flask) -> None:
    from views.main.auth import auth as auth_blueprint
    from views.main.main import main as main_blueprint
    from views.main.admin_control import admin_control as ac_blueprint
    from views.main.user_cp import user_cp as ucp_blueprint
    from views.main.archive import orders_archive as orders_archive_blueprint
    from views.main.categories.shoes import shoes as shoes_blueprint
    from views.main.categories.linen import linen as linen_blueprint
    from views.main.categories.parfum import parfum as parfum_blueprint
    from views.main.categories.clothes import clothes as clothes_blueprint
    from views.main.requests_common import requests_common as requests_common_blueprint
    from views.crm.crm_dash import crm_d as crm_d_blueprint
    from views.crm.crm_uoc import crm_uoc as crm_uoc_blueprint
    from views.api.transactions import api as api_blueprint

    app.register_blueprint(auth_blueprint)
    app.register_blueprint(main_blueprint)
    app.register_blueprint(ac_blueprint, url_prefix='/admin_control')
    app.register_blueprint(ucp_blueprint, url_prefix='/user_control_panel')
    app.register_blueprint(orders_archive_blueprint, url_prefix='/orders_archive')
    app.register_blueprint(shoes_blueprint, url_prefix='/shoes')
    app.register_blueprint(linen_blueprint, url_prefix='/linen')
    app.register_blueprint(parfum_blueprint, url_prefix='/parfum')
    app.register_blueprint(clothes_blueprint, url_prefix='/clothes')
    app.register_blueprint(requests_common_blueprint, url_prefix='/rc')
    app.register_blueprint(crm_d_blueprint, url_prefix='/crm_dashboard')
    app.register_blueprint(crm_uoc_blueprint, url_prefix='/crm_uoc')
    app.register_blueprint(api_blueprint, url_prefix='/api')
