"""Exercise CRM bulk approval, permissions and size merging on an isolated database."""
import ast
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from types import SimpleNamespace as NS
from typing import Optional
import unittest
from unittest.mock import Mock

from flask import Flask, jsonify, request
from sqlalchemy import Column, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Boolean, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base, relationship

ROOT = Path(__file__).resolve().parents[1]
CRM = ROOT / 'app/views/main/product_cards/crm'
Base = declarative_base()


class Status(Enum):
    SENT = 'sent'
    SENT_NO_RD = 'sent_no_rd'
    IN_PROGRESS = 'in_progress'
    IN_MODERATION = 'in_moderation'
    CLARIFICATION = 'clarification'
    APPROVED = 'approved'
    REJECTED = 'rejected'


class Card(Base):
    __tablename__ = 'cards'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, default=50)
    manager_id = Column(Integer, default=10)
    category = Column(String, default='clothes')
    status = Column(SqlEnum(Status), default=Status.IN_MODERATION)
    created_at = Column(DateTime, default=datetime.now)
    approved_at = Column(DateTime)
    moderation_at = Column(DateTime)
    is_repeat_moderation = Column(Boolean, default=True)
    processing_company_label = Column(String, default='Company')
    card_log = Column(String, default='')
    clothes = relationship('Clothing', cascade='all, delete-orphan')


class Clothing(Base):
    __tablename__ = 'clothing'
    id = Column(Integer, primary_key=True)
    card_id = Column(ForeignKey('cards.id'))
    article = Column(String)
    color = Column(String, default='black')
    subcategory = Column(String, default='common')
    sizes_quantities = relationship('Size', backref='clothes', cascade='all,delete')


class Size(Base):
    __tablename__ = 'sizes'
    id = Column(Integer, primary_key=True)
    clothing_id = Column(ForeignKey('clothing.id'))
    size = Column(String)
    size_type = Column(String, default='RU')
    is_approved = Column(Boolean, default=False)


def load_functions(path, names, ns):
    tree = ast.parse(path.read_text())
    nodes = [node for node in tree.body if getattr(node, 'name', None) in names
             or isinstance(node, ast.Assign) and any(getattr(t, 'id', '') in names for t in node.targets)
             or isinstance(node, ast.AnnAssign) and getattr(node.target, 'id', '') in names]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), ns)


class BulkApprovalTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine('sqlite://')
        Base.metadata.create_all(engine)
        self.session = Session(engine)
        self.addCleanup(engine.dispose)
        self.addCleanup(self.session.close)
        Card.query = self.session.query(Card)
        settings = NS(**{cat: NS(CATEGORY_PROCESS=cat.lower()) for cat in ('Clothes', 'Shoes', 'Linen', 'Socks')})
        self.user = NS(id=10, role='manager', login_name='operator')
        self.ns = dict(ProductCard=Card, ModerationStatus=Status, settings=settings,
                       current_user=self.user, db=NS(session=self.session), request=request,
                       jsonify=jsonify, logger=Mock(), SQLAlchemyError=SQLAlchemyError,
                       Optional=Optional, dataclass=dataclass, datetime=datetime,
                       CATEGORIES_COMMON={'clothes': dict(model=Clothing, rel_name='clothes', has_subcategory=True)},
                       h_append_card_log=lambda old, addition: (old or '') + addition,
                       h_pc_move_render_list_html=lambda *a, **kw: ('<list>', 0))
        load_functions(CRM / 'transitions.py', {'TRANSITIONS', 'CRM_ADMIN_ROLES', 'CRM_MANAGER_ROLE',
                       'ALLOWED_BACK_TO_SENT_ROLES', 'MoveResult', 'can_see_all',
                       'validate_transition', 'check_owner_or_admin', 'check_special_rules'}, self.ns)
        load_functions(CRM / 'helpers.py', {'h_pc_move_apply_status_transition'}, self.ns)
        load_functions(CRM / 'handlers.py', {'h_pc_move_finalize_approval', 'h_pc_bulk_move_cards'}, self.ns)
        self.app = Flask(__name__)

    def card(self, article='A', sizes=('S',), **kw):
        card = Card(clothes=[Clothing(article=article, sizes_quantities=[Size(size=s) for s in sizes])], **kw)
        self.session.add(card)
        self.session.commit()
        return card

    def move(self, ids, target='approved'):
        with self.app.test_request_context(method='POST', data={'card_ids[]': ids, 'target': target}):
            result = self.ns['h_pc_bulk_move_cards']()
            response, code = result if isinstance(result, tuple) else (result, 200)
            return response.get_json(), code

    def test_selected_cards_only_and_approval_metadata(self):
        first, second, untouched = self.card('A'), self.card('B'), self.card('C')
        data, code = self.move([first.id, second.id, first.id])
        self.assertEqual((code, data['moved_count']), (200, 2))
        self.assertEqual(set(data['updated_columns']), {'in_moderation', 'approved'})
        for card in (first, second):
            self.assertEqual(card.status, Status.APPROVED)
            self.assertIsNotNone(card.approved_at)
            self.assertFalse(card.is_repeat_moderation)
            self.assertTrue(card.clothes[0].sizes_quantities[0].is_approved)
        self.assertEqual(untouched.status, Status.IN_MODERATION)

    def test_manager_cannot_move_other_operators_cards(self):
        own, other = self.card('A'), self.card('B', manager_id=11)
        _, code = self.move([own.id, other.id])
        self.assertEqual(code, 403)
        self.assertEqual(own.status, Status.IN_MODERATION)
        self.assertEqual(other.status, Status.IN_MODERATION)

    def test_admin_roles_keep_permission_for_other_operators_cards(self):
        for role in ('superuser', 'supermanager'):
            self.user.role = role
            card = self.card(role, manager_id=11)
            self.assertEqual(self.move([card.id])[1], 200)
            self.assertEqual(card.status, Status.APPROVED)

    def test_invalid_company_rolls_back_previously_flushed_approval(self):
        first, invalid = self.card('A'), self.card('B', processing_company_label='')
        data, code = self.move([first.id, invalid.id])
        self.assertEqual(code, 400)
        self.assertIn('компания', data['message'])
        self.assertEqual(first.status, Status.IN_MODERATION)
        self.assertIsNone(first.approved_at)
        self.assertFalse(first.clothes[0].sizes_quantities[0].is_approved)

    def test_same_article_cards_merge_sizes_without_duplicates(self):
        first, second = self.card(sizes=('S',)), self.card(sizes=('S', 'M'))
        second_id = second.id
        self.assertEqual(self.move([first.id, second.id])[1], 200)
        self.assertIsNone(self.session.get(Card, second_id))
        self.assertEqual({s.size for s in first.clothes[0].sizes_quantities}, {'S', 'M'})
        self.assertTrue(all(s.is_approved for s in first.clothes[0].sizes_quantities))

    def test_failed_batch_rolls_back_size_merge_and_deletion(self):
        base = self.card(sizes=('S',), status=Status.APPROVED)
        source = self.card(sizes=('M',))
        invalid = self.card('B', processing_company_label='')
        source_id = source.id
        self.assertEqual(self.move([source.id, invalid.id])[1], 400)
        self.assertIsNotNone(self.session.get(Card, source_id))
        self.assertEqual(source.status, Status.IN_MODERATION)
        self.assertEqual({s.size for s in base.clothes[0].sizes_quantities}, {'S'})
        self.assertEqual({s.size for s in source.clothes[0].sizes_quantities}, {'M'})

    def test_special_rule_denial_keeps_whole_batch_unchanged(self):
        first, second = self.card('A'), self.card('B')
        self.ns['check_special_rules'] = lambda user, card, target: (
            NS(message='Forbidden', status_code=403) if card.id == second.id else None)
        self.assertEqual(self.move([first.id, second.id])[1], 403)
        self.assertEqual(first.status, Status.IN_MODERATION)
        self.assertEqual(second.status, Status.IN_MODERATION)

    def test_previous_clarification_transition_still_works(self):
        card = self.card(status=Status.CLARIFICATION)
        data, code = self.move([card.id], 'in_moderation')
        self.assertEqual(code, 200)
        self.assertEqual(card.status, Status.IN_MODERATION)
        self.assertIn('Перенесено на модерацию', data['message'])
        self.assertFalse(card.clothes[0].sizes_quantities[0].is_approved)

    def test_other_bulk_transitions_and_missing_ids_remain_forbidden(self):
        card = self.card(status=Status.CLARIFICATION)
        self.assertEqual(self.move([card.id])[1], 400)
        self.assertEqual(self.move([999])[1], 404)
        self.assertEqual(card.status, Status.CLARIFICATION)


if __name__ == '__main__':
    unittest.main()
