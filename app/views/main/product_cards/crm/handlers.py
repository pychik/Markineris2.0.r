import zipfile
from datetime import datetime
from io import BytesIO

from flask import flash, redirect, render_template, request, jsonify, send_file, url_for
from flask_login import current_user
from pandas import DataFrame
from xlsxwriter import Workbook
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import joinedload
from typing import Optional

from logger import logger
from models import db, ProductCard, User, ModerationStatus, ProcessingCompany, UserProcessingCompany
from utilities.download import OrdersProcessor, ShoesProcessor, ClothesProcessor, SocksProcessor, LinenProcessor, \
    ParfumProcessor
from views.crm.schema import is_forbidden_pair_by_inn
from .helpers import crm_get_cards, helper_categories_counter, split_cards_by_status, product_card_download_common, \
    delete_company_from_pool_no_reassign, h_pc_move_render_list_html, h_append_card_log, \
    h_pc_move_pack_cards, h_pc_move_template_for_status, h_pc_move_get_cards_by_status, \
    h_pc_move_apply_status_transition, get_card_download_info, h_find_card_ids_by_article_or_tm, \
    h_cards_ctx_key_for_status, helper_reject_cards_by_rd_date_to_today, is_at2_admin_user, \
    get_crm_card_for_user, apply_crm_cards_scope
from .transitions import validate_transition, check_special_rules, check_owner_or_admin
from ..support import CATEGORIES_COMMON, MODERATION_STATUS_TITLES, json_response, card_has_rd
from config import settings


def h_crm_cards():
    category = request.args.get("category")  # slug: clothes/shoes/...
    subcategory = request.args.get("subcategory")  # только для clothes

    cards = crm_get_cards(category=category, subcategory=subcategory, user=current_user)
    buckets = split_cards_by_status(cards)
    sent_no_rd_cards = buckets["sent_no_rd"]
    sent_cards = buckets["sent"]
    in_progress_cards = buckets["in_progress"]
    in_moderation_cards = buckets["in_moderation"]
    clarification_cards = buckets["clarification"]
    approved_cards = buckets["approved"]
    rejected_cards = buckets["rejected"]
    categories_common = CATEGORIES_COMMON
    categories_counter = helper_categories_counter(cards)
    status_counter = {k: len(v) for k, v in buckets.items()}

    companies_pool = (
        ProcessingCompany.query
        .filter(ProcessingCompany.is_active.is_(True))
        .with_entities(ProcessingCompany.id, ProcessingCompany.inn, ProcessingCompany.title)
        .distinct()
        .order_by(ProcessingCompany.title.asc())
        .all()
    )
    bck = request.args.get("bck", 0, type=int)

    if bck:
        return jsonify({
            "status": "success",
            "htmlresponse": render_template("product_cards/crm/cards/data_block.html", **locals())
        })

    return render_template("product_cards/crm/crm_main.html", **locals())


def h_pc_lazy_column():
    status_value = (request.args.get("status") or "").strip()
    category = (request.args.get("category") or "").strip() or None
    subcategory = (request.args.get("subcategory") or "").strip() or None
    company_id = request.args.get("company_id", type=int)  # ✅ NEW

    allowed = {
        ModerationStatus.SENT_NO_RD.value,
        ModerationStatus.SENT.value,
        ModerationStatus.IN_PROGRESS.value,
        ModerationStatus.IN_MODERATION.value,
        ModerationStatus.APPROVED.value,
        ModerationStatus.REJECTED.value,
        ModerationStatus.PARTIALLY_APPROVED.value,
    }
    if status_value not in allowed:
        return jsonify(status="error", message="Недопустимый статус"), 400

    if category and category not in CATEGORIES_COMMON:
        return jsonify(status="error", message="Неизвестная категория"), 400
    if subcategory and category != "clothes":
        return jsonify(status="error", message="Подкатегория доступна только для clothes"), 400

    # ✅ company_id валидируем (пустой/None = нет фильтра)
    if company_id is not None and company_id <= 0:
        return jsonify(status="error", message="Некорректная компания"), 400

    cards = h_pc_move_get_cards_by_status(
        status_value=status_value,
        category=category,
        subcategory=subcategory,
        company_id=company_id,
    )
    packed = h_pc_move_pack_cards(cards)

    tpl = h_pc_move_template_for_status(status_value)
    if not tpl:
        return jsonify(status="error", message="Шаблон не найден"), 500

    ctx = {"categories_common": CATEGORIES_COMMON}

    if status_value == ModerationStatus.SENT.value:
        ctx["sent_cards"] = packed
    elif status_value == ModerationStatus.SENT_NO_RD.value:
        ctx["sent_no_rd_cards"] = packed
    elif status_value == ModerationStatus.IN_PROGRESS.value:
        ctx["in_progress_cards"] = packed
    elif status_value == ModerationStatus.IN_MODERATION.value:
        ctx["in_moderation_cards"] = packed
    elif status_value == ModerationStatus.APPROVED.value:
        ctx["approved_cards"] = packed
    elif status_value == ModerationStatus.REJECTED.value:
        ctx["rejected_cards"] = packed
    else:
        ctx["partially_approved_cards"] = packed

    html = render_template(tpl, **ctx)

    return jsonify(
        status="success",
        qty=len(packed),
        list_html=html,
        status_value=status_value
    )


def h_download_product_card(pc_id: int):
    card = (
        apply_crm_cards_scope(ProductCard.query, current_user)
        .filter(ProductCard.id == pc_id)
        .with_entities(ProductCard.id, ProductCard.user_id)
        .first()
    )
    if not card:
        flash(message="Карточка не найдена", category="error")
        return redirect(url_for('crm_d.cards'))

    user = User.query.get(card.user_id)

    return product_card_download_common(user=user, pc_id=pc_id)


def h_transfer_sent_to_in_progress():

    role = getattr(current_user, "role", None)

    allowed_roles = [settings.SUPER_USER, settings.SUPER_MANAGER, settings.MANAGER_USER]
    if role not in allowed_roles:
        return json_response(status="error", message="Недостаточно прав", code=403)

    dt = datetime.now()
    dt_str = dt.strftime("%d.%m.%Y %H:%M")

    q = ProductCard.query.filter(ProductCard.status == ModerationStatus.SENT)

    cards = q.order_by(ProductCard.id.asc()).all()

    if not cards:
        return json_response(status="error", message="Нет карточек в статусе 'Отправленные'", code=404)

    moved = 0
    try:
        for card in cards:
            card.status = ModerationStatus.IN_PROGRESS
            card.manager_id = current_user.id
            card.sent_at = dt
            card.card_log = h_append_card_log(
                card.card_log,
                f"\n{dt_str} карточка переведена в обработку массовым переносом оператором {current_user.login_name};"
            )
            moved += 1

        db.session.commit()
        # db.session.rollback()
    except Exception as e:
        db.session.rollback()
        return json_response(status="error", message=f"Ошибка переноса: {e}", code=500)

    return json_response(status="success", message=f"Перенесено карточек: {moved}", moved=moved)


