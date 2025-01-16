from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

from config import settings

db = SQLAlchemy()


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    # this field is responsible for order numeration for specific admin
    admin_order_num = db.Column(db.Integer, default=0)
    email = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(50), default='+79999999999')
    password = db.Column(db.String(255))
    login_name = db.Column(db.String(1000))
    created_at = db.Column(db.DateTime(), default=datetime.now)

    role = db.Column(db.String(100))
    client_code = db.Column(db.String(100))
    status = db.Column(db.Boolean, default=False)
    is_at2 = db.Column(db.Boolean, default=False)  # is agent type 2 ( agent with tg and common balance for clients)
    is_crm = db.Column(db.Boolean, default=True)
    is_send_excel = db.Column(db.Boolean, default=False)
    order_notification = db.Column(db.String(600), default=settings.AGENT_DEFAULT_NOTE)
    agent_fee = db.Column(db.Integer, default=20)
    phone_verified = db.Column(db.Boolean, default=False)

    balance = db.Column(db.Integer, default=0)
    pending_balance_rf = db.Column(db.Integer, default=0)  # pending refill balance
    trust_limit = db.Column(db.Integer, default=0)
    # pending_balance_wo = db.Column(db.Integer, default=0)  # pending write off balance

    partners = db.relationship("PartnerCode", secondary='users_partners', backref='users', lazy='joined')
    # telegram = db.relationship('Telegram', backref='users', lazy='dynamic')
    telegram = db.relationship('Telegram', secondary='users_telegrams', back_populates="users", lazy='joined')

    promos = db.relationship('Promo', secondary='users_promos', back_populates="users", lazy='joined')
    bonus_codes = db.relationship('Bonus', secondary='users_bonus_codes', back_populates="users", lazy='joined')

    orders = db.relationship('Order', backref='users', cascade="all,delete", lazy='dynamic',
                             foreign_keys='Order.user_id')

    transactions = db.relationship('UserTransaction', backref='users', lazy='dynamic', foreign_keys='UserTransaction.user_id')

    crm_orders = db.relationship('Order', backref='managers', cascade="all,delete", lazy='dynamic',
                                 foreign_keys='Order.manager_id')

    orders_stats = db.relationship('OrderStat', backref='users', cascade="all,delete", lazy='dynamic',
                                   foreign_keys='OrderStat.user_id')
    orders_stats_m = db.relationship('OrderStat', backref='managers', cascade="all,delete", lazy='dynamic',
                                     foreign_keys='OrderStat.manager_id')

    telegram_message = db.relationship('TelegramMessage', backref='users', cascade="all,delete", lazy='joined')

    admin_parent_id = db.Column(db.Integer(), db.ForeignKey('users.id'))
    admin_group = db.relationship("User", backref=db.backref('admin_parent', remote_side=[id]), lazy='joined',
                                  order_by="desc(User.id)")
    restore_link = db.relationship('RestoreLink', backref="users", cascade="all,delete", lazy='dynamic')
    em_messages = db.relationship('EmailMessage', backref="users", cascade="all,delete", lazy='dynamic')

    prices = db.relationship('Price', back_populates='users', lazy='joined')
    price_id = db.Column(db.Integer, db.ForeignKey('prices.id'))


users_partners = db.Table('users_partners',
                          db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
                          db.Column('partner_code_id', db.Integer, db.ForeignKey('partner_codes.id'))
                          )


users_telegrams = db.Table('users_telegrams',
                           db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
                           db.Column('telegram_id', db.Integer, db.ForeignKey('telegram.id'))
                           )

users_promos = db.Table('users_promos',
                        db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
                        db.Column('promo_id', db.Integer, db.ForeignKey('promos.id')),
                        db.Column('activated_at', db.DateTime, default=datetime.now)
                        )

users_bonus_codes = db.Table('users_bonus_codes',
                             db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
                             db.Column('promo_id', db.Integer, db.ForeignKey('bonus_codes.id')),
                             db.Column('activated_at', db.DateTime, default=datetime.now)
                             )

# class UserPromo(db.Model):
#     __tablename__ = 'users_promos'
#     user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
#     promo_id = db.Column(db.Integer, db.ForeignKey('promos.id'), primary_key=True)
#     status = db.Column(db.Boolean, default=False)
#
#     user = db.relationship("User", back_populates="promos")
#     promo = db.relationship("Promo", back_populates="users")


