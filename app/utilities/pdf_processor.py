import fitz
from io import BytesIO
import rarfile
import zipfile
from base64 import b64encode
from pdfrw import PageMerge, PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from PIL import Image
from werkzeug.datastructures import FileStorage

from logger import logger
from config import settings
from utilities.exceptions import GetFirstPageFromPDFError


class RarZipPdfProcessor:
    def __init__(self, rar_file: bytes,  archive_type: str = "zip"):
        self.rar_archive_data = rar_file
        self.archive_type = archive_type

    @staticmethod
    def get_rar_archive_data(rar_file: str) -> bytes:
        with open(rar_file, 'rb') as rar_file:
            rar_data = rar_file.read()
        return rar_data

    @staticmethod
    def _get_target_pdf_members(members):
        pdf_files = [member for member in members if member.filename.endswith('.pdf')]

        target_pdfs = [
            member for member in pdf_files
            if member.filename.startswith(f"{settings.Pdf.PDF_FOLDER_NAME}/")
        ]

        if target_pdfs:
            return target_pdfs

        return [
            member for member in pdf_files
            if '/' not in member.filename.rstrip('/')
        ]

    @staticmethod
    def _add_pdf_to_writer(pdf_merger: PdfWriter, pdf_data: bytes) -> None:
        pdf_reader = PdfReader(BytesIO(pdf_data))
        for page in pdf_reader.pages:
            pdf_merger.addpage(page)

    def get_extract_and_merge_pdfs(self):
        archive_bytes = BytesIO(self.rar_archive_data)
        archive_bytes.seek(0)
        pdf_merger = PdfWriter()

        if self.archive_type == 'rar':
            with rarfile.RarFile(archive_bytes, 'r') as rf:
                target_pdfs = self._get_target_pdf_members(rf.infolist())
                for file_info in target_pdfs:
                    self._add_pdf_to_writer(pdf_merger, rf.read(file_info.filename))

        elif self.archive_type == 'zip':
            with zipfile.ZipFile(archive_bytes, 'r') as zf:
                target_pdfs = self._get_target_pdf_members(zf.infolist())
                for file_info in target_pdfs:
                    self._add_pdf_to_writer(pdf_merger, zf.read(file_info.filename))

        return self.add_page_numbers(pdf_merger)

    @staticmethod
    def add_page_numbers(pdf_merger: PdfWriter) -> BytesIO:
        pages = list(pdf_merger.pagearray)
        total_pages = len(pages)

        for i, page in enumerate(pages, start=1):
            page_number_text = f"{i} - {total_pages}"
            RarZipPdfProcessor.add_text_to_page(page, page_number_text)

        io_pdf = BytesIO()
        pdf_merger.write(io_pdf)
        io_pdf.seek(0)

        return io_pdf

    @staticmethod
    def add_text_to_page(page, text):
        # Get the width and height of the page
        width = float(page.MediaBox[2]) - float(page.MediaBox[0])
        height = float(page.MediaBox[3]) - float(page.MediaBox[1])

        # Calculate the absolute position based on percentage of canvas size
        tx_absolute = int(width * settings.Pdf.TEXT_TX)
        ty_absolute = int(height * settings.Pdf.TEXT_TY)
        # Create a buffer to hold the PDF data
        overlay_buffer = BytesIO()

        # Create a canvas with ReportLab
        can = canvas.Canvas(overlay_buffer, pagesize=(width, height))
        can.setFontSize(size=settings.Pdf.TEXT_FONT_SIZE)

        # Draw the text on the canvas
        can.drawString(tx_absolute, ty_absolute, text)

        # Save the canvas content to the buffer
        can.save()

        # Reset the buffer position to the beginning
        overlay_buffer.seek(0)

        # Read the generated PDF from the buffer using pdfrw
        overlay_pdf = PdfReader(overlay_buffer)

        # Merge the overlay PDF with the existing page
        PageMerge(page).add(overlay_pdf.pages[0]).render()


def get_first_page_as_image(pdf_file_stream: bytes):
    try:
        pdf_document = fitz.open(stream=pdf_file_stream, filetype='pdf')
        first_page = pdf_document.load_page(0)  # Load the first page

        zoom = 2  # Adjust this value for higher/lower DPI
        mat = fitz.Matrix(zoom, zoom)
        pix = first_page.get_pixmap(matrix=mat)

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_str = b64encode(buffer.getvalue()).decode()

        transaction_image = f"""<img id="bill-modal-image" class="border border-1 rounded img-zoom-orig" onclick="zoom_image();" src="data:image/png;base64,{img_str}">"""
        return transaction_image
    except Exception as e:
        logger.exception("Ошибка при получении первой страницы PDF файла")
        raise GetFirstPageFromPDFError()


def helper_check_attached_file(order_file: FileStorage, order_idn: str) -> tuple[bool, str]:

    filename = order_file.filename.lower()

    # проверка на пустой файл
    if filename == '':
        message = f'{settings.Messages.ORDER_MANAGER_FEXT} {filename}'
        return False, message
    # проверка на человеческий фактор
    if order_idn not in filename:
        message = f'{settings.Messages.ORDER_MANAGER_FON} {filename}'
        return False, message
    # Проверка расширения файла
    if not (filename.endswith('.rar') or filename.endswith('.zip')):
        message = settings.Messages.ORDER_ATTACH_FILE_ERROR + ' Поддерживаются только архивы .zip и .rar!'
        return False, message

    # Чтение файла в память
    file_bytes = BytesIO(order_file.read())
    file_bytes.seek(0)

    try:
        if filename.endswith('.rar'):
            with rarfile.RarFile(file_bytes) as archive:
                members = archive.infolist()
        elif filename.endswith('.zip'):
            with zipfile.ZipFile(file_bytes) as archive:
                members = archive.infolist()
        else:
            message = settings.Messages.ORDER_ATTACH_FILE_ERROR + ' Неподдерживаемый тип архива!'
            return False, message

        # Проверка наличия PDF-файлов в папке 'ЭтикеткиPDF/'
        etik_pdf_files = [
            m for m in members
            if m.filename.startswith('ЭтикеткиPDF/') and m.filename.endswith('.pdf')
        ]

        if etik_pdf_files:
            pass  # Всё ок, pdf в нужной папке есть
        else:
            # Ищем PDF в корне архива
            root_pdf_files = [
                m for m in members
                if m.filename.endswith('.pdf') and '/' not in m.filename.rstrip('/')
            ]
            if not root_pdf_files:
                message = settings.Messages.ORDER_ATTACH_FILE_ERROR + ' В архиве отсутствуют PDF-файлы!'
                return False, message

        file_bytes.seek(0)
        order_file.stream = file_bytes

    except Exception as e:
        message = settings.Messages.ORDER_ATTACH_FILE_ERROR + str(e)
        return False, message

    return True, ''


# if __name__ == '__main__':
#     rar_file = 'test.rar'
#
#     rar_pdf_proc = RarPdfProcessor(rar_file=rar_file)
#     a = rar_pdf_proc.get_extract_and_merge_pdfs()
#
#     output_pdf_path = 'test_processor.pdf'
#     with open(output_pdf_path, 'wb') as output_file:
#         output_file.write(a.read())
