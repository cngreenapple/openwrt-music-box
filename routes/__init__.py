from flask import Blueprint

controls_bp = Blueprint('controls', __name__)
bt_bp = Blueprint('bluetooth', __name__)
library_bp = Blueprint('library', __name__)
playlist_bp = Blueprint('playlist', __name__)
system_bp = Blueprint('system', __name__)

from . import controls_routes
from . import bt_routes
from . import library_routes
from . import playlist_routes
from . import system_routes