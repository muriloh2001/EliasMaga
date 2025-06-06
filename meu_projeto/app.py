from flask import Flask, request, render_template
import pandas as pd
import os
from flask import redirect, url_for
from flask import Flask, request, render_template, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

df_global = None  # Armazena o DataFrame carregado

# Dicionário de mapeamento de cores para cor pai
mapeamento_cores = {
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

def classificar_cor_pai(cor):
    if pd.isna(cor):
        return 'Desconhecido'
    cor = cor.lower()
    for palavra, cor_pai in mapeamento_cores.items():
        if palavra in cor:
            return cor_pai
    return 'Outras'

@app.route('/', methods=['GET', 'POST'])
def index():
    global df_global

    if request.method == 'POST' and 'file' in request.files:
        arquivo = request.files['file']
        if arquivo:
            caminho = os.path.join(app.config['UPLOAD_FOLDER'], arquivo.filename)
            arquivo.save(caminho)

            if arquivo.filename.endswith('.csv'):
                df_global = pd.read_csv(caminho)
            elif arquivo.filename.endswith(('.xls', '.xlsx')):
                df_global = pd.read_excel(caminho)
            else:
                flash("Formato de arquivo não suportado!", "error")
                return redirect(url_for('index'))

            df_global['cor_pai'] = df_global['cor_1'].apply(classificar_cor_pai)

            flash("Arquivo carregado com sucesso! Você pode ir para a página de análise.", "success")
            return redirect(url_for('analise'))

    return render_template('index.html')



@app.route('/classificar_cores', methods=['GET'])
def classificar_cores():
    global df_global

    if df_global is None or 'cor_1' not in df_global.columns:
        return "Nenhum arquivo carregado ou coluna 'cor_1' ausente."

    # Cores únicas da planilha
    cores_unicas = df_global['cor_1'].dropna().unique()

    # Gera sugestões com base na função automática
    sugestoes = [
        {
            'cor_1': cor,
            'cor_pai_sugerida': classificar_cor_pai(cor)
        }
        for cor in cores_unicas
    ]

    return render_template('classificar_cores.html', sugestoes=sugestoes)

@app.route('/atualizar_cores', methods=['POST'])
def atualizar_cores():
    global df_global

    if df_global is None:
        return "Nenhum arquivo carregado."

    # Cria um dicionário de correções enviadas
    novas_classificacoes = {}
    for key in request.form:
        if key.startswith('cor_'):
            cor_original = key[4:]  # remove 'cor_' do início
            nova_cor_pai = request.form[key]
            novas_classificacoes[cor_original] = nova_cor_pai

    # Aplica as classificações manualmente
    def classificar_manual(cor):
        if pd.isna(cor):
            return 'Desconhecido'
        return novas_classificacoes.get(cor, 'Outras')

    df_global['cor_pai'] = df_global['cor_1'].apply(classificar_manual)

    return redirect(url_for('index'))

@app.route('/analise', methods=['GET', 'POST'])
def analise():
    global df_global

    if df_global is None:
        return "Nenhum arquivo foi carregado ainda."

    sub_grupos = sorted(df_global['nome_sub_grupo'].dropna().unique())
    secoes = sorted(df_global['nome_secao'].dropna().unique())
    produtos = sorted(df_global['nome_produto'].dropna().unique())

    filtro_sub_grupo = request.form.get('nome_sub_grupo') or ''
    filtro_secao = request.form.get('nome_secao') or ''
    filtro_produto = request.form.get('nome_produto') or ''

    df_filtrado = df_global.copy()

    if filtro_sub_grupo:
        df_filtrado = df_filtrado[df_filtrado['nome_sub_grupo'] == filtro_sub_grupo]
    if filtro_secao:
        df_filtrado = df_filtrado[df_filtrado['nome_secao'] == filtro_secao]
    if filtro_produto:
        df_filtrado = df_filtrado[df_filtrado['nome_produto'] == filtro_produto]

    if not df_filtrado.empty:
        total_por_loja = df_filtrado.groupby('codigo_loja')['Estoque'].sum().reset_index()
        tem_dados = True
    else:
        total_por_loja = None
        tem_dados = False

    return render_template(
        'analise.html',
        sub_grupos=sub_grupos,
        secoes=secoes,
        produtos=produtos,
        filtro_sub_grupo=filtro_sub_grupo,
        filtro_secao=filtro_secao,
        filtro_produto=filtro_produto,
        total_por_loja=total_por_loja,
        tem_dados=tem_dados
    )


if __name__ == '__main__':
    app.run(debug=True)