class PartnerCode(db.Model):
    __tablename__ = 'partner_codes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    code = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(50))
    required_phone = db.Column(db.Boolean, default=False)
    required_email = db.Column(db.Boolean, default=True)
    # users = db.relationship("User", secondary="users_partners")
    # user_id = db.Column(db.Integer, db.ForeignKey('users.id'))


class Telegram(db.Model, UserMixin):
    __tablename__ = 'telegram'
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.String(50))
    name = db.Column(db.String(50))
    comment = db.Column(db.String(50))
    status = db.Column(db.Boolean, default=False)

    # user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    users = db.relationship("User", secondary="users_telegrams", back_populates="telegram")


class Promo(db.Model, UserMixin):
    __tablename__ = 'promos'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True)
    value = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime(), default=datetime.now)
    is_archived = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime(), onupdate=datetime.now)
    users = db.relationship("User", secondary="users_promos", back_populates="promos")


class Bonus(db.Model, UserMixin):
    __tablename__ = 'bonus_codes'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True)
    value = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime(), default=datetime.now)
    is_archived = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime(), onupdate=datetime.now)
    users = db.relationship("User", secondary="users_bonus_codes", back_populates="bonus_codes")

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'value': self.value,
            'created_at': self.created_at,
        }


class Price(db.Model, UserMixin):
    __tablename__ = 'prices'
    id = db.Column(db.Integer, primary_key=True)
    price_code = db.Column(db.String(50), unique=True)
    price_1 = db.Column(db.Numeric(10, 2), default=settings.Prices.F_LTE_100)
    price_2 = db.Column(db.Numeric(10, 2), default=settings.Prices.F_100_500)
    price_3 = db.Column(db.Numeric(10, 2), default=settings.Prices.F_500_1K)
    price_4 = db.Column(db.Numeric(10, 2), default=settings.Prices.F_1K_3K)
    price_5 = db.Column(db.Numeric(10, 2), default=settings.Prices.F_3K_5K)
    price_6 = db.Column(db.Numeric(10, 2), default=settings.Prices.F_5K_10K)
    price_7 = db.Column(db.Numeric(10, 2), default=settings.Prices.F_10K_20K)
    price_8 = db.Column(db.Numeric(10, 2), default=settings.Prices.F_20K_35K)
    price_9 = db.Column(db.Numeric(10, 2), default=settings.Prices.F_35K_50K)
    price_10 = db.Column(db.Numeric(10, 2), default=settings.Prices.F_50K_100K)
    price_11 = db.Column(db.Numeric(10, 2), default=settings.Prices.F_100K)
    price_at2 = db.Column(db.Boolean, default=False)  # price packet for agent type 2
    created_at = db.Column(db.DateTime(), default=datetime.now)
    users = db.relationship('User', back_populates='prices', lazy='dynamic')


class ServiceAccount(db.Model, UserMixin):
    __tablename__ = 'service_accounts'

    id = db.Column(db.Integer, primary_key=True)
    sa_name = db.Column(db.String(50), unique=True)
    sa_type = db.Column(db.String(50))
    sa_qr_path = db.Column(db.String(100))
    sa_reqs = db.Column(db.String(350))
    summ_transfer = db.Column(db.Integer, default=0)
    current_use = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=False)
    is_archived = db.Column(db.Boolean, default=False)
    archived_at = db.Column(db.DateTime(), default=None, nullable=True)
    created_at = db.Column(db.DateTime(), default=datetime.now)
    transactions = db.relationship('UserTransaction', back_populates='service_accounts', lazy='dynamic')


class UserTransaction(db.Model, UserMixin):
    __tablename__ = 'user_transactions'

    id = db.Column(db.BigInteger, primary_key=True)

    # True if refill and False is write-off
    type = db.Column(db.Boolean, default=False)
    amount = db.Column(db.Integer)
    op_cost = db.Column(db.Numeric(10, 2), default=0)  # in case transaction for orders write off - price per one mark
    agent_fee = db.Column(db.Integer, default=20)
    status = db.Column(db.Integer, default=settings.Transactions.PENDING)
    bill_path = db.Column(db.String(150), unique=True)
    created_at = db.Column(db.DateTime(), default=datetime.now)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    sa_id = db.Column(db.Integer, db.ForeignKey('service_accounts.id'), index=True)
    promo_info = db.Column(db.String(100), default='')
    wo_account_info = db.Column(db.String(500), default='')

    service_accounts = db.relationship('ServiceAccount', back_populates='transactions',)
    # orders in process for fixing them whenmake transaction and  changing to POOL stage
    orders_ip = db.relationship('Order', backref='user_transactions',  foreign_keys='Order.transaction_id')
    # orders in stats that we can watch in transaction history
    orders = db.relationship('OrderStat', backref='user_transactions',  foreign_keys='OrderStat.transaction_id')
    # orders = db.relationship('Order', backref='user_transactions',  foreign_keys='Order.transaction_id')
    is_bonus = db.Column(db.Boolean, default=False)


