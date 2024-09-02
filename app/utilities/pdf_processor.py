import fitz
from io import BytesIO
import rarfile
from base64 import b64encode
from pdfrw import PageMerge, PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from PIL import Image
from werkzeug.datastructures import FileStorage

from config import settings


class RarPdfProcessor:
    def __init__(self, rar_file):
        self.rar_archive_data = self.get_rar_archive_data(rar_file=rar_file)
        self.pdf_files = []

    @staticmethod
    def get_rar_archive_data(rar_file: str) -> bytes:
        with open(rar_file, 'rb') as rar_file:
            rar_data = rar_file.read()
        return rar_data

    def get_extract_and_merge_pdfs(self):
        with rarfile.RarFile(BytesIO(self.rar_archive_data), 'r') as rf:
            for file_info in rf.infolist():
                if settings.Pdf.PDF_FOLDER_NAME in file_info.filename and file_info.filename.endswith('.pdf'):
                    pdf_data = rf.read(file_info.filename)
                    self.pdf_files.append(BytesIO(pdf_data))

        pdf_merger = PdfWriter()
        for pdf_file in self.pdf_files:
            pdf_reader = PdfReader(pdf_file)
            for page in pdf_reader.pages:
                pdf_merger.addpage(page)

        return self.add_page_numbers(pdf_merger)

    @staticmethod
    def add_page_numbers(pdf_merger: PdfWriter) -> BytesIO:
        io_pdf = BytesIO()
        pdf_merger.write(io_pdf)
        io_pdf.seek(0)

        output = PdfReader(io_pdf)
        for i, page in enumerate(output.pages, start=1):
            page_number_text = f"{i} - {len(output.pages)}"
            RarPdfProcessor.add_text_to_page(page, page_number_text)

        io_pdf = BytesIO()
        io_pdf_writer = PdfWriter()
        io_pdf_writer.addpages(output.pages)
        io_pdf_writer.write(io_pdf)
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
        can.setFontSize(size=6)  # Setting font size to 6

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


def get_first_page_as_image(pdf_path: str):
    pdf_document = fitz.open(pdf_path)
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


def helper_check_attached_file(order_file: FileStorage) -> tuple[bool, str]:
    # Read the file into a BytesIO object
    file_bytes = BytesIO(order_file.read())
    file_bytes.seek(0)

    # Open and extract the RAR file from the BytesIO object
    try:
        with rarfile.RarFile(file_bytes) as rf:
            # Check if 'ЭтикеткиPDF' folder exists
            if not any(member.filename.startswith('ЭтикеткиPDF/') for member in rf.infolist()):
                message = settings.Messages.ORDER_ATTACH_FILE_ERROR + ' нет папки ЭтикеткиPDF в прилагаемом архиве!'
                return False, message
            # Process files in the 'ЭтикеткиPDF' folder only first for files
            pdf_member = next(
                (member for member in rf.infolist()
                 if member.filename.startswith('ЭтикеткиPDF/') and member.filename.endswith('.pdf')),
                None
            )

            if not pdf_member:
                message = settings.Messages.ORDER_ATTACH_FILE_ERROR + ' В папке ЭтикеткиPDF нет pdf или присутствуют файлы с другим расширением!'
                return False, message

            file_bytes.seek(0)
            order_file.stream = file_bytes
    except Exception as e:
        message = settings.Messages.ORDER_ATTACH_FILE_ERROR + str(e)
        return False, message
    else:
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
