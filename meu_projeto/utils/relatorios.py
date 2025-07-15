from io import BytesIO
from fpdf import FPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def gerar_pdf_faltas(faltas):
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Relatório de Faltas", ln=True, align="C")
    pdf.ln(10)

    for falta in faltas:
        linha = f"Cor: {falta['cor_pai']}, Tamanho: {falta['tamanho']}"
        pdf.cell(200, 10, txt=linha, ln=True)

    # Gera o conteúdo do PDF como string Latin1
    pdf_bytes = pdf.output(dest='S').encode('latin1')

    buffer = BytesIO(pdf_bytes)
    buffer.seek(0)
    return buffer

def gerar_pdf_sobras(sobras, codigo_loja=None):
    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", 'B', 14)
            title = "Relatório de Sobras"
            if codigo_loja:
                title += f" - Loja {codigo_loja}"
            self.cell(0, 10, title, ln=True, align='C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", 'I', 8)
            self.cell(0, 10, f'Página {self.page_no()}', align='C')

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    
    # Cabeçalho da tabela com cor de fundo
    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(0)
    pdf.set_draw_color(200, 200, 200)
    
    pdf.cell(83, 10, "Cor Pai", 1, 0, 'C', True)
    pdf.cell(71, 10, "Tamanho", 1, 0, 'C', True)
    pdf.cell(36, 10, "Estoque", 1, 1, 'C', True)

    pdf.set_font("Arial", '', 11)
    for sobra in sobras:
        pdf.cell(83, 8, sobra['cor_pai'], 1, 0, 'C')
        pdf.cell(71, 8, sobra['tamanho'], 1, 0, 'C')
        pdf.cell(36, 8, str(sobra['Estoque']), 1, 1, 'C')


    pdf_bytes = pdf.output(dest='S').encode('latin1')
    buffer = BytesIO(pdf_bytes)
    buffer.seek(0)
    return buffer