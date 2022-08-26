import os

from flask import request, Blueprint, render_template, abort
from CTFd.utils.user import get_current_user, is_admin
from CTFd.utils.decorators import authed_only, admins_only
from CTFd.models import Users

from ..utils import get_current_challenge_id, random_home_path, dojo_route, get_active_users, redirect_user_socket


desktop = Blueprint("pwncollege_desktop", __name__)


def can_connect_to(desktop_user):
    return any((
        is_admin(),
        desktop_user.id == get_current_user().id,
        os.path.exists(f"/var/homes/nosuid/{random_home_path(desktop_user)}/LIVE")
    ))


def can_control(desktop_user):
    return any((
        is_admin(),
        desktop_user.id == get_current_user().id
    ))


@desktop.route("/desktop")
@desktop.route("/desktop/<int:user_id>")
@desktop.route("/<dojo>/desktop")
@desktop.route("/<dojo>/desktop/<int:user_id>")
@dojo_route
@authed_only
def view_desktop(dojo=None, user_id=None):
    current_user = get_current_user()
    if user_id is None:
        user_id = current_user.id

    user = Users.query.filter_by(id=user_id).first()
    if not can_connect_to(user):
        abort(403)

    try:
        password_type = "interact" if can_control(user) else "view"
        password_path = f"/var/homes/nosuid/{random_home_path(user)}/.vnc/pass-{password_type}"
        password = open(password_path).read()
    except FileNotFoundError:
        password = None

    active = bool(password)
    view_only = int(user_id != current_user.id)

    return render_template("desktop.html",
                           dojo=dojo,
                           active=active,
                           password=password,
                           user_id=user_id,
                           view_only=view_only)

@desktop.route("/desktop/<int:user_id>/")
@desktop.route("/desktop/<int:user_id>/<path:path>")
@authed_only
def forward_desktop(user_id, path=""):
    prefix = f"/desktop/{user_id}/"
    assert request.full_path.startswith(prefix)
    path = request.full_path[len(prefix):]

    user = Users.query.filter_by(id=user_id).first()
    if not can_connect_to(user):
        abort(403)

    return redirect_user_socket(user, ".vnc/novnc.socket", f"/{path}")


@desktop.route("/admin/desktops", methods=["GET"])
@admins_only
def view_all_desktops():
    return render_template("admin_desktops.html", users=get_active_users())