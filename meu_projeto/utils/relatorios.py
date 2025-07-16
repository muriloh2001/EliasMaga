from io import BytesIO
from fpdf import FPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def gerar_pdf_faltas_grade(grade_faltas, todos_tamanhos, codigo_loja=None, nome_grupo=None):
    from fpdf import FPDF

    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", 'B', 14)
            title = "Relatório de Faltas"
            if codigo_loja:
                title += f" - Loja {codigo_loja}"
            if nome_grupo:
                title += f" - Grupo: {nome_grupo}"
            self.cell(0, 10, title, ln=True, align='C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", 'I', 8)
            self.cell(0, 10, f'Página {self.page_no()}', align='C')

    pdf = PDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 10)

    largura_total = 297 - 20
    num_colunas = 1 + len(todos_tamanhos)
    col_width = largura_total / num_colunas
    row_height = 8

    pdf.set_fill_color(240, 240, 240)
    pdf.cell(col_width, row_height, "Cor Pai", 1, 0, 'C', True)
    for tam in todos_tamanhos:
        pdf.cell(col_width, row_height, tam, 1, 0, 'C', True)
    pdf.ln()

    pdf.set_font("Arial", '', 10)
    for cor, tamanhos in grade_faltas.items():
        pdf.cell(col_width, row_height, cor, 1, 0, 'C')
        for tam in todos_tamanhos:
            valor = tamanhos.get(tam, '')
            pdf.cell(col_width, row_height, valor if valor else '', 1, 0, 'C')
        pdf.ln()

    buffer = BytesIO(pdf.output(dest='S').encode('latin1'))
    buffer.seek(0)
    return buffer


def gerar_pdf_sobras_grade(grade_sobras, todos_tamanhos, codigo_loja=None, nome_grupo=None):
    from fpdf import FPDF

    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", 'B', 14)
            title = "Relatório de Sobras"
            if codigo_loja:
                title += f" - Loja {codigo_loja}"
            if nome_grupo:
                title += f" - Grupo: {nome_grupo}"
            self.cell(0, 10, title, ln=True, align='C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", 'I', 8)
            self.cell(0, 10, f'Página {self.page_no()}', align='C')

    pdf = PDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()

    largura_total = 297 - 20
    num_colunas = 1 + len(todos_tamanhos)
    col_width = largura_total / num_colunas
    row_height = 8

    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(col_width, row_height, "Cor Pai", 1, 0, 'C', True)
    for tam in todos_tamanhos:
        pdf.cell(col_width, row_height, tam, 1, 0, 'C', True)
    pdf.ln()

    pdf.set_font("Arial", '', 10)
    for cor, tamanhos in grade_sobras.items():
        pdf.cell(col_width, row_height, cor, 1, 0, 'C')
        for tam in todos_tamanhos:
            valor = tamanhos.get(tam, 0)
            pdf.cell(col_width, row_height, str(valor), 1, 0, 'C')
        pdf.ln()

    buffer = BytesIO(pdf.output(dest='S').encode('latin1'))
    buffer.seek(0)
    return buffer