def h_download_cards_companies_in_progress():

    CATEGORY_META = {
        "shoes": (CATEGORIES_COMMON["shoes"]["rel_name"], ShoesProcessor, settings.Shoes.CATEGORY),
        "clothes": (CATEGORIES_COMMON["clothes"]["rel_name"], ClothesProcessor, settings.Clothes.CATEGORY),
        "socks": (CATEGORIES_COMMON["socks"]["rel_name"], SocksProcessor, settings.Socks.CATEGORY),
        "linen": (CATEGORIES_COMMON["linen"]["rel_name"], LinenProcessor, settings.Linen.CATEGORY),
        "parfum": (CATEGORIES_COMMON["parfum"]["rel_name"], ParfumProcessor, settings.Parfum.CATEGORY),
    }

    # ----------------------------
    # helpers
    # ----------------------------
    def _json_error(message: str, code: int = 400):
        return jsonify(status="error", message=message), code

    def _safe_part(s: str) -> str:
        s = (s or "").strip()
        for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
            s = s.replace(ch, "_")
        return s[:180]

    def _get_manager_id_from_request() -> Optional[int]:
        mid = request.form.get("manager_id", type=int)
        if mid is None and request.is_json:
            mid = (request.json or {}).get("manager_id")
        return int(mid) if mid else None

    def _pad_rows(rows: list[list], width: int) -> list[list]:
         out = []
         for r in rows:
             r = list(r) if r is not None else []
             if len(r) < width:
                 r = r + [""] * (width - len(r))
             elif len(r) > width:
                 r = r[:width]
             out.append(r)
         return out

    def _set_autowidth_columns(worksheet, data: list[list]):
         if not data:
             return
         col_widths = {}
         for row in data:
             for c, cell in enumerate(row):
                 ln = len(str(cell)) if cell is not None else 0
                 col_widths[c] = max(col_widths.get(c, 0), ln)
         for c, w in col_widths.items():
             worksheet.set_column(c, c, min(w + 2, 80))

    def _build_category_excels(category_key: str, card_items: list[tuple[int, list]], *, flag_046: bool = False) -> \
    list[tuple[BytesIO, str]]:
        """
        Делает 0..2 XLSX файла на категорию:
          - <category>_РФ_ВНУТР.xlsx  (если есть inner)
          - <category>_ВВЕЗЕН.xlsx   (если есть outer)
        В каждой строке данных последний столбец = card_id.
        ШАПКУ НЕ МЕНЯЕМ.
        """
        rel_name, processor_cls, category_for_headers = CATEGORY_META[category_key]

        start_rows = OrdersProcessor.excel_start_data_ext(
            category=category_for_headers,
            flag_046=flag_046
        ) or []

        # ❌ УБРАТЬ: заголовок card_id в шапке не нужен
        # start_rows[0] = start_rows[0] + ["card_id"]

        rows_outer, rows_inner = [], []

        for pc_id, items in card_items:
            if not items:
                continue

            _common, outer, inner = processor_cls.prepare_ext_data(
                orders_list=items,
                flag_046=flag_046,
                has_aggr=False,
            )

            if outer:
                rows_outer.extend([list(r) + [pc_id] for r in outer])
            if inner:
                rows_inner.extend([list(r) + [pc_id] for r in inner])

        # если вообще нет строк — ничего не делаем
        if not rows_outer and not rows_inner:
            return []

        # ширина по максимуму среди реально используемых данных (шапка + outer/inner)
        width = max([len(r) for r in (start_rows + rows_outer + rows_inner)] or [0])
        start_rows_p = _pad_rows(start_rows, width) if start_rows else []
        rows_outer_p = _pad_rows(rows_outer, width)
        rows_inner_p = _pad_rows(rows_inner, width)

        files: list[tuple[BytesIO, str]] = []

        def _make_one_xlsx(sheet_title: str, data_rows: list[list], suffix: str) -> tuple[BytesIO, str]:
            output = BytesIO()
            wb = Workbook(output)
            ws = wb.add_worksheet(sheet_title)
            OrdersProcessor.add_to_excel(ws, data_rows, row=0, col=0)
            _set_autowidth_columns(ws, data_rows)
            wb.close()
            output.seek(0)

            # ✅ убрали IN_PROGRESS из имени
            fname = f"{_safe_part(category_key)}_{suffix}.xlsx"
            return output, fname

        # если inner есть — делаем отдельный файл
        if rows_inner_p:
            data = start_rows_p + rows_inner_p
            files.append(_make_one_xlsx("РФ_ВНУТР", data, "РФ_ВНУТР"))

        # если outer есть — делаем отдельный файл
        if rows_outer_p:
            data = start_rows_p + rows_outer_p
            files.append(_make_one_xlsx("ВВЕЗЕН", data, "ВВЕЗЕН"))

        return files

    # ----------------------------
    # main
    # ----------------------------
    role = getattr(current_user, "role", None)
    manager_id = _get_manager_id_from_request()

    q = ProductCard.query.filter(ProductCard.status == ModerationStatus.IN_PROGRESS)

    # manager_id применяем ТОЛЬКО для manager
    if role == settings.MANAGER_USER:
        q = q.filter(ProductCard.manager_id == (manager_id or current_user.id))

    cards: list[ProductCard] = (
        q.options(joinedload(ProductCard.creator))
         .order_by(ProductCard.id.asc())
         .all()
    )

    if not cards:
        return _json_error("Нет карточек в статусе IN_PROGRESS", 404)

    # компании владельцев
    owner_ids = {c.user_id for c in cards if c.user_id}

    upc_rows: list[UserProcessingCompany] = (
        UserProcessingCompany.query
        .join(ProcessingCompany, UserProcessingCompany.company_id == ProcessingCompany.id)
        .filter(
            UserProcessingCompany.user_id.in_(owner_ids),
            UserProcessingCompany.is_approved.is_(True),
            ProcessingCompany.is_active.is_(True),
        )
        .options(joinedload(UserProcessingCompany.company))
        .all()
    )

    companies_by_user: dict[int, list[ProcessingCompany]] = {}
    for row in upc_rows:
        companies_by_user.setdefault(row.user_id, []).append(row.company)

    # разложение карточек по папкам компаний
    company_cards: dict[str, list[ProductCard]] = {}
    for card in cards:
        user = card.creator
        if not user:
            continue

        comps = companies_by_user.get(user.id) or []
        if not comps:
            folder = f"БЕЗ_КОМПАНИИ/{_safe_part(user.login_name or str(user.id))}"
            company_cards.setdefault(folder, []).append(card)
        else:
            for comp in comps:
                folder = f"{_safe_part(comp.inn)} {_safe_part(comp.title)}"
                company_cards.setdefault(folder, []).append(card)

    dt = datetime.now()
    dt_str = dt.strftime("%d.%m.%Y %H:%M")
    is_manager = (role in [settings.MANAGER_USER, settings.SUPER_MANAGER])

    outer_zip = BytesIO()
    wrote_anything = False

    try:
        with zipfile.ZipFile(outer_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for folder, cards_in_company in company_cards.items():
                by_cat: dict[str, list[tuple[int, list]]] = {}

                for card in cards_in_company:
                    cat_key = card.category
                    if cat_key not in CATEGORY_META:
                        continue

                    rel_name, _processor_cls, _headers_cat = CATEGORY_META[cat_key]
                    items = getattr(card, rel_name)  # rel_name из CATEGORIES_COMMON
                    by_cat.setdefault(cat_key, []).append((card.id, items))

                for cat_key, card_items in by_cat.items():
                    excel_files = _build_category_excels(cat_key, card_items, flag_046=False)

                    for xlsx_io, fname in excel_files:
                        xlsx_io.seek(0)
                        zf.writestr(f"{folder}/{fname}", xlsx_io.read())
                        wrote_anything = True

            # если менеджер — переводим статус и лог
            if is_manager:
                for card in cards:
                    card.status = ModerationStatus.IN_MODERATION
                    card.moderation_at = dt
                    card.card_log = h_append_card_log(
                        card.card_log,
                        f"\n{dt_str} карточка переведена на модерацию оператором {current_user.login_name};"
                    )

        outer_zip.seek(0)

        if not wrote_anything:
            # чтобы не скачивался пустой архив
            db.session.rollback()
            return _json_error(
                "Нечего выгружать: категории карточек не распознаны или данные пустые",
                422
            )

        if is_manager:
            db.session.commit()

    except Exception as e:
        db.session.rollback()
        return _json_error(f"Ошибка формирования архива: {e}", 500)

    filename = f"cards_in_progress_{dt.strftime('%Y%m%d_%H%M')}.zip"

    resp = send_file(
        outer_zip,
        mimetype="application/zip",
        as_attachment=True,
        download_name=filename,
    )

    # ✅ если переводили в модерацию — сообщаем фронту
    if is_manager:
        resp.headers["X-PC-Moved"] = "1"
        resp.headers["X-PC-Moved-From"] = ModerationStatus.IN_PROGRESS.value
        resp.headers["X-PC-Moved-To"] = ModerationStatus.IN_MODERATION.value

    return resp


def h_download_cards_companies_by_status():
    status_str = request.args.get("status")

    if not status_str:
        return jsonify(
            status="error",
            message="Не указан статус"
        ), 400

    try:
        status = ModerationStatus(status_str)
        if status == ModerationStatus.CREATED:
            raise ValueError()
    except ValueError:
        return jsonify(
            status="error",
            message="Некорректный статус"
        ), 400

    CATEGORY_META = {
        "shoes": (CATEGORIES_COMMON["shoes"]["rel_name"], ShoesProcessor, settings.Shoes.CATEGORY),
        "clothes": (CATEGORIES_COMMON["clothes"]["rel_name"], ClothesProcessor, settings.Clothes.CATEGORY),
        "socks": (CATEGORIES_COMMON["socks"]["rel_name"], SocksProcessor, settings.Socks.CATEGORY),
        "linen": (CATEGORIES_COMMON["linen"]["rel_name"], LinenProcessor, settings.Linen.CATEGORY),
        "parfum": (CATEGORIES_COMMON["parfum"]["rel_name"], ParfumProcessor, settings.Parfum.CATEGORY),
    }

    def _json_error(message: str, code: int = 400):
        return jsonify(status="error", message=message), code

    def _safe_part(s: str) -> str:
        s = (s or "").strip()
        for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
            s = s.replace(ch, "_")
        return s[:180]

    def _pad_rows(rows: list[list], width: int) -> list[list]:
        out = []
        for r in rows:
            r = list(r) if r is not None else []
            if len(r) < width:
                r = r + [""] * (width - len(r))
            elif len(r) > width:
                r = r[:width]
            out.append(r)
        return out

    def _set_autowidth_columns(worksheet, data: list[list]):
        if not data:
            return
        col_widths = {}
        for row in data:
            for c, cell in enumerate(row):
                ln = len(str(cell)) if cell is not None else 0
                col_widths[c] = max(col_widths.get(c, 0), ln)
        for c, w in col_widths.items():
            worksheet.set_column(c, c, min(w + 2, 80))

    def _build_category_excels(category_key: str, card_items: list[tuple[int, list]], *, flag_046: bool = False) -> list[tuple[BytesIO, str]]:
        rel_name, processor_cls, category_for_headers = CATEGORY_META[category_key]

        start_rows = OrdersProcessor.excel_start_data_ext(
            category=category_for_headers,
            flag_046=flag_046
        ) or []

        rows_outer, rows_inner = [], []

        for pc_id, items in card_items:
            if not items:
                continue

            _common, outer, inner = processor_cls.prepare_ext_data(
                orders_list=items,
                flag_046=flag_046,
                has_aggr=False,
            )

            if outer:
                rows_outer.extend([list(r) + [pc_id] for r in outer])
            if inner:
                rows_inner.extend([list(r) + [pc_id] for r in inner])

        if not rows_outer and not rows_inner:
            return []

        width = max([len(r) for r in (start_rows + rows_outer + rows_inner)] or [0])
        start_rows_p = _pad_rows(start_rows, width) if start_rows else []
        rows_outer_p = _pad_rows(rows_outer, width)
        rows_inner_p = _pad_rows(rows_inner, width)

        files: list[tuple[BytesIO, str]] = []

        def _make_one_xlsx(sheet_title: str, data_rows: list[list], suffix: str) -> tuple[BytesIO, str]:
            output = BytesIO()
            wb = Workbook(output)
            ws = wb.add_worksheet(sheet_title)
            OrdersProcessor.add_to_excel(ws, data_rows, row=0, col=0)
            _set_autowidth_columns(ws, data_rows)
            wb.close()
            output.seek(0)
            # ✅ без IN_PROGRESS в имени
            fname = f"{_safe_part(category_key)}_{suffix}.xlsx"
            return output, fname

        if rows_inner_p:
            files.append(_make_one_xlsx("РФ_ВНУТР", start_rows_p + rows_inner_p, "РФ_ВНУТР"))
        if rows_outer_p:
            files.append(_make_one_xlsx("ВВЕЗЕН", start_rows_p + rows_outer_p, "ВВЕЗЕН"))

        return files

    # --- main ---
    q = ProductCard.query.filter(ProductCard.status == status)

    # ограничение ТОЛЬКО для менеджера
    if current_user.role == settings.MANAGER_USER and status not in [ModerationStatus.SENT, ModerationStatus.SENT_NO_RD]:
        q = q.filter(ProductCard.manager_id == current_user.id)

    # (пока) правила доступа/фильтрации оставь как у вас принято.
    # Если нужно — потом добавите роли как обсуждали ранее.

    cards: list[ProductCard] = (
        q.options(joinedload(ProductCard.creator))
         .order_by(ProductCard.id.asc())
         .all()
    )
    if not cards:
        return _json_error(f"Нет карточек в статусе {status.value}", 404)

    owner_ids = {c.user_id for c in cards if c.user_id}

    upc_rows: list[UserProcessingCompany] = (
        UserProcessingCompany.query
        .join(ProcessingCompany, UserProcessingCompany.company_id == ProcessingCompany.id)
        .filter(
            UserProcessingCompany.user_id.in_(owner_ids),
            UserProcessingCompany.is_approved.is_(True),
            ProcessingCompany.is_active.is_(True),
        )
        .options(joinedload(UserProcessingCompany.company))
        .all()
    )

    companies_by_user: dict[int, list[ProcessingCompany]] = {}
    for row in upc_rows:
        companies_by_user.setdefault(row.user_id, []).append(row.company)

    company_cards: dict[str, list[ProductCard]] = {}
    for card in cards:
        user = card.creator
        if not user:
            continue

        comps = companies_by_user.get(user.id) or []
        if not comps:
            folder = f"БЕЗ_КОМПАНИИ/{_safe_part(user.login_name or str(user.id))}"
            company_cards.setdefault(folder, []).append(card)
        else:
            for comp in comps:
                folder = f"{_safe_part(comp.inn)} {_safe_part(comp.title)}"
                company_cards.setdefault(folder, []).append(card)

    dt = datetime.now()
    outer_zip = BytesIO()
    wrote_anything = False

    try:
        with zipfile.ZipFile(outer_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for folder, cards_in_company in company_cards.items():
                by_cat: dict[str, list[tuple[int, list]]] = {}

                for card in cards_in_company:
                    cat_key = card.category
                    if cat_key not in CATEGORY_META:
                        continue
                    rel_name, _processor_cls, _headers_cat = CATEGORY_META[cat_key]
                    items = getattr(card, rel_name)
                    by_cat.setdefault(cat_key, []).append((card.id, items))

                for cat_key, card_items in by_cat.items():
                    excel_files = _build_category_excels(cat_key, card_items, flag_046=False)
                    for xlsx_io, fname in excel_files:
                        xlsx_io.seek(0)
                        zf.writestr(f"{folder}/{fname}", xlsx_io.read())
                        wrote_anything = True

        outer_zip.seek(0)

        if not wrote_anything:
            return _json_error("Нечего выгружать: данные пустые", 422)

    except Exception as e:
        return _json_error(f"Ошибка формирования архива: {e}", 500)

    filename = f"cards_{status.value}_{dt.strftime('%Y%m%d_%H%M')}.zip"
    return send_file(
        outer_zip,
        mimetype="application/zip",
        as_attachment=True,
        download_name=filename,
    )


def h_crm_user_companies(user_id: int):
    # (опционально) доступ: только crm роли
    # if current_user.role not in {"manager", "supermanager", "superuser"}: ...

    rows = (
        UserProcessingCompany.query
        .options(joinedload(UserProcessingCompany.company))
        .filter(UserProcessingCompany.user_id == user_id)
        .order_by(UserProcessingCompany.slot.asc())
        .all()
    )

    companies = [{
        "slot": r.slot,
        "is_approved": bool(r.is_approved),
        "title": r.company.title if r.company else "",
        "inn": r.company.inn if r.company else "",
        "is_active": bool(r.company.is_active) if r.company else True,
    } for r in rows]

    html = render_template(
        "product_cards/crm/_user_companies_badges.html",
        companies=companies
    )
    return jsonify({"status": "success", "html": html, "count": len(companies)})


def h_pc_take_card_to_processing(pc_id: int):
    category = request.form.get("category") or None
    subcategory = request.form.get("subcategory") or None

    dt = datetime.now()
    dt_str = dt.strftime("%d-%m-%Y %H:%M:%S")
    manager_login = getattr(current_user, "login_name", "") or str(current_user.id)
    log_line = f"\n{dt_str} взял {manager_login};"

    try:
        # --- 1. Предварительная проверка карточки ---
        card = (
            ProductCard.query
            .filter(
                ProductCard.id == pc_id,
                ProductCard.manager_id.is_(None),
                ProductCard.status.in_([ModerationStatus.SENT, ModerationStatus.SENT_NO_RD]),
            )
            .first()
        )

        if not card:
            return json_response(
                message="Карточка уже взята в работу или не находится в статусах 'Отправлена' / 'Отправлена без РД'",
                status="error",
                code=400
            )

        from_status = card.status.value  # "sent" или "sent_no_rd"

        # --- 2. Проверка РД для SENT_NO_RD ---
        if card.status == ModerationStatus.SENT_NO_RD and not card_has_rd(card):
            return json_response(
                message="Нельзя взять карточку в работу: для статуса 'Отправлена без РД' необходимо добавить РД в карточку.",
                status="error",
                code=400
            )

        # --- 3. Атомарное обновление (защита от гонок) ---
        updated = (
            ProductCard.query
            .filter(
                ProductCard.id == pc_id,
                ProductCard.manager_id.is_(None),
                ProductCard.status.in_([ModerationStatus.SENT, ModerationStatus.SENT_NO_RD]),
            )
            .update(
                {
                    ProductCard.status: ModerationStatus.IN_PROGRESS,
                    ProductCard.manager_id: current_user.id,
                    ProductCard.taken_at: dt,
                    ProductCard.card_log: func.right(
                        func.coalesce(ProductCard.card_log, "") + log_line,
                        settings.ProducCards.MAX_LOG
                    ),
                },
                synchronize_session=False
            )
        )

        if updated != 1:
            return json_response(
                message="Карточку уже забрал другой оператор",
                status="error",
                code=409
            )

        db.session.commit()

        # --- 4. Перерендер колонок ---
        cards = crm_get_cards(category=category, subcategory=subcategory, user=current_user)
        buckets = split_cards_by_status(cards)

        sent_cards = buckets.get(ModerationStatus.SENT.value, [])
        sent_no_rd_cards = buckets.get(ModerationStatus.SENT_NO_RD.value, [])
        in_progress_cards = buckets.get(ModerationStatus.IN_PROGRESS.value, [])

        from_qty = len(sent_cards) if from_status == ModerationStatus.SENT.value else len(sent_no_rd_cards)

        if from_status == ModerationStatus.SENT.value:
            from_list_html = render_template(
                "product_cards/crm/cards/updated_stages/_sent_list.html",
                sent_cards=sent_cards,
                categories_common=CATEGORIES_COMMON,
            )
        else:
            from_list_html = render_template(
                "product_cards/crm/cards/updated_stages/_sent_no_rd_list.html",
                sent_no_rd_cards=sent_no_rd_cards,
                categories_common=CATEGORIES_COMMON,
            )

        to_list_html = render_template(
            "product_cards/crm/cards/updated_stages/_in_progress_list.html",
            in_progress_cards=in_progress_cards,
            categories_common=CATEGORIES_COMMON,
        )

        return json_response(
            status="success",
            message=f"Карточка №{pc_id} закреплена за оператором {manager_login}",

            from_status=from_status,
            from_qty=from_qty,
            from_list_html=from_list_html,

            to_status=ModerationStatus.IN_PROGRESS.value,
            to_qty=len(in_progress_cards),
            to_list_html=to_list_html,
        )

    except SQLAlchemyError:
        db.session.rollback()
        logger.exception("DB error in pc_take_card_to_processing")
        return json_response(message="Ошибка БД", status="error", code=500)

    except Exception:
        db.session.rollback()
        logger.exception("Unexpected error in pc_take_card_to_processing")
        return json_response(message="Неизвестная ошибка", status="error", code=500)


def h_companies_modal():
    companies = (ProcessingCompany.query
                 .order_by(ProcessingCompany.is_active.desc(), ProcessingCompany.id.desc())
                 .all())
    html = render_template("product_cards/crm/companies/modal.html", companies=companies)
    return jsonify({"status": "success", "html": html})


def h_companies_create():
    try:
        title = (request.form.get("title") or "").strip()
        inn = (request.form.get("inn") or "").strip()

        if not title:
            return jsonify({"status": "error", "message": "Укажите название фирмы"}), 400

        c = ProcessingCompany(title=title, inn=inn or None, is_active=True)
        db.session.add(c)
        db.session.commit()

        companies = ProcessingCompany.query.order_by(ProcessingCompany.is_active.desc(),
                                                     ProcessingCompany.id.desc()).all()
        table_html = render_template("product_cards/crm/companies/_table.html", companies=companies)

        return jsonify({"status": "success", "message": "Фирма добавлена", "table_html": table_html})

    except Exception:
        db.session.rollback()
        logger.exception("companies_create error")
        return jsonify({"status": "error", "message": "Ошибка добавления"}), 500


def h_companies_update(company_id: int):
    try:
        c = ProcessingCompany.query.get(company_id)
        if not c:
            return jsonify({"status": "error", "message": "Фирма не найдена"}), 404

        title = (request.form.get("title") or "").strip()
        inn = (request.form.get("inn") or "").strip()
        is_active = request.form.get("is_active")  # "1"/"0" or None

        if title:
            c.title = title
        c.inn = inn or None
        if is_active is not None:
            c.is_active = True if is_active in ("1", "true", "True", "on") else False

        db.session.commit()

        companies = ProcessingCompany.query.order_by(ProcessingCompany.is_active.desc(),
                                                     ProcessingCompany.id.desc()).all()
        table_html = render_template("product_cards/crm/companies/_table.html", companies=companies)

        return jsonify({"status": "success", "message": "Фирма обновлена", "table_html": table_html})

    except Exception:
        db.session.rollback()
        logger.exception("companies_update error")
        return jsonify({"status": "error", "message": "Ошибка обновления"}), 500


def h_companies_delete(company_id: int):
    try:
        ok, msg, meta = delete_company_from_pool_no_reassign(company_id)
        if not ok:
            return jsonify({"status": "error", "message": msg, **meta}), 400

        db.session.commit()

        companies = ProcessingCompany.query.order_by(ProcessingCompany.id.desc()).all()
        table_html = render_template("product_cards/crm/companies/_table.html", companies=companies)

        return jsonify({"status": "success", "message": msg, "table_html": table_html, **meta})

    except SQLAlchemyError:
        db.session.rollback()
        logger.exception("companies_delete db error")
        return jsonify({"status": "error", "message": "Ошибка БД"}), 500

    except Exception:
        db.session.rollback()
        logger.exception("companies_delete error")
        return jsonify({"status": "error", "message": "Ошибка удаления"}), 500


def h_pc_move_card(pc_id: int):
    target = (request.form.get("target") or "").strip()
    reject_reason = (request.form.get("reject_reason") or "").strip()

    # фильтры (протаскиваем!)
    category = (request.form.get("category") or "").strip() or None
    subcategory = (request.form.get("subcategory") or "").strip() or None

    def _dt():
        dt = datetime.now()
        return dt, dt.strftime("%d-%m-%Y %H:%M:%S")

    def _manager_login():
        return getattr(current_user, "login_name", "") or str(current_user.id)

    def _sq_key(card: ProductCard, sq) -> tuple:
        # ключ уникальности размера (как у тебя в extract_card_main_and_sizes)
        if card.category in (settings.Clothes.CATEGORY_PROCESS, settings.Socks.CATEGORY_PROCESS):
            return (sq.size, getattr(sq, "size_type", None))
        if card.category == settings.Linen.CATEGORY_PROCESS:
            return (sq.size, getattr(sq, "unit", None))
        # shoes
        return (sq.size,)

    def _iter_sqs(card: ProductCard):
        # отдаёт сами объекты sq (не dict)
        if card.category == settings.Clothes.CATEGORY_PROCESS:
            for c in card.clothes:
                for sq in c.sizes_quantities:
                    yield c, sq
        elif card.category == settings.Socks.CATEGORY_PROCESS:
            for s in card.socks:
                for sq in s.sizes_quantities:
                    yield s, sq
        elif card.category == settings.Shoes.CATEGORY_PROCESS:
            for sh in card.shoes:
                for sq in sh.sizes_quantities:
                    yield sh, sq
        elif card.category == settings.Linen.CATEGORY_PROCESS:
            for l in card.linen:
                for sq in l.sizes_quantities:
                    yield l, sq

    def _card_has_any_sizes(card: ProductCard) -> bool:
        for _, _sq in _iter_sqs(card):
            return True
        return False

    def _set_all_sizes_approved(card: ProductCard) -> None:
        for _, sq in _iter_sqs(card):
            if hasattr(sq, "is_approved"):
                sq.is_approved = True

    def _find_base_card_same_article(card: ProductCard):
        """
        Ищем базовую карточку ЭТОГО ЖЕ пользователя по article (+ subcategory для clothes),
        но только среди статусов APPROVED / PARTIALLY_APPROVED.
        Берём самую раннюю (created_at asc) — это будет "основная".
        """
        cfg = CATEGORIES_COMMON.get(card.category)
        if not cfg:
            return None

        model = cfg["model"]
        rel_name = cfg["rel_name"]

        items = getattr(card, rel_name) or []
        main = items[0] if items else None
        if not main or not getattr(main, "article", None):
            return None

        allowed_statuses = (
            ModerationStatus.APPROVED,
            ModerationStatus.PARTIALLY_APPROVED,
        )

        q = (
            db.session.query(ProductCard)
            .join(model, ProductCard.id == model.card_id)
            .filter(
                ProductCard.id != card.id,
                ProductCard.user_id == card.user_id,
                ProductCard.category == card.category,
                ProductCard.status.in_(allowed_statuses),
                model.article == main.article,
            )
            .order_by(ProductCard.created_at.asc())
        )

        if cfg.get("has_subcategory") and hasattr(model, "subcategory"):
            q = q.filter(model.subcategory == getattr(main, "subcategory", None))

        return q.first()

    def _merge_sizes_into_base_and_delete(card: ProductCard, base: ProductCard) -> int:
        """
        Переносим недостающие sizes_quantities из card в base.
        Перенос делаем APPEND в base_item.sizes_quantities (SQLAlchemy перевесит FK).
        Дубликаты (по ключу) из card удаляем, чтобы не плодить мусор.
        Возвращаем число ДОБАВЛЕННЫХ.
        """
        cfg = CATEGORIES_COMMON.get(base.category)
        if not cfg:
            return 0

        rel_name = cfg["rel_name"]
        base_items = getattr(base, rel_name) or []
        base_item = base_items[0] if base_items else None
        if not base_item:
            return 0

        # существующие ключи в базе
        base_keys = set()
        for _, sq in _iter_sqs(base):
            base_keys.add(_sq_key(base, sq))

        added = 0

        # переносим из card
        for parent_obj, sq in list(_iter_sqs(card)):  # list() чтобы безопасно менять коллекции
            k = _sq_key(card, sq)

            if k in base_keys:
                # такой размер уже есть в базе -> можно просто удалить sq из новой карточки
                # (чтобы при delete(card) не тащить дубль)
                db.session.delete(sq)
                continue

            # перенос: append на базовый parent
            base_item.sizes_quantities.append(sq)
            if hasattr(sq, "is_approved"):
                sq.is_approved = True

            base_keys.add(k)
            added += 1

        # добиваем approved на базе (на всякий)
        _set_all_sizes_approved(base)

        # если нужно, можно обновить статус базы (часто логично)
        # base.status = ModerationStatus.APPROVED
        # if not base.approved_at:
        #     base.approved_at = datetime.now()

        # удаляем карточку-источник
        db.session.delete(card)
        return added

    try:
        card = ProductCard.query.filter_by(id=pc_id).first()
        if not card:
            return jsonify({"status": "error", "message": "Карточка не найдена"}), 404

        from_status = card.status.value if hasattr(card.status, "value") else str(card.status)

        # SENT не двигаем этим методом
        if from_status in [ModerationStatus.SENT.value, ModerationStatus.SENT_NO_RD.value]:
            return jsonify({"status": "error", "message": "Карточка в 'Отправленные' берётся отдельной кнопкой"}), 400

        # 1) матрица переходов
        if not validate_transition(from_status, target):
            return jsonify({"status": "error", "message": f"Нельзя переместить из '{from_status}' в '{target}'"}), 400

        # 2) владелец / админ
        err = check_owner_or_admin(current_user, card)
        if err:
            return jsonify({"status": "error", "message": err.message}), err.status_code

        # 3) особые правила
        err = check_special_rules(current_user, card, target)
        if err:
            return jsonify({"status": "error", "message": err.message}), err.status_code

        # 4) меняем статус + тайминги + базовый лог
        try:
            h_pc_move_apply_status_transition(card, target, reject_reason=reject_reason)
        except PermissionError as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": str(e)}), 403
        except ValueError as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": str(e)}), 400

        # 5) спец-логика при APPROVED: merge sizes или approve sizes
        merge_info = None
        if target == ModerationStatus.APPROVED.value:
            # parfum: ничего не мерджим
            if card.category != settings.Parfum.CATEGORY_PROCESS:
                base = _find_base_card_same_article(card)

                # условие: "если по артикулу есть уже какие-то размеры" -> base существует и у неё есть размеры
                if base and _card_has_any_sizes(base):
                    dt, dt_str = _dt()
                    mgr = _manager_login()

                    added = _merge_sizes_into_base_and_delete(card, base)

                    # лог в base
                    base.card_log = h_append_card_log(
                        base.card_log,
                        f"\n{dt_str} добавлены размеры из карточки №{pc_id} (перенесено: {added}) оператором {mgr};"
                    )

                    # лог в card (успеваем записать до delete) — полезно для аудита
                    # card.card_log = h_append_card_log(
                    #     card.card_log,
                    #     f"\n{dt_str} карточка объединена с карточкой №{base.id} и удалена оператором {mgr};"
                    # )

                    merge_info = {"base_id": base.id, "added": added}
                else:
                    # нет base с размерами -> просто approve sizes на этой карточке
                    dt, dt_str = _dt()
                    mgr = _manager_login()

                    _set_all_sizes_approved(card)
                    card.card_log = h_append_card_log(
                        card.card_log,
                        f"\n{dt_str} все размеры помечены как одобренные оператором {mgr};"
                    )
            else:
                # parfum — если у юнитов есть is_approved, можно поставить
                for p in card.parfum:
                    if hasattr(p, "is_approved"):
                        p.is_approved = True

        db.session.commit()

        heavy = {
            ModerationStatus.APPROVED.value,
            ModerationStatus.REJECTED.value,
            ModerationStatus.PARTIALLY_APPROVED.value,
        }

        from_html, from_qty = h_pc_move_render_list_html(from_status, category=category, subcategory=subcategory)

        resp = {
            "status": "success",
            "from": from_status,
            "to": target,
            "from_qty": from_qty,
            "from_list_html": from_html,
            "to_is_heavy": (target in heavy),
        }

        if merge_info:
            resp["message"] = (
                f"Карточка объединена: размеры перенесены в карточку №{merge_info['base_id']} "
                f"(добавлено: {merge_info['added']}), текущая карточка удалена."
            )
            resp["merged_to_card_id"] = merge_info["base_id"]

        if target not in heavy:
            to_html, to_qty = h_pc_move_render_list_html(target, category=category, subcategory=subcategory)
            resp.update({
                "to_qty": to_qty,
                "to_list_html": to_html,
            })

        return jsonify(resp)

    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Ошибка БД"}), 500
    except Exception:
        db.session.rollback()
        logger.exception("pc_move_card error")
        return jsonify({"status": "error", "message": "Ошибка"}), 500


def h_pc_cards(pc_id: int):
    if current_user.role not in ('supermanager', 'markineris_admin', 'superuser') and not is_at2_admin_user(current_user):
        return jsonify(status="error", message="Нет доступа"), 403

    card = get_crm_card_for_user(pc_id, current_user)
    if not card:
        return jsonify(status="error", message="Карточка не найдена"), 404

    return jsonify(
        status="success",
        logs=card.card_log or ""
    )


def h_search_crm_card():
    mode = (request.form.get("search_mode") or "id").strip().lower()
    q = (request.form.get("q") or "").strip()

    allowed_statuses = {
        ModerationStatus.SENT.value,
        ModerationStatus.SENT_NO_RD.value,
        ModerationStatus.IN_PROGRESS.value,
        ModerationStatus.IN_MODERATION.value,
        ModerationStatus.CLARIFICATION.value,
        ModerationStatus.APPROVED.value,
        ModerationStatus.REJECTED.value,
        ModerationStatus.PARTIALLY_APPROVED.value,
    }

    # --- 1) Поиск по ID (как раньше) ---
    if mode == "id":
        if not q.isdigit():
            return jsonify(status="error", message="Введите номер карточки"), 400

        pc_id = int(q)

        card = (
            apply_crm_cards_scope(ProductCard.query, current_user)
            .options(joinedload(ProductCard.creator), joinedload(ProductCard.manager))
            .filter(ProductCard.id == pc_id)
            .first()
        )
        if not card:
            return jsonify(status="error", message=f"Карточка №{pc_id} не найдена"), 404

        st = card.status.value if hasattr(card.status, "value") else str(card.status)

        if st not in allowed_statuses:
            return jsonify(status="error", message="Карточка не находится в CRM-статусах"), 400

        if getattr(current_user, "role", None) == "manager":
            if st not in [ModerationStatus.SENT.value, ModerationStatus.SENT_NO_RD.value] and card.manager_id != current_user.id:
                return jsonify(status="error", message="Карточка закреплена за другим оператором"), 403

        tpl = h_pc_move_template_for_status(st)
        if not tpl:
            return jsonify(status="error", message="Шаблон статуса не найден"), 500

        packed = h_pc_move_pack_cards([card])
        one = packed[0]

        ctx = {"categories_common": CATEGORIES_COMMON}
        key = h_cards_ctx_key_for_status(st)
        if key:
            ctx[key] = [one]

        html = render_template(tpl, **ctx)

        return jsonify(
            status="success",
            found_count=1,
            html=(
                f"<div class='mb-2'><b>Статус:</b> "
                f"<u>{MODERATION_STATUS_TITLES.get(st, st)}</u></div>{html}"
            ),
        )

    # --- 2) Поиск по артикулу / trademark ---
    if mode == "article":
        if not q:
            return jsonify(status="error", message="Введите артикул или торговую марку"), 400

        ids = h_find_card_ids_by_article_or_tm(q)
        if not ids:
            return jsonify(status="error", message="Ничего не найдено"), 404

        cards = (
            apply_crm_cards_scope(ProductCard.query, current_user)
            .options(joinedload(ProductCard.creator), joinedload(ProductCard.manager))
            .filter(ProductCard.id.in_(ids))
            .all()
        )

        # фильтр CRM-статусов
        cards = [
            c for c in cards
            if (c.status.value if hasattr(c.status, "value") else str(c.status)) in allowed_statuses
        ]
        if not cards:
            return jsonify(status="error", message="Найденные карточки не находятся в CRM-статусах"), 400

        # права менеджера: SENT можно, остальное — только своё
        if getattr(current_user, "role", None) == settings.MANAGER_USER:
            filtered = []
            for c in cards:
                st = c.status.value if hasattr(c.status, "value") else str(c.status)
                if st in [ModerationStatus.SENT.value, ModerationStatus.SENT_NO_RD.value] or c.manager_id == current_user.id:
                    filtered.append(c)
            cards = filtered
            if not cards:
                return jsonify(status="error", message="Все найденные карточки закреплены за другими операторами"), 403

        packed = h_pc_move_pack_cards(cards)

        # группируем по статусам и рендерим блоками
        order = [
            ModerationStatus.SENT.value,
            ModerationStatus.SENT_NO_RD.value,
            ModerationStatus.IN_PROGRESS.value,
            ModerationStatus.IN_MODERATION.value,
            ModerationStatus.CLARIFICATION.value,
            ModerationStatus.APPROVED.value,
            ModerationStatus.REJECTED.value,
            ModerationStatus.PARTIALLY_APPROVED.value,
        ]

        by_status = {st: [] for st in order}
        for item in packed:
            by_status.setdefault(item["status"], []).append(item)

        chunks = []
        for st in order:
            items = by_status.get(st) or []
            if not items:
                continue

            tpl = h_pc_move_template_for_status(st)
            if not tpl:
                continue

            ctx = {"categories_common": CATEGORIES_COMMON}
            key = h_cards_ctx_key_for_status(st)
            if key:
                ctx[key] = items

            part_html = render_template(tpl, **ctx)
            title = MODERATION_STATUS_TITLES.get(st, st)

            chunks.append(
                f"<div class='crm-status-block'>"
                f"  <div class='mb-2'><b>Статус:</b> <u>{title}</u> "
                f"  <span class='text-muted'>({len(items)})</span></div>"
                f"  {part_html}"
                f"</div>"
            )

        html = (
            f"<div class='mb-2 text-muted'>"
            f"Поиск по артикулу/ТМ: <b>{q}</b>"
            f"</div>" + "".join(chunks)
        )

        return jsonify(status="success", found_count=len(packed), html=html)

    return jsonify(status="error", message="Некорректный режим поиска"), 400


def h_crm_set_company_slot(card_id: int):
    slot = request.form.get("slot", type=int)
    company_id = request.form.get("company_id", type=int)

    if slot not in (1, 2):
        return jsonify(status="error", message="Некорректный слот"), 400
    if not company_id:
        return jsonify(status="error", message="Не выбрана компания"), 400

    card = ProductCard.query.filter_by(id=card_id).first()
    if not card:
        return jsonify(status="error", message="Карточка не найдена"), 404

    if card.status != ModerationStatus.PARTIALLY_APPROVED:
        return jsonify(status="error", message="Менять компании можно только в PARTIALLY_APPROVED"), 403

    if current_user.role not in {"manager", "supermanager", "superuser"}:
        return jsonify(status="error", message="Недостаточно прав"), 403

    comp = ProcessingCompany.query.filter_by(id=company_id, is_active=True).first()
    if not comp:
        return jsonify(status="error", message="Компания не найдена или не активна"), 400

    try:
        row = (UserProcessingCompany.query
               .options(joinedload(UserProcessingCompany.company))
               .filter_by(user_id=card.user_id, slot=slot)
               .first())

        # ✅ если слот уже заполнен активной компанией — запрещаем менять
        if row and row.company and row.company.is_active:
            return jsonify(status="error", message="Этот слот уже заполнен. Изменение запрещено."), 400

        # если эта компания уже стоит в другом слоте — запрещаем (чтобы не было дубля)
        other = (UserProcessingCompany.query
                 .filter(UserProcessingCompany.user_id == card.user_id,
                         UserProcessingCompany.company_id == company_id)
                 .first())
        if other:
            return jsonify(status="error", message="Эта компания уже закреплена в другом слоте"), 400

        # ✅ запрет на запрещённые сочетания компаний (по ИНН) между слотами 1/2
        other_slot = 2 if slot == 1 else 1
        other_row = (UserProcessingCompany.query
                     .options(joinedload(UserProcessingCompany.company))
                     .filter(UserProcessingCompany.user_id == card.user_id,
                             UserProcessingCompany.slot == other_slot)
                     .first())

        if other_row and other_row.company:
            if is_forbidden_pair_by_inn(other_row.company.inn, comp.inn):
                return jsonify(
                    status="error",
                    message=f"Нельзя ставить вместе: '{other_row.company.title}' и '{comp.title}'."
                ), 400

        if row:
            row.company_id = company_id
            row.is_approved = True

        else:
            db.session.add(UserProcessingCompany(
                user_id=card.user_id,
                slot=slot,
                company_id=company_id,
                is_approved=True,
            ))

        # лог
        dt = datetime.now()
        mgr = getattr(current_user, "login_name", "") or str(current_user.id)
        card.card_log = h_append_card_log(
            card.card_log,
            f"\n{dt:%d-%m-%Y %H:%M:%S} добавил компанию в слот {slot}: '{comp.title}' ({comp.inn}) оператор {mgr};"
        )

        db.session.commit()

        # пересобираем блок
        user_companies_rows = (
            UserProcessingCompany.query
            .options(joinedload(UserProcessingCompany.company))
            .filter(UserProcessingCompany.user_id == card.user_id)
            .order_by(UserProcessingCompany.slot.asc())
            .all()
        )
        user_companies = []
        by_slot = {}
        for r in user_companies_rows:
            c = r.company
            item = {
                "slot": r.slot,
                "company_id": r.company_id,
                "is_approved": bool(r.is_approved),
                "title": c.title if c else "",
                "inn": c.inn if c else "",
                "is_active": bool(c.is_active) if c else True,
            }
            user_companies.append(item)
            by_slot[r.slot] = item

        slot1_filled = bool(by_slot.get(1) and by_slot[1].get("company_id"))
        slot2_filled = bool(by_slot.get(2) and by_slot[2].get("company_id"))

        pool_companies = (ProcessingCompany.query
                          .filter(ProcessingCompany.is_active.is_(True))
                          .order_by(ProcessingCompany.title.asc())
                          .all())

        html = render_template(
            "product_cards/user/helpers/_card_view_companies_block.html",
            user_companies=user_companies,
            pool_companies=pool_companies,
            can_edit_companies=True,
            card=card,
            slot1_filled=slot1_filled,
            slot2_filled=slot2_filled,
        )

        return jsonify(status="success", html=html)

    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(status="error", message="Ошибка БД при сохранении"), 500


def h_crm_approve_from_partially(card_id: int):
    def _slot_ok(s: int):
        r = by_slot.get(s)
        return bool(r and r.company and r.company.is_active)

    card = ProductCard.query.filter_by(id=card_id).first()
    if not card:
        return jsonify(status="error", message="Карточка не найдена"), 404

    if card.status != ModerationStatus.PARTIALLY_APPROVED:
        return jsonify(status="error", message="Действие доступно только в PARTIALLY_APPROVED"), 400

    if current_user.role not in {"manager", "supermanager", "superuser"}:
        return jsonify(status="error", message="Недостаточно прав"), 403

    # ✅ проверяем слоты пользователя карточки
    rows = (UserProcessingCompany.query
            .options(joinedload(UserProcessingCompany.company))
            .filter(UserProcessingCompany.user_id == card.user_id,
                    UserProcessingCompany.slot.in_([1,2]))
            .all())

    by_slot = {r.slot: r for r in rows}

    if not _slot_ok(1) or not _slot_ok(2):
        return jsonify(status="error", message="Нельзя перевести в APPROVED: заполните оба слота компаний"), 400

    dt = datetime.now()
    for s in (1, 2):
        r = by_slot[s]
        r.is_approved = True
        r.approved_at = dt

    try:
        h_pc_move_apply_status_transition(card, ModerationStatus.APPROVED.value)

        mgr = getattr(current_user, "login_name", "") or str(current_user.id)
        card.card_log = h_append_card_log(
            card.card_log,
            f"\n{dt:%d-%m-%Y %H:%M:%S} подтвердил компании (2 слота) и перевёл в APPROVED {mgr};"
        )

        db.session.commit()
        return jsonify(status="success", message=f"Карточка №{card.id} переведена в APPROVED")

    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(status="error", message="Ошибка БД"), 500


def h_crm_reject_cards_by_rd_today():
    try:
        res = helper_reject_cards_by_rd_date_to_today()
        return jsonify(res), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(status="error", message=str(e)), 500
