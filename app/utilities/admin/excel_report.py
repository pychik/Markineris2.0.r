from datetime import datetime, date
from io import BytesIO
from copy import copy
from typing import Dict, Any, List, Optional

from pandas import DataFrame

from xlsxwriter import Workbook
from xlsxwriter.worksheet import Worksheet

from config import settings
from models import UserTransaction


class ExcelReportProcessor:
    def __init__(self, transactions: list[UserTransaction], transaction_summ: int, tr_status: str,
                 date_range: str, ) -> None:
        self._transactions = transactions
        self._transaction_summ = transaction_summ
        self._date_range = date_range
        self._tr_status = tr_status
        self._report_file_name = self.report_file_name()

    @property
    def transactions(self) -> list:
        return self._transactions

    def transactions_processed(self) -> list:
        res = []
        for el in self.transactions:
            operation_type = settings.Transactions.TRANSACTION_OPERATION_TYPES.get(el.type)
            status = settings.Transactions.TRANSACTIONS.get(el.status)
            sa_row = f"{el.sa_name} ({el.sa_type})" if el.type else ""
            res.append([el.created_at.strftime("%d-%m-%Y %H:%M"), el.email, el.login_name,
                        operation_type, status, el.amount, sa_row,
                        el.wo_account_info, ])
        return res

    def report_file_name(self) -> str:
        return f"{self._tr_status}"

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

        output.name = "{status}_report.xlsx".format(status=self._tr_status)
        output.seek(0)
        output.flush()
        return output

    @staticmethod
    def set_styles(workbook: Workbook, worksheet: Worksheet, row: int):
        little_format = workbook.add_format({'font_size': 6, 'text_wrap': 'true'})
        for i in range(2, row + 1):
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
        return copy(settings.Reports.UT_START_FILL)

    @staticmethod
    def adjusting_df(df: DataFrame, worksheet: Worksheet):
        for idx, col in enumerate(df):  # loop through all columns
            series = df[col]
            max_len = max((
                series.astype(str).map(len).max(),  # len of largest item
                len(str(series.name))  # len of column name/header
            )) + 1  # adding a little extra space
            worksheet.set_column(idx, idx, max_len)


class ExcelReportMixin:
    """
    extend excel report
    """

    def set_column_width(self, sheet):
        col_widths = {}
        filter_data = []
        if self.filters:
            filter_data = list(zip(self.filters.keys(), self.filters.values()))
        all_data = filter_data + (
            [self.columns_name] if self.columns_name else []) + self.data
        for row in all_data:
            for col_idx, cell_value in enumerate(row):
                if cell_value:
                    col_widths[col_idx] = max(col_widths.get(col_idx, 0), len(str(cell_value)))
        for col_idx, width in col_widths.items():
            sheet.set_column(col_idx, col_idx, width + 2)


class ExcelReportWithSheetMixin:
    """
    extend excel report
    """
    filters: Optional[Dict[str, Any]] = None,
    columns_name: Optional[List[str]] = None,
    data: Optional[List] = None

    def set_column_width(self, sheet):
        col_widths = {}
        filter_data = []
        if self.filters:
            filter_data = list(zip(self.filters.keys(), self.filters.values()))
        all_data = filter_data + (
            [self.columns_name] if self.columns_name else []) + list(self.data[sheet.name])

        for row in all_data:
            for col_idx, cell_value in enumerate(row):
                if cell_value:
                    col_widths[col_idx] = max(col_widths.get(col_idx, 0), len(str(cell_value)))
        for col_idx, width in col_widths.items():
            sheet.set_column(col_idx, col_idx, width + 2)


class BaseExcelReport(ExcelReportMixin):
    """
    Base class for Excel report
    data: main data to save
    filters: dictionary with filters name and value
    output_file_name: output file name without extensions
    sheet_name: name of sheet
    columns_name: list of main data columns name
    cell_condition_format: dict with keys as column index and values with
    """

    def __init__(
            self,
            data: List,
            condition_format: Optional[dict[int, dict]],
            filters: Optional[Dict[str, Any]] = None,
            columns_name: Optional[List[str]] = None,
            sheet_name: Optional[str] = 'sheet 1',
            output_file_name: Optional[str] = 'WorkBook.xlsx',
    ):
        self.filters = filters
        self.data = data
        self.sheet_name = sheet_name
        self.columns_name = columns_name
        self.output_file_name = f'{output_file_name}.xlsx'
        self.output = BytesIO()
        self.workbook = Workbook(self.output)
        self.condition_format = condition_format