class TelegramMessage(db.Model, UserMixin):
    __tablename__ = 'telegram_messages'
    id = db.Column(db.Integer, primary_key=True)
    send_admin_info = db.Column(db.Boolean(), default=True)
    send_organization_name = db.Column(db.Boolean(), default=True)
    send_organization_idn = db.Column(db.Boolean(), default=True)
    send_login_name = db.Column(db.Boolean(), default=True)
    send_email = db.Column(db.Boolean(), default=True)
    send_phone = db.Column(db.Boolean(), default=True)
    send_client_code = db.Column(db.Boolean(), default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))


class RestoreLink(db.Model, UserMixin):
    __tablename__ = 'restore_links'
    id = db.Column(db.Integer, primary_key=True)
    link = db.Column(db.String(150), default='')
    status = db.Column(db.Boolean(), default=True)
    created_at = db.Column(db.DateTime(), default=datetime.now)
    used_at = db.Column(db.DateTime(), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))


class EmailMessage(db.Model, UserMixin):
    __tablename__ = 'email_messages'
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(500), default='')
    created_at = db.Column(db.DateTime(), default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))


class Order(db.Model, UserMixin):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)

    category = db.Column(db.String(100), nullable=False, default='')

    company_idn = db.Column(db.String(100))
    company_type = db.Column(db.String(100))
    company_name = db.Column(db.String(100))
    edo_type = db.Column(db.String(100), default="ЭДО-ЛАЙТ")
    edo_id = db.Column(db.String(100), default="")
    mark_type = db.Column(db.String(100), default='МАРКИРОВКА НЕ ВЫБРАНА')
    user_comment = db.Column(db.String(450), default="")
    has_new_tnveds = db.Column(db.Boolean, default=False)

    payment = db.Column(db.Boolean(), default=False)
    processed = db.Column(db.Boolean(), default=False)
    external_problem = db.Column(db.Boolean(), default=False)

    stage = db.Column(db.Integer, default=0, index=True)
    comment_problem = db.Column(db.String(230), default='')
    comment_cancel = db.Column(db.String(230), default='')

    p_started = db.Column(db.DateTime())  # pool strated
    m_started = db.Column(db.DateTime())  # manager has taken order
    m_finished = db.Column(db.DateTime())  # manager has taken order
    cp_created = db.Column(db.DateTime())  # problem created
    cc_created = db.Column(db.DateTime())  # cancel made

    # save to_delete for bg_tasks not used
    to_delete = db.Column(db.Boolean(), default=False)  # not currently used but can be useful in future
    order_idn = db.Column(db.String(100), unique=True, nullable=True, default=None)

    created_at = db.Column(db.DateTime(), default=datetime.now)  # user started creating order
    crm_created_at = db.Column(db.DateTime())  # order pushed to NEW stage of crm
    sent_at = db.Column(db.DateTime())  # order sent
    closed_at = db.Column(db.DateTime())  # order processed

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), index=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    stage_setter_name = db.Column(db.String(100))
    transaction_id = db.Column(db.Integer, db.ForeignKey('user_transactions.id'), index=True)

    order_zip_file = db.relationship('OrderFile', uselist=False, cascade='all,delete', backref='orders')
    shoes = db.relationship('Shoe', backref='orders', cascade="all,delete", lazy='joined')
    linen = db.relationship('Linen', backref='orders', cascade="all,delete", lazy='joined')
    parfum = db.relationship('Parfum', backref='orders', cascade="all,delete", lazy='joined')
    clothes = db.relationship('Clothes', backref='orders', cascade="all,delete", lazy='joined')
    socks = db.relationship('Socks', backref='orders', cascade="all,delete", lazy='joined')


