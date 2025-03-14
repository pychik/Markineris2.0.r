from flask_migrate import Migrate
from flask_simple_captcha import CAPTCHA
from jinja2.filters import FILTERS
import urllib3

from config import settings
from settings.initialization import create_app
from settings.blueprints import register_blueprints
from settings.handlers import register_handlers, setup_login
from .commands import create_superuser, create_superuser_custom, set_server_default_params
from .jinja_filters import count_quantity, time_since, time_since_top

urllib3.disable_warnings()

# jinja template filter adding
FILTERS["count_quantity"] = count_quantity
FILTERS["time_since"] = time_since
FILTERS["time_since_top"] = time_since_top

migrate_handler = Migrate()
SIMPLE_CAPTCHA = CAPTCHA(config=settings.CAPTCHA_CONFIG)
# Then later on.

app, db = create_app()
register_blueprints(app)
register_handlers(app)
setup_login(app)
SIMPLE_CAPTCHA.init_app(app)

app.cli.add_command(create_superuser)
app.cli.add_command(create_superuser_custom)
app.cli.add_command(set_server_default_params)


if __name__ == '__main__':
    app.run(debug=True)