class ExcelReport(BaseExcelReport):

    def __init__(
            self,
            data: List,
            condition_format: Optional[dict[int, list]] = None,
            filters: Optional[Dict[str, Any]] = None,
            columns_name: Optional[List[str]] = None,
            sheet_name: Optional[str] = 'sheet 1',
            output_file_name: Optional[str] = 'WorkBook.xlsx',
    ) -> None:
        """
        data: list of data to save in file
        filters: dictionary with filters name and value
        output_file_name: output file name without extensions
        """
        super().__init__(data=data,
                         filters=filters,
                         columns_name=columns_name,
                         sheet_name=sheet_name,
                         output_file_name=output_file_name,
                         condition_format=condition_format,
                         )
        self.col_name_and_filter_formatter = self.workbook.add_format(settings.ExcelFormatting.FILTER_AND_COL_NAME_FORMATTER)
        self.main_data_formatter = self.workbook.add_format(settings.ExcelFormatting.MAIN_DATA_FORMATTER)
        self.date_formatter = self.workbook.add_format(settings.ExcelFormatting.DATE_FORMATTER)
        self.datetime_formatter = self.workbook.add_format(settings.ExcelFormatting.DATETIME_FORMATTER)

    def create_report(self) -> BytesIO:

        sheet = self.workbook.add_worksheet(self.sheet_name)
        row = self.add_filters_and_column_name(sheet, self.col_name_and_filter_formatter)
        self.write_main_data(row, sheet, self.main_data_formatter)
        self.set_column_width(sheet)
        self.workbook.close()
        self.output.seek(0)
        self.output.flush()
        return self.output

    def write_main_data(self, row: int, sheet: Worksheet, formatters):
        col = 0
        for data_row in self.data:
            for value in data_row:
                if type(value) is datetime:
                    sheet.write_datetime(row, col, value, self.datetime_formatter)
                elif type(value) is date:
                    sheet.write_datetime(row, col, value, self.date_formatter)
                else:
                    sheet.write(row, col, value, formatters)

                if self.condition_format:
                    self.apply_condition_formatting(col, row, sheet=sheet)

                col += 1

            col = 0
            row += 1

    def add_filters_and_column_name(self, sheet: Worksheet, formatters) -> int:
        """
        add filters and column name to sheet
        return: index of next row to write in
        """
        row, col = 0, 0
        if self.filters:
            for filter_name, filter_value in self.filters.items():
                sheet.write(row, col, filter_name, formatters)
                sheet.write(row, col + 1, filter_value)
                row += 1
            row += 1
        if self.columns_name:
            col = 0
            for column_name in self.columns_name:
                sheet.write(row, col, column_name, formatters)
                col += 1
            row += 1
        return row

    def apply_condition_formatting(self, col: int, row: int, sheet: Worksheet, ):
        if col in self.condition_format.keys():
            for condition in self.condition_format[col]:
                sheet.conditional_format(row, col, row, col, {
                    'type': condition.get('type'),
                    'criteria': condition.get('criteria'),
                    'value': condition.get('value'),
                    'format': self.workbook.add_format(condition.get('format')),
                })


class ExcelReportWithSheets(ExcelReportWithSheetMixin):
    def __init__(
            self,
            report_data: dict[str, list],
            filters: Optional[Dict[str, Any]] = None,
            columns_name: Optional[List[str]] = None,
            output_file_name: str = 'report.xlsx'
    ):
        self.filters = filters
        self.data = report_data
        self.columns_name = columns_name
        self.output_file_name = f'{output_file_name}.xlsx'
        self.output = BytesIO()
        self.workbook = Workbook(self.output)
        self.date_formatter = self.workbook.add_format(settings.ExcelFormatting.DATE_FORMATTER)
        self.datetime_formatter = self.workbook.add_format(settings.ExcelFormatting.DATETIME_FORMATTER)
        self.main_data_formatter = self.workbook.add_format(settings.ExcelFormatting.MAIN_DATA_FORMATTER)
        self.col_name_and_filter_formatter = self.workbook.add_format(settings.ExcelFormatting.FILTER_AND_COL_NAME_FORMATTER)

    def create_sheets(self) -> None:
        for sheet_name in self.data.keys():
            self.workbook.add_worksheet(sheet_name)

    def write_main_data(self, row, sheet: Worksheet) -> None:
        col = 0
        for data_row in self.data[sheet.name]:
            for value in data_row:
                if isinstance(value, datetime):
                    sheet.write_datetime(row, col, value, self.date_formatter)
                if isinstance(value, date):
                    sheet.write_datetime(row, col, value, self.datetime_formatter)
                else:
                    sheet.write(row, col, value, self.main_data_formatter)
                col += 1

            col = 0
            row += 1

    def add_filters_and_column_name(self, sheet: Worksheet) -> int:
        """
        add filters and column name to sheet
        return: index of next row to write in
        """
        row, col = 0, 0
        if self.filters:
            for filter_name, filter_value in self.filters.items():
                sheet.write(row, col, filter_name, self.col_name_and_filter_formatter)
                sheet.write(row, col + 1, filter_value)
                row += 1
            row += 1
        if self.columns_name:
            col = 0
            for column_name in self.columns_name:
                sheet.write(row, col, column_name, self.col_name_and_filter_formatter)
                col += 1
            row += 1
        return row

    def create_report(self):
        self.create_sheets()
        for sheet in self.workbook.worksheets():
            row = self.add_filters_and_column_name(sheet)
            self.write_main_data(row, sheet)
            self.set_column_width(sheet)
        self.workbook.close()
        self.output.seek(0)
        self.output.flush()
        return self.output
