from flask import Flask
import os

def create_app():
    # Defina a instância do Flask dentro da função de criação
    app = Flask(__name__)
    app.secret_key = 'sua_chave_secreta_aqui'

    # Configurações de upload
    UPLOAD_FOLDER = 'uploads'
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    # Variáveis globais
    global df_global, mapeamento_cores
    df_global = None
    mapeamento_cores = {}

    # Agora, registre o blueprint (evita a importação circular)
    from routes.routes import routes_bp  # Isso é feito dentro da função para evitar o ciclo
    app.register_blueprint(routes_bp)

    return app

if __name__ == '__main__':
    # Crie e rode o app dentro da função `create_app`
    app = create_app()
    app.run(debug=True)
