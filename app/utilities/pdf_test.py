from io import BytesIO
import fitz
import rarfile
from PyPDF2 import PdfMerger, PdfReader, PdfWriter, Transformation
from reportlab.pdfgen import canvas

import pdfrw

import threading
from time import time
# Function to merge PDF pages


def time_counter(func):
    def wrapper(*args, **kwargs):
        start_time = time()
        func(*args, **kwargs)
        end_time = time()
        print(f"Time taken: {end_time - start_time} seconds")
    return wrapper


def merge_pdfs(pdf_files, output_file):
    pdf_writer = PdfWriter()

    for pdf_file in pdf_files:
        with open(pdf_file, 'rb') as pdf:
            pdf_reader = PdfReader(pdf)
            # Add each page to the writer object
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                pdf_writer.add_page(page)

    # Write the merged PDF to the output file
    with open(output_file, 'wb') as output:
        pdf_writer.write(output)


# Function to merge PDFs using threading
@time_counter
def merge_pdfs_threaded(pdf_files, output_file, num_threads=4):
    # Split the list of PDF files into chunks based on the number of threads
    chunks = [pdf_files[i::num_threads] for i in range(num_threads)]
    threads = []

    # Create and start threads
    for chunk in chunks:
        thread = threading.Thread(target=merge_pdfs, args=(chunk, output_file))
        thread.start()
        threads.append(thread)

    # Wait for all threads to complete
    for thread in threads:
        thread.join()


@time_counter
def merge_pdfs_nt(pdf_files, output_file):
    pdf_writer = PdfWriter()

    for pdf_file in pdf_files:
        with open(pdf_file, 'rb') as pdf:
            pdf_reader = PdfReader(pdf)
            # Add each page to the writer object
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                pdf_writer.add_page(page)

    # Write the merged PDF to the output file
    with open(output_file, 'wb') as output:
        pdf_writer.write(output)



@time_counter
def merge_pdfs_pdfrw(pdf_files, output_file):
    all_pages = []

    # Collect all pages from input PDFs
    for pdf_file in pdf_files:
        input_pdf = pdfrw.PdfReader(pdf_file)
        all_pages.extend(input_pdf.pages)

    # Write all collected pages to the output PDF
    output_pdf = pdfrw.PdfWriter()
    for page in all_pages:
        output_pdf.addpage(page)

    # Save the merged PDF
    output_pdf.write(output_file)

@time_counter
def merge_pdfs_fitz(pdf_files, output_file):
    output_pdf = fitz.open()

    # Iterate through input PDFs
    for pdf_file in pdf_files:
        input_pdf = fitz.open(pdf_file)

        # Iterate through pages in the input PDF
        for page_number in range(input_pdf.page_count):
            # Extract page content
            page = input_pdf.load_page(page_number)
            output_pdf.insert_pdf(input_pdf, from_page=page_number, to_page=page_number)

        input_pdf.close()

    # Save the merged PDF
    output_pdf.save(output_file)
    output_pdf.close()

# Example usage
if __name__ == "__main__":
    # List of PDF files to merge
    pdf_files = 12000*["cl_1.pdf",]  # Add your PDF files here

    # Output file name
    output_file_1 = "merged_output_1.pdf"
    output_file_2 = "merged_output_2.pdf"

    # Merge PDFs using threading

    # merge_pdfs_nt(pdf_files, output_file_1)
    merge_pdfs_fitz(pdf_files, output_file_1)
    merge_pdfs_pdfrw(pdf_files, output_file_2)

    print("PDFs merged successfully!")
