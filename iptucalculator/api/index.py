from flask import Flask, render_template, request, redirect
import sys
import os

# Adicionar o diretório pai ao path para importar a aplicação principal
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar a aplicação Flask existente
from app import app as flask_app

# Este arquivo é o ponto de entrada para o Vercel
# Todas as solicitações são encaminhadas para a aplicação Flask

@flask_app.route('/', defaults={'path': ''})
@flask_app.route('/<path:path>')
def catch_all(path):
    # Tenta renderizar a rota normal primeiro
    try:
        return flask_app.dispatch_request()
    except Exception as e:
        # Se falhar, redireciona para a rota principal
        return redirect('/')

# Necessário para o Vercel
app = flask_app
