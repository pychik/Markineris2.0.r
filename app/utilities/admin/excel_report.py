from io import BytesIO
from copy import copy
from pandas import DataFrame

from xlsxwriter import Workbook
from xlsxwriter.worksheet import Worksheet

from config import settings
from models import UserTransaction


class ExcelReportProcessor:
    def __init__(self, transactions: list[UserTransaction], transaction_summ: int, tr_type: str, tr_status: str,
                 date_range: str,) -> None:
        self._transactions = transactions
        self._transaction_summ = transaction_summ
        self._tr_type = tr_type
        self._date_range = date_range
        self._tr_status = tr_status
        self._report_file_name = self.report_file_name()

    @property
    def transactions(self) -> list:
        return self._transactions

    def transactions_processed(self) -> list:
        res = []
        for el in self.transactions:
            res.append([el.created_at.strftime("%d-%m-%Y %H:%M"), el.email, el.login_name,
                        f"{self._tr_type}_{self._tr_status}", el.amount, el.wo_account_info, ])
        return res

    def report_file_name(self) -> str:
        return f"{self._tr_type}"

    def get_excel_report(self) -> BytesIO:

        """
            return report and it's name
        """
        output = BytesIO()
        workbook = Workbook(output)
        worksheet_1 = workbook.add_worksheet(name=self._report_file_name)

        # Some data we want to write to the worksheet.
        main_data = self.excel_start_data()
        main_data.extend(self.transactions_processed())

        df_dict = {}
        ExcelReportProcessor.add_to_excel(worksheet=worksheet_1, data=main_data, row=0, col=0)
        df_dict["df1"] = DataFrame(main_data)

        ExcelReportProcessor.adjusting_df(df=df_dict["df1"], worksheet=worksheet_1)

        workbook.close()
        df_dict.clear()

        output.name = "{tr_type}_report.xlsx".format(tr_type=self._tr_type)
        output.seek(0)
        output.flush()
        return output

    @staticmethod
    def set_styles(workbook: Workbook,  worksheet: Worksheet, row: int):
        little_format = workbook.add_format({'font_size': 6, 'text_wrap': 'true'})
        for i in range(2, row+1):
            worksheet.set_row(row=i, cell_format=little_format)

    @staticmethod
    def add_to_excel(worksheet: Worksheet, data: tuple | list | None, row: int, col: int) -> None:
        col_n = copy(col)
        for data_row in data:
            for data_cell in data_row:
                worksheet.write(row, col, data_cell)
                col += 1
            col = col_n
            row += 1

    @staticmethod
    def excel_start_data():
        res = copy(settings.Reports.UT_START)
        return res

    @staticmethod
    def adjusting_df(df: DataFrame, worksheet: Worksheet):
        for idx, col in enumerate(df):  # loop through all columns
            series = df[col]
            max_len = max((
                series.astype(str).map(len).max(),  # len of largest item
                len(str(series.name))  # len of column name/header
            )) + 1  # adding a little extra space
            worksheet.set_column(idx, idx, max_len)

