from io import BytesIO
import rarfile
from pdfrw import PageMerge, PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


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
        # Create a buffer to hold the PDF data
        overlay_buffer = BytesIO()

        # Create a canvas with ReportLab

        can = canvas.Canvas(overlay_buffer, pagesize=letter)
        can.setFontSize(size=6)  # Setting font size to 6
        # Calculate the absolute position based on percentage of canvas size
        width, height = letter
        tx_absolute = int(width * settings.Pdf.TEXT_TX)
        ty_absolute = int(height * settings.Pdf.TEXT_TY)

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


# if __name__ == '__main__':
#     rar_file = 'test.rar'
#
#     rar_pdf_proc = RarPdfProcessor(rar_file=rar_file)
#     a = rar_pdf_proc.get_extract_and_merge_pdfs()
#
#     output_pdf_path = 'test_processor.pdf'
#     with open(output_pdf_path, 'wb') as output_file:
#         output_file.write(a.read())
