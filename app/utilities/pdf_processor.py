from io import BytesIO
import rarfile
from PyPDF2 import PdfMerger, PdfReader, PdfWriter, Transformation
from reportlab.pdfgen import canvas


from config import settings


class RarPdfProcessor:
    def __init__(self, rar_file):
        self.rar_archive_data = self.get_rar_archive_data(rar_file=rar_file)
        self.pdf_files = []

    @staticmethod
    def get_rar_archive_data(rar_file: str) -> bytes:
        with open(file=rar_file, mode='rb') as rar_file:
            rar_data = rar_file.read()
        return rar_data

    def get_extract_and_merge_pdfs(self):
        with rarfile.RarFile(BytesIO(self.rar_archive_data), 'r') as rf:
            for file_info in rf.infolist():
                if settings.Pdf.PDF_FOLDER_NAME in file_info.filename and file_info.filename.endswith('.pdf'):
                    pdf_data = rf.read(file_info.filename)
                    self.pdf_files.append(BytesIO(pdf_data))
                # else:
                #     return None
        pdf_merger = PdfMerger()
        for pdf_file in self.pdf_files:
            pdf_merger.append(pdf_file)

        return self.add_page_numbers(pdf_merger=pdf_merger)

    @staticmethod
    def add_page_numbers(pdf_merger: PdfMerger) -> BytesIO:
        """
            Add page numbers to each page
        :param pdf_merger:
        :return:
        """

        # Create buffer for editing pages
        io_pdf = BytesIO()
        pdf_merger.write(io_pdf)
        io_pdf.seek(0)

        pdf_reader = PdfReader(io_pdf)
        pdf_writer = PdfWriter()

        pages_quantity = len(pdf_reader.pages)
        for page_number in range(pages_quantity):
            page = pdf_reader.pages[page_number]

            page_number_text = f"{page_number + 1} - {pages_quantity}"
            page.merge_page(RarPdfProcessor.create_text_page(page_number_text, pdf_reader.pages[0].mediabox))

            pdf_writer.add_page(page)

        # Create buffer for returning stream
        io_writer = BytesIO()
        pdf_writer.write(io_writer)
        io_writer.seek(0)
        return io_writer

    @staticmethod
    def create_text_page(text, media_box):
        """
            Create a new page with text as page number
        :param text:
        :param media_box:
        :return:
        """
        packet = BytesIO()
        can = canvas.Canvas(packet)
        can.setFontSize(size=settings.Pdf.TEXT_FONT_SIZE)
        can.drawString(settings.Pdf.TEXT_TX, settings.Pdf.TEXT_TY, text)
        can.save()

        packet.seek(0)
        new_pdf = PdfReader(packet)

        new_page = new_pdf.pages[0]
        new_page.add_transformation(Transformation().translate(0, 0))
        new_page.merge_page(page2=new_page, expand=media_box[3])
        return new_page


# if __name__ == '__main__':
#     rar_file = 'test.rar'
#
#     rar_pdf_proc = RarPdfProcessor(rar_file=rar_file)
#     a = rar_pdf_proc.get_extract_and_merge_pdfs()
#
#     output_pdf_path = 'test_processor.pdf'
#     with open(output_pdf_path, 'wb') as output_file:
#         output_file.write(a.read())
