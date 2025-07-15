from flask import Flask
import os
from routes.routes import routes_bp

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

# Pasta de upload
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Variáveis globais
df_global = None
mapeamento_cores = {}

app.register_blueprint(routes_bp)

if __name__ == '__main__':
    app.run(debug=True)