class OrderFile(db.Model, UserMixin):
    __tablename__ = 'order_files'

    id = db.Column(db.Integer, primary_key=True)
    origin_name = db.Column(db.String(100), nullable=False, default='')
    file_system_name = db.Column(db.String(100))
    file_link = db.Column(db.String(100))
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), index=True)


class OrderStat(db.Model, UserMixin):
    __tablename__ = 'orders_stats'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False, default='')
    company_idn = db.Column(db.String(100))
    company_type = db.Column(db.String(100))
    company_name = db.Column(db.String(100))
    order_idn = db.Column(db.String(100), unique=True)
    rows_count = db.Column(db.Integer, default=1)
    marks_count = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime(),)
    op_cost = db.Column(db.Numeric(10, 2), default=None)  # order price per one mark cost
    # payment = db.Column(db.Boolean, default=False)

    comment_problem = db.Column(db.String(230), default='')
    cp_created = db.Column(db.DateTime())  # problem created

    m_started = db.Column(db.DateTime())  # manager have taken order
    m_finished = db.Column(db.DateTime())  # manager have taken order

    crm_created_at = db.Column(db.DateTime())  # order pushed to NEW stage of crm
    sent_at = db.Column(db.DateTime())  # order sent
    # closed_at = db.Column(db.DateTime())  # order processed
    saved_at = db.Column(db.DateTime(), default=datetime.now)  # order saved into order_stats
    stage_setter_name = db.Column(db.String(100))
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    # without backref- only sql
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('user_transactions.id'), index=True)


class CommonMixin:
    id = db.Column(db.BigInteger, primary_key=True)
    type = db.Column(db.String(50))

    article_price = db.Column(db.Float(), default=0)
    tnved_code = db.Column(db.String(50), default='')
    country = db.Column(db.String(58), default='')
    tax = db.Column(db.Integer(), default=0)
    trademark = db.Column(db.String(100))

    rd_type = db.Column(db.String(50))
    rd_name = db.Column(db.String(100))
    rd_date = db.Column(db.Date())


class OrderCommon(CommonMixin):
    article = db.Column(db.String(100))
    box_quantity = db.Column(db.Integer(), default=1)


class Shoe(db.Model, UserMixin, OrderCommon):
    __tablename__ = "shoes"

    # SHOE_TYPE IS TYPE COMMONMIXIN
    color = db.Column(db.String(50))
    material_top = db.Column(db.String(50))
    material_lining = db.Column(db.String(50))
    material_bottom = db.Column(db.String(50))
    gender = db.Column(db.String(50))
    with_packages = db.Column(db.Boolean(), default=False)

    sizes_quantities = db.relationship('ShoeQuantitySize', backref='shoes', cascade="all,delete", lazy='joined')
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), index=True)


class ShoeQuantitySize(db.Model, UserMixin):
    __tablename__ = "shoes_quantity_sizes"
    id = db.Column(db.BigInteger, primary_key=True)
    size = db.Column(db.String())
    quantity = db.Column(db.Integer())
    shoe_id = db.Column(db.Integer, db.ForeignKey('shoes.id', ondelete='CASCADE'), index=True)


class Linen(db.Model, UserMixin, OrderCommon):
    __tablename__ = "linen"

    # BED_LINEN PRODUCT tYPE IS TYPE COMMONMIXIN
    color = db.Column(db.String(50))
    customer_age = db.Column(db.String(50))
    textile_type = db.Column(db.String(50))
    content = db.Column(db.String(100))
    with_packages = db.Column(db.String(50), default="нет")
    sizes_quantities = db.relationship('LinenQuantitySize', backref='linen', cascade="all,delete", lazy='joined')
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), index=True)


class LinenQuantitySize(db.Model, UserMixin):
    __tablename__ = "linen_quantity_sizes"
    id = db.Column(db.BigInteger, primary_key=True)
    size = db.Column(db.String())
    quantity = db.Column(db.Integer())
    lin_id = db.Column(db.Integer, db.ForeignKey('linen.id', ondelete='CASCADE'), index=True)


class Parfum(db.Model, UserMixin, CommonMixin):

    # PARFUM TYPE IS TYPE (COMMONMIXIN)
    volume_type = db.Column(db.String(50))
    volume = db.Column(db.String(50))
    package_type = db.Column(db.String(50))
    material_package = db.Column(db.String(50))
    with_packages = db.Column(db.String(50), default="нет")
    box_quantity = db.Column(db.Integer(), default=1)
    quantity = db.Column(db.Integer())
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), index=True)


