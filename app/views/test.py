from flask import Blueprint, render_template
from flask_login import login_required, current_user

test_bp = Blueprint('test', __name__)

@test_bp.route('/tailwind-test')
def tailwind_test():
    """
    A test route to verify Tailwind CSS is working.
    This route does not require authentication.
    """
    return render_template('test/tailwind_test.html', current_user=None)