#!/bin/bash

# Instala pacotes Python
pip install -r requirements.txt

# Cria a pasta staticfiles se não existir (para garantir)
mkdir -p staticfiles

# Verifica se a pasta templates está presente
if [ ! -d "templates" ]; then
  echo "Pasta templates não encontrada! Vamos criar."
  mkdir -p templates
fi

# Verifica se a pasta static está presente
if [ ! -d "static" ]; then
  echo "Pasta static não encontrada! Vamos criar."
  mkdir -p static
fi

echo "Build concluído com sucesso!"
