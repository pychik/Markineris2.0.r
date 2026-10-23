from datetime import date

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from config import settings
from models import db
from rd_registry.service import NO_COUNTRY, RD_MIN_DATE, category_choices, category_label, list_rd, min_suggest_date, \
    recommend_rd, save_rd, search_rd, set_archived
from tezaurus.runtime_catalogs import get_all_countries
from utilities.support import bck_sumausmumu_required, user_activated

rd_registry = Blueprint("rd_registry", __name__)

# Кто открывает страницу реестра, добавляет и правит записи. Операторы (manager) только ищут из карточки.
ACCESS_ROLES = {settings.SUPER_USER, settings.SUPER_MANAGER}
# Кто архивирует и возвращает из архива - только администратор.
ARCHIVE_ROLES = {settings.SUPER_USER}

# для ссылки «Реестр РД» в выпадающих меню CRM
rd_registry.add_app_template_global(ACCESS_ROLES, "rd_registry_access_roles")


def _check_role(roles: set[str]) -> None:
    if current_user.role not in roles:
        abort(403)


def _back():
    """Назад на страницу реестра с теми же фильтрами; принимаем только внутренние пути модуля."""
    index_url = url_for("rd_registry.index")
    target = request.form.get("next") or ""
    return redirect(target if target.startswith(index_url) else index_url)


@rd_registry.route("/search", methods=["GET"])
@login_required
@user_activated
@bck_sumausmumu_required
def search():
    items, has_more = search_rd(request.args.get("q"), tnved=request.args.get("tnved"),
                                country=request.args.get("country"))
    return jsonify(status="success", items=items, has_more=has_more)


@rd_registry.route("/recommended", methods=["GET"])
@login_required
@user_activated
@bck_sumausmumu_required
def recommended():
    """Проверенные РД из Tezaurus под ТНВЭД, страну и вид товара карточки."""
    items = recommend_rd(request.args.get("tnved"), request.args.get("country"), request.args.get("type"))
    return jsonify(status="success", items=items)


@rd_registry.route("/", methods=["GET"])
@login_required
@user_activated
def index():
    _check_role(ACCESS_ROLES)
    filters = {
        "q": request.args.get("q", ""),
        "archived": request.args.get("archived") == "1",
        "hide_expired": request.args.get("hide_expired") == "1",
        "category": request.args.get("category", ""),
        "rd_type": request.args.get("rd_type", ""),
        "country": request.args.get("country", ""),
        "sort": "updated" if request.args.get("sort") == "updated" else "created",
        "dir": "asc" if request.args.get("dir") == "asc" else "desc",
    }
    pagination = list_rd(
        query=filters["q"],
        archived=filters["archived"],
        hide_expired=filters["hide_expired"],
        category=filters["category"],
        rd_type=filters["rd_type"],
        country=filters["country"],
        sort=filters["sort"],
        direction=filters["dir"],
        page=request.args.get("page", 1, type=int),
    )
    # сортировка, фильтры и пагинация перерисовывают только блок таблицы (см. JS в index.html)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    return render_template(
        "rd_registry/_results.html" if is_ajax else "rd_registry/index.html",
        pagination=pagination,
        **filters,
        rd_types=settings.RD_TYPES,
        categories=category_choices(),
        countries=get_all_countries(),
        no_country=NO_COUNTRY,
        category_label=category_label,
        rd_min_date=RD_MIN_DATE,
        today=date.today(),
        min_suggest_date=min_suggest_date(),
        can_archive=current_user.role in ARCHIVE_ROLES,
    )


@rd_registry.route("/save", methods=["POST"])
@login_required
@user_activated
def save():
    _check_role(ACCESS_ROLES)
    try:
        save_rd(request.form, user_id=current_user.id, entry_id=request.form.get("entry_id", type=int))
        db.session.commit()
        flash("РД сохранён.", "success")
    except ValueError as e:
        db.session.rollback()
        flash(str(e), "error")
    return _back()


@rd_registry.route("/<int:entry_id>/archive", methods=["POST"])
@login_required
@user_activated
def archive(entry_id: int):
    _check_role(ARCHIVE_ROLES)
    archived = request.form.get("archived") == "1"
    try:
        set_archived(entry_id, archived, user_id=current_user.id)
        db.session.commit()
        flash("РД перенесён в архив." if archived else "РД возвращён из архива.", "success")
    except ValueError as e:
        db.session.rollback()
        flash(str(e), "error")
    return _back()
