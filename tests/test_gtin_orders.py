"""GTIN grouping runs against an isolated SQLite database, without application services."""
import ast
import json
from copy import copy
from datetime import datetime
from enum import Enum
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, create_engine, select
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, lazyload, selectinload

ROOT = Path(__file__).resolve().parents[1]


def load_function(path, name, namespace, class_name=None):
    nodes = ast.parse((ROOT / path).read_text()).body
    if class_name:
        nodes = next(node for node in nodes if isinstance(node, ast.ClassDef) and node.name == class_name).body
    node = next(node for node in nodes if isinstance(node, ast.FunctionDef) and node.name == name)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), path, 'exec'), namespace)
    return namespace[name]


schema = ast.parse((ROOT / 'app/views/crm/schema.py').read_text())
company_enum = next(node for node in schema.body if isinstance(node, ast.ClassDef) and node.name == 'CompaniesOperators')
enum_namespace = {'Enum': Enum}
exec(compile(ast.Module(body=[company_enum], type_ignores=[]), 'schema.py', 'exec'), enum_namespace)
namespace = {}
with patch.dict('sys.modules', {'views.crm.schema': NS(CompaniesOperators=enum_namespace['CompaniesOperators'])}):
    exec(compile((ROOT / 'app/utilities/gtin_orders.py').read_text(), 'gtin_orders.py', 'exec'), namespace)

Base = declarative_base()


class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    stage = Column(Integer, default=0)
    processed = Column(Boolean, default=False)
    to_delete = Column(Boolean, default=False)
    order_idn = Column(String, unique=True)
    user_id = Column(Integer)
    category = Column(String, default='одежда')
    is_moderation = Column(Boolean, default=False)
    is_gtin_order = Column(Boolean, default=False)
    company_idn = Column(String)
    company_type = Column(String)
    company_name = Column(String)
    edo_type = Column(String)
    edo_id = Column(String)
    mark_type = Column(String)
    rd_replacement_consent = Column(Boolean)
    created_at = Column(DateTime, default=datetime.now)
    processing_company_key = Column(String)
    processing_company_label = Column(String)
    processing_info = Column(String)
    upd_number = Column(String)
    clothes = relationship('Position', back_populates='order', cascade='all,delete')


class Position(Base):
    __tablename__ = 'positions'
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    order = relationship(Order, back_populates='clothes')
    gtin = Column(String)
    gtin_company_key = Column(String)
    quantity = Column(Integer, default=2)
    weight_grams = Column(Integer, default=100)
    sizes_quantities = relationship('Size', back_populates='clothes', cascade='all,delete')


class Size(Base):
    __tablename__ = 'sizes'
    id = Column(Integer, primary_key=True)
    position_id = Column(Integer, ForeignKey('positions.id'))
    clothes = relationship(Position, back_populates='sizes_quantities')
    size = Column(String)
    size_type = Column(String, default='РОССИЯ')
    quantity = Column(Integer)
    gtin = Column(String)
    gtin_company_key = Column(String)


class GtinOrderTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.models_patch = patch.dict('sys.modules', {'models': NS(Order=Order, db=NS(session=self.session))})
        self.models_patch.start()

    def tearDown(self):
        self.models_patch.stop()
        self.session.close()
        self.engine.dispose()

    def draft(self, keys):
        order = Order(user_id=4, company_name='Клиент',
                      company_type='ИП', company_idn='123456789012', rd_replacement_consent=True)
        order.clothes = [Position(gtin=({'g:GRENADA': '04640735105562', 'g:AVRORA': '04640735105579'}.get(key)),
                                  gtin_company_key=key) for key in keys]
        self.session.add(order)
        self.session.commit()
        return order

    def size_draft(self):
        order = Order(user_id=4, company_name='Клиент')
        position = Position(weight_grams=101)
        position.sizes_quantities = [
            Size(size='42', quantity=2, gtin='04640735105562', gtin_company_key='g:GRENADA'),
            Size(size='44', quantity=3, gtin='04640735105579', gtin_company_key='g:AVRORA'),
            Size(size='46', quantity=5),
            Size(size='48', quantity=1, gtin='04640735105586', gtin_company_key='g:GRENADA'),
        ]
        order.clothes = [position]
        self.session.add(order)
        self.session.commit()
        return order

    def test_partial_size_gtins_split_by_company_preserves_size_ids_quantity_and_weight(self):
        order = self.size_draft()
        original_ids = {sq.id for sq in order.clothes[0].sizes_quantities}
        result = namespace['split_order'](order, 'clothes')
        self.session.commit()
        self.assertEqual([row.processing_company_key for row in result], ['g:GRENADA', 'g:AVRORA', None])
        self.assertEqual([len(row.clothes) for row in result], [2, 1, 1])
        all_positions = [position for row in result for position in row.clothes]
        self.assertEqual(sum(position.weight_grams for position in all_positions), 101)
        self.assertEqual(sum(sq.quantity for position in all_positions for sq in position.sizes_quantities), 11)
        self.assertEqual({sq.id for position in all_positions for sq in position.sizes_quantities}, original_ids)
        for position in all_positions:
            sq, = position.sizes_quantities
            self.assertEqual(position.gtin or '', sq.gtin or '')
            self.assertEqual(position.gtin_company_key or '', sq.gtin_company_key or '')

    def test_size_split_rollback_restores_original_position(self):
        order = self.size_draft()
        namespace['split_order'](order, 'clothes')
        self.session.rollback()
        self.assertEqual(self.session.query(Order).count(), 1)
        self.assertEqual(len(order.clothes), 1)
        self.assertEqual(len(order.clothes[0].sizes_quantities), 4)
        self.assertEqual(order.clothes[0].weight_grams, 101)
        self.assertIsNone(order.clothes[0].gtin)



    def test_merging_multiple_new_sizes_moves_every_size_with_its_metadata(self):
        order = self.draft([None])
        existing = order.clothes[0]
        existing.sizes_quantities = [Size(size='42', quantity=2)]
        incoming = Position(sizes_quantities=[
            Size(size='44', quantity=3, gtin='04640735105562', gtin_company_key='g:GRENADA'),
            Size(size='46', quantity=4, gtin='04640735105579', gtin_company_key='g:AVRORA')])
        context = dict(Any=object, build_size_key=lambda sq, category: (sq.size,), normalize_int_key=lambda value: int(value or 0))
        merge = load_function('app/utilities/saving_helpers.py', 'merge_size_quantities', context)
        merge(existing, incoming, 'clothes')
        self.session.commit()
        self.assertEqual([sq.size for sq in existing.sizes_quantities], ['42', '44', '46'])
        self.assertEqual([sq.gtin for sq in existing.sizes_quantities], [None, '04640735105562', '04640735105579'])
        self.assertEqual(sum(sq.quantity for sq in existing.sizes_quantities), 9)

    def test_size_gtin_conflicts_are_checked_against_other_positions(self):
        order = self.size_draft()
        with self.assertRaises(namespace['GTINCompanyConflict']):
            namespace['validate_gtin_company'](order.clothes, '04640735105562', 'g:AVRORA')

    def test_size_mapping_validation_and_normalized_size_types(self):
        parse = namespace['parse_size_gtins']
        rows = [dict(size='42', size_type='РОССИЯ', gtin='04640735105562', company='g:GRENADA'),
                dict(size='44', size_type='ОСОБЫЕ_РАЗМЕРЫ', gtin='', company='')]
        mapping = parse(json.dumps(rows))
        self.assertEqual(mapping[('42', 'РОССИЯ', '')], ('04640735105562', 'g:GRENADA'))
        position = NS(gtin=None, gtin_company_key=None, sizes_quantities=[
            NS(size='42', size_type='РОССИЯ'), NS(size='44', size_type='МЕЖДУНАРОДНЫЙ')])
        namespace['apply_size_gtins'](position, json.dumps(rows), [('42', 2, 'РОССИЯ'), ('44', 3, 'ОСОБЫЕ_РАЗМЕРЫ')])
        self.assertEqual(position.sizes_quantities[0].gtin, '04640735105562')
        self.assertEqual(position.sizes_quantities[1].gtin, '')
        with self.assertRaises(namespace['GTINSizeValidationError']):
            namespace['apply_size_gtins'](position, json.dumps(rows[:1]), [('42', 2, 'РОССИЯ'), ('44', 3, 'ОСОБЫЕ_РАЗМЕРЫ')])
        invalid = [dict(rows[0], company=''), dict(rows[0], gtin=''), dict(rows[0], gtin='123'),
                   dict(rows[0], company='g:UNKNOWN')]
        for row in invalid:
            with self.subTest(row=row), self.assertRaises(namespace['GTINSizeValidationError']):
                parse(json.dumps([row]))
        for raw in ('null', '{}', '[1]', '{', json.dumps([rows[0], rows[0]]),
                    json.dumps([rows[0], dict(rows[0], size='44')])):
            with self.subTest(raw=raw), self.assertRaises(namespace['GTINSizeValidationError']):
                parse(raw)

    def test_category_savers_attach_gtins_to_sizes_and_keep_ordinary_sizes(self):
        settings = NS(**{name: NS(CATEGORY=name.lower()) for name in ('Shoes', 'Clothes', 'Socks', 'Linen')})
        settings.Linen.KPB_TYPE = 'КОМПЛЕКТ ПОСТЕЛЬНОГО БЕЛЬЯ'
        def position_factory(**kwargs):
            fields = dict(sizes_quantities=[], set_items=[])
            fields.update(kwargs)
            return NS(**fields)
        context = dict(Order=Order, settings=settings, datetime=datetime,
                       normalize_article_placeholder=lambda value: value,
                       normalize_clothes_type_for_subcategory=lambda value, category: value,
                       process_input_str=lambda value: value, rd_name_clean=lambda value: value,
                       ClothesSubcategories=NS(common=NS(value='common')),
                       get_clothes_size_type=lambda *args, **kwargs: 'NORMALIZED',
                       get_socks_size_type=lambda *args: 'NORMALIZED',
                       validate_gtin_fields=namespace['validate_gtin_fields'],
                       apply_size_gtins=namespace['apply_size_gtins'],
                       append_or_merge_position=lambda positions, position, category, **kwargs: positions.append(position),
                       AggrOrder=object, normalize_trademark_placeholder=lambda value: value,
                       normalize_length_width_size_type=lambda value: value,
                       normalize_length_width_size_value=lambda value, kind: value,
                       validate_clothes_size_type_for_subcategory=lambda *args: None,
                       SizeTypeException=ValueError, _copy_pc_approval_flag=lambda *args: False,
                       _check_shoes_compatibility=lambda value: None, _check_clothes_compatibility=lambda value: None,
                       _check_socks_compatibility=lambda value: None, _check_linen_compatibility=lambda value: None,
                       Shoe=position_factory, Clothes=position_factory, Socks=position_factory, Linen=position_factory,
                       ShoeQuantitySize=NS, ClothesQuantitySize=NS, SocksQuantitySize=NS, LinenQuantitySize=NS)
        for category in ('shoes', 'clothes', 'socks', 'linen'):
            with self.subTest(category=category):
                raw_sizes = [('100*200', 'см', 2), ('120*200', 'см', 3)] if category == 'linen' else (
                    [('42', 2), ('44', 3)] if category == 'shoes' else [('42', 2, 'РОССИЯ'), ('44', 3, 'ОСОБЫЕ_РАЗМЕРЫ')])
                rows = [dict(size=row[0],
                             size_type=row[2] if category in ('clothes', 'socks') else '',
                             unit=row[1] if category == 'linen' else '',
                             gtin='04640735105562' if index == 0 else '',
                             company='g:GRENADA' if index == 0 else '') for index, row in enumerate(raw_sizes)]
                form = dict(weight_grams=100, article='A1', type='ТОВАР', content='ХЛОПОК', rd_name='', size_gtins=json.dumps(rows))
                order = NS(**{category: []})
                save = load_function('app/utilities/saving_uts.py', 'save_' + category, context)
                self.assertIs(save(order, form, raw_sizes), order)
                position, = getattr(order, category)
                self.assertIsNone(position.gtin)
                self.assertIsNone(position.gtin_company_key)
                self.assertEqual(position.sizes_quantities[0].gtin, '04640735105562')
                self.assertEqual(position.sizes_quantities[0].gtin_company_key, 'g:GRENADA')
                self.assertEqual(position.sizes_quantities[1].gtin, '')
                self.assertEqual(position.sizes_quantities[1].gtin_company_key, '')
                self.assertEqual([sq.quantity for sq in position.sizes_quantities], [2, 3])
                position.fast_order_company_id = None
                for index, sq in enumerate(position.sizes_quantities):
                    sq.id = index + 1
                target = NS(**{category: []})
                copier = load_function('app/utilities/saving_uts.py', 'save_copy_order_' + category, context)
                self.assertIs(copier([position], target), target)
                copied, = getattr(target, category)
                self.assertEqual([(sq.size, sq.quantity, sq.gtin, sq.gtin_company_key) for sq in copied.sizes_quantities],
                                 [(sq.size, sq.quantity, sq.gtin, sq.gtin_company_key) for sq in position.sizes_quantities])

    def test_fields_are_paired_and_only_catalog_companies_are_accepted(self):
        validate = namespace['validate_gtin_fields']
        self.assertEqual(validate(None, None), ('', ''))
        self.assertEqual(validate(' 04640735105562 ', 'g:GRENADA'), ('04640735105562', 'g:GRENADA'))
        for gtin, key in [('123', 'g:GRENADA'), ('１２３４５６７８', 'g:GRENADA'),
                          ('0464073510556', 'g:GRENADA'), ('046407351055620', 'g:GRENADA'),
                          ('14640735105562', 'g:GRENADA'), ('46040735105562', 'g:GRENADA'),
                          ('0464073510556a', 'g:GRENADA'), ('046４０７３５１０５５６２', 'g:GRENADA'),
                          ('04640735105562', ''), ('', 'g:GRENADA'), ('04640735105562', 'g:UNKNOWN')]:
            with self.subTest(gtin=gtin, company=key), self.assertRaises(ValueError):
                validate(gtin, key)

    def test_same_gtin_requires_same_company_before_saving_any_position(self):
        order = self.draft(['g:GRENADA'])
        saved = []
        settings = NS(CATEGORIES_DICT={'одежда': 'clothes'},
                      **{name: NS(CATEGORY='одежда' if name == 'Clothes' else name.lower())
                         for name in ('Shoes', 'Clothes', 'Socks', 'Linen', 'Parfum', 'Cosmetics', 'Toys')})
        context = dict(Order=Order, settings=settings, validate_gtin_fields=namespace['validate_gtin_fields'],
                       validate_gtin_company=namespace['validate_gtin_company'], parse_size_gtins=namespace['parse_size_gtins'],
                       save_clothes=lambda **kwargs: saved.append(kwargs) or kwargs['order'])
        save = load_function('app/utilities/saving_uts.py', 'common_save_db', context)
        form = dict(gtin='04640735105562', gtin_company_key='g:AVRORA', weight_grams='100')
        with self.assertRaises(namespace['GTINCompanyConflict']) as error:
            save(order, form.copy(), 'одежда')
        self.assertIn('04640735105562', str(error.exception))
        self.assertIn('ту же проводящую компанию', str(error.exception))
        self.assertEqual(saved, [])
        self.assertEqual(len(order.clothes), 1)
        form['gtin_company_key'] = 'g:GRENADA'
        self.assertIs(save(order, form.copy(), 'одежда'), order)
        self.assertEqual(len(saved), 1)
        # The restriction applies to this order only, and different GTINs remain independent.
        other_order = self.draft(['g:AVRORA'])
        form['gtin_company_key'] = 'g:AVRORA'
        self.assertIs(save(other_order, form.copy(), 'одежда'), other_order)
        form['gtin'] = '04640735105579'
        self.assertIs(save(order, form.copy(), 'одежда'), order)

    def test_conflict_is_reported_in_ajax_and_edit_form(self):
        from typing import Union
        flashed = []
        settings = NS(CATEGORIES_DICT={'toys': 'toys'},
                      **{name: NS(CATEGORY=name.lower(), CATEGORY_PROCESS=name.lower())
                         for name in ('Shoes', 'Clothes', 'Socks', 'Linen', 'Parfum', 'Cosmetics', 'Toys')})
        def reject(**kwargs):
            raise namespace['GTINCompanyConflict']('04640735105562')
        context = dict(Union=Union, Response=object, settings=settings,
                       GTINCompanyConflict=namespace['GTINCompanyConflict'], GTINSizeValidationError=namespace['GTINSizeValidationError'], current_user=NS(id=4),
                       request=NS(form=dict(gtin='04640735105562', gtin_company_key='g:AVRORA'),
                                  args={}, view_args={'subcategory': 'common'}),
                       Category=NS(check_subcategory=lambda **kwargs: True),
                       trademark_matches_product_type=lambda *args: False,
                       ValidatorProcessor=NS(check_tnveds=lambda **kwargs: False,
                                             validate_toys_subcategory_payload=lambda **kwargs: None),
                       preprocess_order_common=reject,
                       jsonify=lambda **kwargs: kwargs,
                       flash=lambda **kwargs: flashed.append(kwargs),
                       url_for=lambda endpoint, **kwargs: (endpoint, kwargs), redirect=lambda url: url)
        route = load_function('app/utilities/support.py', 'preprocess_order_category', context)
        with patch.dict('sys.modules', {'utilities.gtin_orders': NS(**namespace)}):
            response = route(1, None, 'toys')
            self.assertEqual(response['status'], 'error')
            self.assertIn('04640735105562', response['message'])
            self.assertEqual(flashed, [])
            target, kwargs = route(1, 2, 'toys')
            self.assertEqual(target, 'toys.index')
            self.assertEqual(kwargs['o_id'], 1)
            self.assertEqual(flashed[0]['category'], 'warning')
            self.assertIn('04640735105562', flashed[0]['message'])

    def test_checkout_rejects_previously_saved_conflicting_gtin(self):
        order = self.draft(['g:GRENADA', 'g:AVRORA'])
        order.clothes[1].gtin = order.clothes[0].gtin
        self.session.commit()
        with self.assertRaises(namespace['GTINCompanyConflict']):
            namespace['split_order'](order, 'clothes')
        self.assertEqual(self.session.query(Order).count(), 1)
        self.assertEqual(len(order.clothes), 2)
        self.assertFalse(order.is_gtin_order)

    def test_mixed_order_becomes_three_orders_and_preserves_positions(self):
        order = self.draft(['g:GRENADA', None, 'g:AVRORA', 'g:GRENADA', None])
        original_ids = sorted(item.id for item in order.clothes)
        result = namespace['split_order'](order, 'clothes')
        self.session.commit()
        self.assertEqual([len(item.clothes) for item in result], [2, 2, 1])
        self.assertEqual([item.is_gtin_order for item in result], [True, False, True])
        self.assertEqual(sorted(item.id for row in result for item in row.clothes), original_ids)
        self.assertEqual(sum(item.quantity for row in result for item in row.clothes), 10)
        self.assertEqual(sum(item.weight_grams for row in result for item in row.clothes), 500)
        self.assertTrue(all(row.user_id == 4 and row.rd_replacement_consent for row in result))
        self.assertIn('Гренада', result[0].processing_company_label)
        self.assertIsNone(result[1].processing_company_key)
        self.assertTrue(all(not row.upd_number for row in result))

    def test_ordinary_or_single_company_does_not_create_empty_orders(self):
        for keys in [[None, None], ['g:AVRORA', 'g:AVRORA']]:
            order = self.draft(keys)
            self.assertEqual(namespace['split_order'](order, 'clothes'), [order])

    def test_failure_rolls_back_split_and_keeps_draft(self):
        order = self.draft(['g:GRENADA', None, 'g:AVRORA'])
        namespace['split_order'](order, 'clothes')
        self.session.rollback()
        self.assertEqual(self.session.query(Order).count(), 1)
        self.assertEqual(len(order.clothes), 3)
        self.assertFalse(order.is_gtin_order)



    def test_submission_saves_every_order_or_rolls_back_every_order(self):
        for keys, fail in ((['g:GRENADA', None, 'g:AVRORA'], False),
                           (['g:GRENADA', None, 'g:AVRORA'], True),
                           ([None], False), (['g:GRENADA'], False)):
            with self.subTest(keys=keys, fail=fail):
                order = self.draft(keys)
                for relation in ('shoes', 'socks', 'linen', 'parfum', 'cosmetics', 'toys'):
                    setattr(Order, relation, property(lambda self: []))
                calls = []
                notifications = []
                messages = []
                user = NS(id=4, is_at2=False)
                settings = NS(CATEGORIES_DICT={'одежда': 'clothes'}, CLIENT_MARK_QUANTITY=100,
                              OrderStage=NS(CREATING=0),
                              Messages=NS(PROCESS_SUCCESS='Оформлен ', ORDER_ADD_ERROR='Ошибка'),
                              **{name: NS(CATEGORY=name.lower() if name != 'Clothes' else 'одежда')
                                 for name in ('Shoes', 'Clothes', 'Socks', 'Linen', 'Parfum', 'Cosmetics', 'Toys')})
                def start(**kwargs):
                    calls.append(kwargs['order_idn'])
                    if fail and len(calls) == 2:
                        raise ValueError('failure')
                    row = self.session.get(Order, kwargs['o_id'])
                    row.order_idn = kwargs['order_idn']
                    row.stage = 1
                    return 1
                context = dict(__name__="utilities.support", __package__="utilities", Order=Order, User=object, Response=object, settings=settings, select=select,
                               db=NS(session=self.session), current_user=user,
                               request=NS(form={}), get_subcategory=lambda **kwargs: 'common',
                               flash=lambda *args, **kwargs: messages.append(kwargs), redirect=lambda value: value,
                               url_for=lambda endpoint, **kwargs: endpoint, Markup=str,
                               validate_order_comment_length=lambda **kwargs: True,
                               validate_and_build_contact_info=lambda *args: (True, 'contact', ''),
                               order_has_user_rd=lambda order: False,
                               parse_rd_replacement_consent=lambda *args, **kwargs: None,
                               validate_and_normalize_company_fields=lambda *args: (True, dict(company_type=args[0], company_name=args[1], company_idn=args[2]), ''),
                               ExceptionDataUsers=NS(get_company_idns=lambda: []),
                               check_order_pos=lambda **kwargs: True,
                               get_rows_marks=lambda **kwargs: (3, 6),
                               ValidatorProcessor=NS(validate_aggr_order_completeness=lambda **kwargs: True),
                               helper_check_uoabm=lambda **kwargs: (1, 0, False, ''),
                               process_order_start=start,
                               helper_send_user_order_tg_notify=lambda **kwargs: notifications.append(kwargs['order_idn']),
                               MarkinerisInform=NS(send_message_tg=NS(delay=lambda **kwargs: None)),
                               logger=NS(exception=lambda *args: None))
                context.update(lazyload=lazyload, selectinload=selectinload)
                load_function('app/utilities/support.py', 'category_order_load_options', context)
                submit = load_function('app/utilities/support.py', 'helper_process_category_order', context)
                modules = {'utilities.download': NS(orders_process_send_order=lambda **kwargs: None),
                           'utilities.gtin_orders': NS(split_order=namespace['split_order'],
                                                       reserve_order_numbers=lambda user, count: [f'{order.id}_{n}' for n in range(count)]),
                           'unused_port_placeholder': NS()}
                with patch.dict('sys.modules', modules):
                    submit(user, order, 'одежда', '')
                if fail:
                    self.assertEqual(order.stage, 0)
                    self.assertEqual(len(order.clothes), 3)
                    self.assertEqual(notifications, [])
                    self.assertTrue(all('успешно оформлены' not in item['message'] for item in messages))
                else:
                    rows = self.session.query(Order).filter(Order.order_idn.in_(calls)).all()
                    self.assertEqual(len(rows), len(keys))
                    self.assertEqual(notifications, calls)
                    self.assertEqual(len(messages), 1)
                    message = messages[0]['message']
                    for number in calls:
                        self.assertIn(f'<b>{number}</b>', message)
                    if len(keys) > 1:
                        self.assertIn('Заказ разделён на несколько заказов', message)
                        self.assertIn(f'всего: {len(keys)}', message)
                        self.assertIn('Номера заказов:', message)
                    else:
                        self.assertEqual(message, f'{settings.Messages.PROCESS_SUCCESS}<b>{calls[0]}</b>!')
                self.session.rollback()

    def test_copying_identical_gtin_position_sums_sizes_and_weight(self):
        settings = NS(**{name: NS(CATEGORY=name.lower()) for name in
                         ('Shoes', 'Clothes', 'Socks', 'Linen', 'Parfum', 'Cosmetics', 'Toys')})
        ns = dict(Any=object, settings=settings, normalize_placeholder_value=lambda value, *args: value,
                  normalize_key_value=lambda value: value or '', normalize_float_key=lambda value: value,
                  normalize_int_key=lambda value: int(value or 0), NO_TRADEMARK_PLACEHOLDERS=(),
                  NO_TRADEMARK_VALUE='', NO_ARTICLE_PLACEHOLDERS=(), NO_ARTICLE_VALUE='')
        for name in ('build_position_key', 'build_size_key', 'merge_size_quantities', 'append_or_merge_position'):
            load_function('app/utilities/saving_helpers.py', name, ns)
        def position(company='g:GRENADA', gtin='04640735105562'):
            return NS(trademark='Тест', article='A1', tnved_code='6403990000', country='РОССИЯ',
                      rd_type=None, rd_name=None, rd_date=None, article_price=100, tax=20,
                      type='ТУФЛИ', color='ЧЕРНЫЙ', material_top='КОЖА', material_lining='КОЖА',
                      material_bottom='РЕЗИНА', gender='Женские', weight_grams=100,
                      gtin=gtin, gtin_company_key=company, sizes_quantities=[NS(size='42', quantity=2)])
        original = position()
        items = [original]
        ns['append_or_merge_position'](items, position(), 'shoes')
        self.assertEqual(len(items), 1)
        self.assertEqual(original.sizes_quantities[0].quantity, 4)
        self.assertEqual(original.weight_grams, 200)
        ns['append_or_merge_position'](items, position('g:AVRORA'), 'shoes')
        ns['append_or_merge_position'](items, position(gtin='04640735105579'), 'shoes')
        self.assertEqual(len(items), 3)
        size_positions = []
        first = position(gtin=None, company=None)
        first.sizes_quantities[0].gtin = '04640735105562'
        first.sizes_quantities[0].gtin_company_key = 'g:GRENADA'
        ns['append_or_merge_position'](size_positions, first, 'shoes')
        second = copy(first)
        second.sizes_quantities = [copy(first.sizes_quantities[0])]
        ns['append_or_merge_position'](size_positions, second, 'shoes')
        self.assertEqual(len(size_positions), 1)
        self.assertEqual(size_positions[0].sizes_quantities[0].quantity, 4)
        different = position(gtin=None, company=None)
        ns['append_or_merge_position'](size_positions, different, 'shoes')
        self.assertEqual(len(size_positions), 2)  # Same size without GTIN must remain distinct.
        other_size = position(gtin=None, company=None)
        other_size.sizes_quantities = [NS(size='44', quantity=1, gtin='04640735105562', gtin_company_key='g:GRENADA')]
        ns['append_or_merge_position'](size_positions, other_size, 'shoes')
        self.assertEqual(len(size_positions), 2)  # It may merge with the ordinary position, but not with the other GTIN size.
        self.assertEqual(len(size_positions[0].sizes_quantities), 1)

    def test_failed_edit_can_roll_back_the_original_position_deletion(self):
        from sqlalchemy import text
        from typing import Optional
        order = self.draft(['g:GRENADA', 'g:AVRORA'])
        position_id = order.clothes[0].id
        context = dict(Order=Order, Optional=Optional, text=text, db=NS(session=self.session),
                       current_user=NS(orders=self.session.query(Order)),
                       settings=NS(OrderStage=NS(CREATING=0)),
                       get_delete_pos_stmts=lambda **kwargs: f"DELETE FROM positions WHERE id={kwargs['m_id']} AND order_id={kwargs['o_id']}",
                       logger=NS(error=lambda *args: None), flash=lambda *args, **kwargs: None)
        delete = load_function('app/utilities/support.py', 'process_delete_order_pos', context)
        self.assertEqual(delete('одежда', order.id, position_id, edit=True), 'success')
        self.session.expire(order, ['clothes'])
        self.assertEqual(len(order.clothes), 1)
        # If validation or saving fails, the whole edit is rolled back.
        self.session.rollback()
        self.assertEqual(len(order.clothes), 2)
        self.assertIn(position_id, [item.id for item in order.clothes])

    def test_numbers_are_reserved_together_without_committing(self):
        session = NS(execute=lambda stmt, params: NS(first=lambda: NS(admin_order_num=23)))
        with patch.dict('sys.modules', {'models': NS(db=NS(session=session))}):
            user = NS(id=7, admin_parent_id=4, role='ordinary_user')
            self.assertEqual(namespace['reserve_order_numbers'](user, 3), ['4_21', '4_22', '4_23'])


