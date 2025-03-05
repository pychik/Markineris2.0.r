from abc import ABC, abstractmethod
from io import BytesIO
from typing import Optional, Union

from pandas import DataFrame
from xlsxwriter.workbook import Workbook
from xlsxwriter.worksheet import Worksheet


class ProcessorInterface(ABC):

    @abstractmethod
    def excel_add_worksheet_data(self, company_idn: str, company_name: str, company_type: str, edo_type: str,
                                 edo_id: str, mark_type: str,
                                 user_name: str, user_phone: str, user_email: str, partner: str) -> None:
        ...

    @abstractmethod
    def process_to_excel(self, list_of_orders: iter) -> tuple:
        ...

    @abstractmethod
    def orders_list(self) -> list:
        ...

    @property
    def orders_list_outer(self) -> list:
        return ...

    @property
    def orders_list_inner(self) -> list:
        return ...

    @staticmethod
    def prepare_batches(orders_divided: list, batch_size=400):
        ...

    @staticmethod
    def prepare_data(orders_list: list):
        ...

    @staticmethod
    def prepare_ext_data(orders_list: list, flag_046: bool = False):
        ...

    @staticmethod
    def get_filename(order_num: int, category: str, pos_count: int, count: int,
                     partner_code: str, company_type: str, company_name: str, flag_046: bool = False) -> str:
        ...

    @staticmethod
    def set_styles(workbook: Workbook, worksheet: Worksheet, row: int):
        ...

    @staticmethod
    def add_to_excel(worksheet: Worksheet, data: Optional[Union[tuple, list]], row: int, col: int) -> None:
        ...

    @staticmethod
    def excel_start_data(category: str):
        ...

    @staticmethod
    def excel_start_data_ext(category: str,  flag_046: bool = False):
        ...

    @staticmethod
    def adjusting_df(df: DataFrame, worksheet: Worksheet):
        ...

    @staticmethod
    def archive_excels(excel_files: list[BytesIO], filename: str) -> BytesIO:
        ...

    @staticmethod
    def eatp(value: str, field_type: str) -> str:
        ...

    def make_file(self, order_num: int, category: str, pos_count: int, orders_pos_count: int,
                  c_partner_code: str, company_type: str, company_name: str, company_idn: str, edo_type: str,
                  edo_id: str, mark_type: str, c_name: str, c_phone: str, c_email: str, ) -> tuple[BytesIO, str]:
        ...

    @staticmethod
    def eatp(value: str, field_type: str) -> str:
        ...