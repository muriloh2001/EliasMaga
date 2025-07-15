import os

# Configurações gerais
UPLOAD_FOLDER = 'uploads'
SECRET_KEY = 'sua_chave_secreta_aqui'
MAPEAMENTO_CSV = 'mapeamento_cores.csv'

# Mapeamento automático de cores
MAPEAMENTO_AUTOMATICO = {
    'azul': 'Azul',
    'marinho': 'Marinho',
    'verde': 'Verde',
    'militar': 'Verde',
    'preto': 'Preto',
    'branco': 'Branco',
    'vermelho': 'Vermelho',
    'rosa': 'Rosa',
    'cinza': 'Cinza',
    'amarelo': 'Amarelo',
    'bege': 'Bege',
    'laranja': 'Laranja',
    'roxo': 'Roxo',
    'bordô': 'Vermelho',
    'marrom': 'Marrom'
}

# Colunas relevantes para análise
COLUNAS_RELEVANTES = [
    'codigo_produto', 'nome_produto', 'codigo_loja', 'fornecedor',
    'nome_grupo', 'nome_sub_grupo', 'nome_departamento', 'nome_secao',
    'cor_1', 'cor_2', 'cor_3', 'tamanho', 'Estoque', 'Venda', 'Total', '%Total'
]

# Tipos das colunas ao carregar o CSV
TIPOS_COLUNAS = {
    'codigo_produto': 'str',
    'nome_produto': 'category',
    'codigo_loja': 'int32',
    'fornecedor': 'category',
    'nome_grupo': 'category',
    'nome_sub_grupo': 'category',
    'nome_departamento': 'category',
    'nome_secao': 'category',
    'cor_1': 'category',
    'cor_2': 'category',
    'cor_3': 'category',
    'tamanho': 'category',
    'Estoque': 'int16',
    'Venda': 'float32',
    'Total': 'float32',
    '%Total': 'float32'
}