class GtinExportTests(unittest.TestCase):
    def test_row_formats_keep_gtin_as_text_and_keep_existing_columns(self):
        categories = NS(**{name: NS(CATEGORY=name.lower()) for name in ('Cosmetics', 'Toys')})
        fn = load_function('app/utilities/download.py', 'export_gtin_row', {'settings': categories}, 'OrdersProcessor')
        position = NS(gtin='04640735105562')
        self.assertEqual(fn(['tnved'], position, 'clothes', False, True, size=NS(gtin='04640735105579')), ['04640735105579', 'tnved'])
        self.assertEqual(fn(['tnved'], NS(gtin=None), 'clothes', False, True, size=NS(gtin=None)), ['', 'tnved'])
        for category in ('shoes', 'linen', 'parfum', 'clothes', 'socks'):
            with self.subTest(category=category):
                self.assertEqual(fn(['tnved', 'name'], position, category, False, True), [position.gtin, 'tnved', 'name'])
                self.assertEqual(fn(['tnved', 'name'], position, category, False, False), ['tnved', 'name'])
        self.assertEqual(fn(['', 'tnved', 'name'], position, 'cosmetics', False, True), [position.gtin, 'tnved', 'name'])
        self.assertEqual(fn(['', 'tnved', 'name'], position, 'toys', False, True), [position.gtin, 'tnved', 'name'])
        self.assertEqual(fn(['', '', 'article'], position, 'clothes', True, True), ['', position.gtin, 'article'])

    def test_local_size_and_box_quantities_survive_gtin_export(self):
        common = NS(CATEGORY='одежда', NUMBER_STANDART='стандарт', CHILDREN_NUMBER_STANDART='детский',
                    TYPES_CODES={}, SYZE_TYPES_CODES={})
        categories = NS(Clothes=common, Socks=NS(CATEGORY='носки', TYPES_CODES={}, SYZE_TYPES_CODES={}),
                        Cosmetics=NS(CATEGORY='косметика'), Toys=NS(CATEGORY='игрушки'),
                        COUNTRIES_INNER={'РОССИЯ'}, COUNTRIES_CODES={})
        processors = NS(placeholder_export_value=lambda value, kind: value,
                        normalize_length_width_size_type_for_export=lambda value: value,
                        normalize_length_width_size_for_export=lambda value, kind: value,
                        normalize_export_content=lambda value: value, eatp=lambda value, field_type: value)
        ns = dict(settings=categories, OrdersProcessor=processors, datetime=datetime,
                  resolve_clothes_category_code=lambda value: 'code')
        processors.export_gtin_row = load_function('app/utilities/download.py', 'export_gtin_row', ns, 'OrdersProcessor')
        helpers = NS(get_gender_dec=lambda **kwargs: 'женские', get_gender=lambda **kwargs: 'женские',
                     get_gender_046=lambda **kwargs: 'женские')
        for class_name in ('ClothesProcessor', 'SocksProcessor'):
            ns[class_name] = helpers
            prepare = load_function('app/utilities/download.py', 'prepare_ext_data', ns, class_name)
            for flag in (False, True):
                item = NS(gtin='', tnved_code='6100000000', rd_type=None, rd_date=None, rd_name=None,
                          trademark='Тест', article='A1', type='ФУТБОЛКИ', color='БЕЛЫЙ', gender='Женский',
                          subcategory='common', content='ХЛОПОК', country='РОССИЯ', is_children=True,
                          article_price=100, tax=22, box_quantity=3,
                          sizes_quantities=[NS(size='42', size_type='РОССИЯ', quantity=2)])
                ordinary = prepare([item], flag_046=flag)
                item.gtin = '04640735105562'
                gtin = prepare([item], flag_046=flag)
                expected = list(ordinary[0][0])
                if flag:
                    expected[1] = item.gtin
                else:
                    self.assertEqual(expected[18], 6)
                    expected.insert(0, item.gtin)
                self.assertEqual(gtin[0][0], expected)
                self.assertEqual(gtin[1], [])
                self.assertEqual(gtin[2], [expected])

    def test_both_rf_and_import_filenames_have_gtin_before_origin_without_company(self):
        # Exercise the actual make_file branch, including the existing RF/import split.
        generated = []
        processor = NS(flag_046=False, orders_list_outer=[['import']], orders_list_inner=[['rf']],
                       get_filename=lambda **kwargs: ('archive', 'order'),
                       excel_add_worksheet_data=lambda **kwargs: None,
                       safe_filename_part=lambda value: value.replace(' ', '_'),
                       process_to_excel=lambda list_of_orders: generated.extend(list(list_of_orders)) or [])
        ns = {'Order': Order, 'BytesIO': BytesIO,
              'OrdersProcessor': NS(prepare_batches=lambda orders_divided: orders_divided,
                                   archive_excels=lambda **kwargs: (None, kwargs['filename']))}
        make = load_function('app/utilities/download.py', 'make_file', ns, 'OrdersProcessor')
        order = NS(id=1, is_moderation=False, is_gtin_order=True, processing_company_label='ООО Гренада (4400023137)', has_aggr=False)
        make(processor, order, 1, 'одежда', 2, 4, '', 'ИП', 'Клиент', '', '', '', '', '', '', '')
        self.assertEqual([rows for rows, _ in generated], [[['import']], [['rf']]])
        self.assertEqual([filename for _, filename in generated], ['order_GTIN_ВВЕЗЕН', 'order_GTIN_РФ_ВНУТР'])
        self.assertTrue(all('Гренада' not in filename and '4400023137' not in filename for _, filename in generated))
        self.assertTrue(generated[0][1].endswith('_ВВЕЗЕН'))
        self.assertTrue(generated[1][1].endswith('_РФ_ВНУТР'))


