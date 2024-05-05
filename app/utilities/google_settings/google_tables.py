import httplib2
import apiclient
import logging as logger
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from rq.decorators import job
from threading import Thread

# from test_config import settings, NOTIFICATION_GT_JOB_PARAMS
from config import settings
from redis_queue.constants import NOTIFICATION_GT_JOB_PARAMS
from utilities.google_settings.schema import OrderRow, PromoRow, RuznakRow

logger.basicConfig(level=logger.WARNING,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',)
logger.getLogger('googleapicliet.discovery_cache').setLevel(logger.ERROR)


class GoogleProcess:
    def __init__(self, data_list: list[OrderRow | PromoRow | RuznakRow],
                 spreadsheet: str = settings.GoogleTables.SPREADSHEET_ID,
                 sheet_name: str = settings.GoogleTables.SHEET_NAME_ORDERS) -> None:
        self.data_list = data_list
        self.spreadsheet = spreadsheet
        self.sheet_name = sheet_name
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(settings.GoogleTables.GT_JSON_SET,
                                                                       ['https://www.googleapis.com/auth/spreadsheets',
                                                                        'https://www.googleapis.com/auth/drive'])

        self.httpAuth = credentials.authorize(httplib2.Http())  # Авторизуемся в системе
        self.service = apiclient.discovery.build('sheets', 'v4', http=self.httpAuth)

    def last_row_index(self, gt_range: str = settings.GoogleTables.SHEET_RANGE_ORDERS) -> int:

        rowcount_raw = (self.service.spreadsheets().values()
                        .get(spreadsheetId=self.spreadsheet,
                             range=gt_range).execute())

        return len(rowcount_raw.get("values"))

    @property
    def sheet_range(self) -> str:
        match (self.spreadsheet, self.sheet_name):
            case (settings.GoogleTables.SPREADSHEET_ID, settings.GoogleTables.SHEET_NAME_PROMOS):
                lr_index = self.last_row_index(gt_range=settings.GoogleTables.SHEET_RANGE_PROMOS)
                return (f"{settings.GoogleTables.SHEET_NAME_PROMOS}!{settings.GoogleTables.FC_PROMOS}"
                        f"{lr_index + 1}:{settings.GoogleTables.LC_PROMOS}")
            case (settings.GoogleTables.SPREADSHEET_ID, settings.GoogleTables.SHEET_NAME_ORDERS):
                lr_index = self.last_row_index(gt_range=settings.GoogleTables.SHEET_RANGE_ORDERS)
                return (f"{settings.GoogleTables.SHEET_NAME_ORDERS}!{settings.GoogleTables.FC_ORDERS}"
                        f"{lr_index + 1}:{settings.GoogleTables.LC_ORDERS}")
            case (settings.GoogleTables.RuZnak.SPREADSHEET_ID_RUZNAK, settings.GoogleTables.RuZnak.SHEET_NAME_RUZNAK):
                lr_index = self.last_row_index(gt_range=settings.GoogleTables.RuZnak.SHEET_RANGE_RUZNAK)
                return (f"{settings.GoogleTables.RuZnak.SHEET_NAME_RUZNAK}!{settings.GoogleTables.RuZnak.FC_RUZNAK}"
                        f"{lr_index + 1}:{settings.GoogleTables.RuZnak.LC_RUZNAK}")
            case _:
                lr_index = self.last_row_index(gt_range=settings.GoogleTables.SHEET_RANGE_ORDERS)
                return (f"{settings.GoogleTables.SHEET_NAME_ORDERS}!{settings.GoogleTables.FC_ORDERS}"
                        f"{lr_index + 1}:{settings.GoogleTables.LC_ORDERS}")

    def send_data_packet(self) -> bool:
        try:
            self.service.spreadsheets().values().batchUpdate(spreadsheetId=self.spreadsheet,
                                                    body={"valueInputOption": "USER_ENTERED",
                                                          "data": [
                                                                      {"range": self.sheet_range,
                                                                       "majorDimension": "ROWS",
                                                                       "values": self.data_list}
                                                                    ]
                                                          }).execute()
            logger.info(msg=f"{settings.Messages.GOOGLE_TABLES_SEND_SUCCESS}")
            return True
        except Exception as e:
            logger.warning(msg=f"{settings.Messages.GOOGLE_TABLES_SEND_ERROR}"
                               f"\n не проведена! \nОшибка: {e}")
            return False

    def send_data_packet_in_thread(self):
        Thread(target=self.send_data_packet, daemon=True).start()

    @staticmethod
    @job(**NOTIFICATION_GT_JOB_PARAMS)
    def send_promo_data(data_packet: PromoRow) -> None:
        gp = GoogleProcess(data_list=[data_packet,], sheet_name=settings.GoogleTables.SHEET_NAME_PROMOS)
        gp.send_data_packet()

    # @staticmethod
    # @job(**NOTIFICATION_GT_JOB_PARAMS)
    # def send_ruznak_data(data_packet: RuznakRow) -> None:
    #     gp = GoogleProcess(data_list=[data_packet, ], spreadsheet=settings.GoogleTables.RuZnak.SPREADSHEET_ID_RUZNAK,
    #                        sheet_name=settings.GoogleTables.RuZnak.SHEET_NAME_RUZNAK)
    #     gp.send_data_packet()


if __name__ == "__main__":
    date_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    test_row = OrderRow(date_value=date_time, order_idn="17_60", partner_code="015", login_name="TEST user",
                        company_name="Organization", phone="+79999999919",  marks_count=40, rows_count=10,
                        category="одежда", price=8, status="Оплачено", agent_type="Единый счет")
    # test_row = RuznakRow(date_value=date_time, company_composed="Organization", marks_count=10, rows_count=40,
    #                      category="одежда", transaction_price=8, final_price=80, partner_code="015", order_idn='2_215')
    # test_row = PromoRow(date_value=date_time, login_name='TEST', service_account='счет ТЕСТ', promo_code='TestPromo',
    #                     promo_summ=5000)

    # test_row = [date_time, "17_60", "015", "TEST user", "Organization", "+79999999919", 40, 10, "одежда", 8, "ОПЛАЧЕНО", "Единый счет"]

    # gp = GoogleProcess(data_list=[test_row, test_row, test_row],)
    # gp = GoogleProcess(data_list=[test_row, test_row, test_row], sheet_name=settings.GoogleTables.SHEET_NAME_PROMOS)
    gp = GoogleProcess(data_list=[test_row, test_row, test_row],
                       spreadsheet=settings.GoogleTables.RuZnak.SPREADSHEET_ID_RUZNAK,
                       sheet_name=settings.GoogleTables.RuZnak.SHEET_NAME_RUZNAK)
    gp.send_data_packet()
