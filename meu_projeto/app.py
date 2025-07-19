import threading
import webbrowser
import time
from flask import Flask
import os

def create_app():
    app = Flask(__name__)
    app.secret_key = 'sua_chave_secreta_aqui'

    UPLOAD_FOLDER = 'uploads'
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    global df_global, mapeamento_cores
    df_global = None
    mapeamento_cores = {}

    from routes.routes import routes_bp
    app.register_blueprint(routes_bp)

    return app

def abrir_navegador():
    time.sleep(1)
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == '__main__':
    app = create_app()
    
    threading.Thread(target=abrir_navegador).start()

    app.run(debug=True, use_reloader=False)