class ClothesMixin(db.Model, UserMixin, OrderCommon):
    # __tablename__ = "clothes"
    __abstract__ = True
    # CLOTHES PRODUCT tYPE IS TYPE COMMONMIXIN
    color = db.Column(db.String(50))
    gender = db.Column(db.String(50))

    content = db.Column(db.String(100))


class CQSMixin(db.Model, UserMixin):
    # __tablename__ = "cl_quantity_sizes"
    __abstract__ = True

    id = db.Column(db.BigInteger, primary_key=True)
    size = db.Column(db.String())
    quantity = db.Column(db.Integer())
    size_type = db.Column(db.String(50))
    # cl_id = db.Column(db.Integer, db.ForeignKey('clothes.id', ondelete='CASCADE'), index=True)


class Clothes(ClothesMixin):
    __tablename__ = "clothes"

    # CLOTHES PRODUCT tYPE IS TYPE COMMONMIXIN
    # color = db.Column(db.String(50))
    # gender = db.Column(db.String(50))
    #
    # content = db.Column(db.String(100))
    sizes_quantities = db.relationship('ClothesQuantitySize', backref='clothes', cascade="all,delete", lazy='joined')
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), index=True)


class ClothesQuantitySize(CQSMixin):
    __tablename__ = "cl_quantity_sizes"

    # id = db.Column(db.BigInteger, primary_key=True)
    # size = db.Column(db.String())
    # quantity = db.Column(db.Integer())
    # size_type = db.Column(db.String(50))
    cl_id = db.Column(db.Integer, db.ForeignKey('clothes.id', ondelete='CASCADE'), index=True)


class Socks(ClothesMixin):
    __tablename__ = "socks"
    sizes_quantities = db.relationship('SocksQuantitySize', backref='socks', cascade="all,delete", lazy='joined')
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), index=True)


class SocksQuantitySize(CQSMixin):
    __tablename__ = "socks_quantity_sizes"
    # id = db.Column(db.BigInteger, primary_key=True)
    # size = db.Column(db.String())
    # quantity = db.Column(db.Integer())
    socks_id = db.Column(db.Integer, db.ForeignKey('socks.id', ondelete='CASCADE'), index=True)


class ServerParam(db.Model):
    __tablename__ = "server_params"

    id = db.Column(db.Integer(),  primary_key=True)
    crm_manager_ps_limit = db.Column(db.Integer, default=settings.OrderStage.DEFAULT_PS_LIMIT)
    crm_manager_mo_limit = db.Column(db.Integer, default=settings.OrderStage.DEFAULT_MO_LIMIT)
    crm_manager_po_limit = db.Column(db.Integer, default=settings.OrderStage.DEFAULT_PO_LIMIT)
    auto_pool_rows = db.Column(db.Integer, default=settings.OrderStage.DEFAULT_AP_ROWS)
    auto_pool_marks = db.Column(db.Integer, default=settings.OrderStage.DEFAULT_AP_MARKS)
    auto_sent_minutes = db.Column(db.Integer, default=settings.OrderStage.DEFAULT_AS_MINUTES)
    account_type = db.Column(db.String(18), default=settings.ServiceAccounts.DEFAULT_QR_ACCOUNT_TYPE)

    balance = db.Column(db.Integer, default=0)
    pending_balance_rf = db.Column(db.Integer, default=0)  # pendin refill balance
    # pending_balance_wo = db.Column(db.Integer, default=0)  # pending write off balance


class TgUser(db.Model):
    __tablename__ = "notification_telegram_user"

    tg_user_id = db.Column(db.BigInteger, primary_key=True, unique=True)
    tg_chat_id = db.Column(db.BigInteger)
    tg_username = db.Column(db.String(255))
    verification_code = db.Column(db.String(64), unique=True, index=True)
    flask_user_id = db.Column(db.Integer, nullable=True, default=None, index=True)

    def __repr__(self) -> str:
        return f"User(user_id={self.tg_user_id}, username={self.tg_username}, is_verified={True if self.flask_user_id else False}"


class ReanimateStatus(db.Model):
    __tablename__ = "reanimate_status"
    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.String(255))
    call_result = db.Column(db.String(36))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    updated_at = db.Column(db.DateTime(), server_default=func.now(), onupdate=func.now())


ModelType = User | PartnerCode