class GtinCompanyPresentationTests(unittest.TestCase):
    def split_label(self, value):
        function = load_function('app/utilities/order_processing_info.py', 'split_processing_company_label',
                                 {'re': __import__('re')})
        return function(value)

    def test_saved_title_and_inn_are_split_without_changing_company_name(self):
        for title, inn in [('ООО "Перемены"', '4400027438'),
                           ('ИП "Туркин Дмитрий Сергеевич"', '111604076740'),
                           ('ООО Компания (филиал)', '4400027438')]:
            self.assertEqual(self.split_label(f'{title} ({inn})'), (title, inn))
        self.assertEqual(self.split_label('Историческая компания'), ('Историческая компания', ''))
        self.assertEqual(self.split_label(None), ('', ''))

    def test_company_is_copyable_before_comment_and_in_gtin_tooltip(self):
        from html.parser import HTMLParser
        from jinja2 import Environment, FileSystemLoader
        class Attributes(HTMLParser):
            def __init__(self, html):
                super().__init__()
                self.copies, self.tooltips = [], []
                self.feed(html)
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if 'data-copy-value' in attrs:
                    self.copies.append(attrs['data-copy-value'])
                    self.assert_copy = attrs.get('onclick')
                if 'data-bs-title' in attrs:
                    self.tooltips.append(attrs['data-bs-title'])
        env = Environment(loader=FileSystemLoader(ROOT / 'app/templates'), autoescape=True)
        env.filters['from_json'] = __import__('json').loads
        title, inn = 'ООО "Перемены"', '4400027438'
        for role in ('admin', 'manager'):
            for enabled in (True, False):
                with self.subTest(role=role, gtin=enabled):
                    order = NS(id=1, manager_login=None, is_moderation=False, is_gtin_order=enabled,
                               processing_company_label=f'{title} ({inn})', category='', is_rf_order=False,
                               user_comment='Комментарий клиента', contact_info=None)
                    context = dict(n=order, current_user=NS(role=role), src='/managers',
                                   processing_company_title=title, processing_company_inn=inn,
                                   url_for=lambda *args, **kwargs: '/link', user_companies=[])
                    body = env.get_template('crm_mod_v1/helpers/order_description.html').render(**context)
                    attrs = Attributes(body)
                    self.assertEqual(attrs.copies, [title, inn] if enabled else [])
                    if enabled:
                        self.assertEqual(attrs.assert_copy, 'copy_buffer(this.dataset.copyValue)')
                        self.assertIn('GTIN компания', body)
                        self.assertLess(body.index('order-processing-company-badge'), body.index('Комментарий клиента'))
                    header = env.get_template('crm_mod_v1/helpers/order_category.html').render(**context)
                    tooltips = Attributes(header).tooltips
                    self.assertEqual(tooltips, [])


if __name__ == '__main__':
    unittest.main()
