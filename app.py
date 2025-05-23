from flask import Flask, jsonify, request
from flask_cors import CORS
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Inicializando o Flask
app = Flask(__name__)

# Habilitar CORS para aceitar requisições de qualquer origem
CORS(app)

# Obtendo a chave da API do Google
API_KEY = os.getenv("GOOGLE_API_KEY")

# Configurando o cliente Gemini
genai.configure(api_key=API_KEY)

# Criando o modelo GenerativeModel
# Use 'gemini-1.5-flash-latest' ou 'gemini-pro' ou outro modelo válido
# 'gemini-2.0-flash' não é um nome de modelo válido.
# Usaremos 'gemini-1.5-flash-latest' por ser rápido e capaz.
gemini_model = genai.GenerativeModel(
    model_name='gemini-1.5-flash-latest',
    generation_config={"response_mime_type": "application/json"} # Configuração aqui
)

def criar_historia(detalhes_lista):
    """
    Função para criar uma história baseada nos detalhes fornecidos.
    Envia uma requisição para a API do Gemini.
    'detalhes_lista' é esperado ser uma lista [titulo_sugerido, prompt_principal]
    """
    if len(detalhes_lista) < 2:
        return {"error": "Título sugerido e prompt principal são necessários."}

    titulo_sugerido = detalhes_lista[0]
    prompt_principal = detalhes_lista[1]

    prompt = f"""
        Crie uma história baseada nos seguintes detalhes:
        Título Sugerido (pode ser adaptado por você): "{titulo_sugerido}"
        Ideia principal, tema ou elementos da história: "{prompt_principal}"

        - O conteúdo deve ter pelo menos uma narrativa completa, com diálogos e descrições, deixando a história rica e interessante, com começo, meio e fim.
        - personagens tem sua fala entre aspas.
        - separe cada parte em parágrafos.
        - a fala dos personagens deve ser em outro parágrafo.
        - crie um título criativo, se necessário, prefira o título sugerido.
        A história deve ser envolvente e criativa, com um começo, meio e fim.
        Retorne APENAS um objeto JSON com as seguintes chaves e tipos:
        - "titulo": uma string contendo o título da história.
        - "conteudo": uma string contendo o corpo da história.


        Exemplo do formato JSON esperado:
        {{
            "titulo": "O Segredo da Montanha Cintilante",
            "conteudo": "Era uma vez, em um vale escondido, uma montanha que brilhava ao luar..."
        }}
    """

    try:
        print(f"Enviando prompt para Gemini: {prompt[:200]}...") # Log para debug
        response = gemini_model.generate_content(contents=prompt)

        # Debug: Imprimir o que a API Gemini retornou
        print(f"Resposta bruta da Gemini (candidates type): {type(response.candidates)}")
        if response.candidates:
            print(f"Primeiro candidato: {response.candidates[0]}")
            if response.candidates[0].content and response.candidates[0].content.parts:
                 print(f"Texto do primeiro candidato: {response.candidates[0].content.parts[0].text[:200]}...")


        # A API, com response_mime_type="application/json", deve retornar o JSON na parte de texto.
        # O acesso mais robusto é via candidates.
        if not response.candidates or not response.candidates[0].content or not response.candidates[0].content.parts:
            print("Resposta da Gemini não tem o conteúdo esperado.")
            return {"error": "Resposta da IA inválida ou vazia."}

        json_text_from_gemini = response.candidates[0].content.parts[0].text
        
        # Processando a resposta (que deve ser uma string JSON)
        response_data = json.loads(json_text_from_gemini)
        
        # Validação básica do JSON retornado pela IA
        if not isinstance(response_data, dict) or "titulo" not in response_data or "conteudo" not in response_data:
            print(f"JSON da Gemini não tem 'titulo' ou 'conteudo'. Recebido: {response_data}")
            return {"error": "A IA retornou um formato de dados inesperado."}
            
        return response_data

    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar JSON da Gemini: {e}")
        print(f"Texto que falhou no parse: {json_text_from_gemini}")
        return {"error": f"Erro ao processar resposta da IA (JSON inválido): {e}"}
    except Exception as e:
        # Captura outros erros da API Gemini ou do processamento
        print(f"Erro ao chamar API Gemini ou processar resposta: {e}")
        # Imprime mais detalhes se for um erro específico da API Gemini
        if hasattr(e, 'response') and e.response:
            print(f"Detalhes do erro da API: {e.response}")
        return {"error": f"Erro na comunicação com a IA: {str(e)}"}


@app.route('/historia', methods=['POST'])
def make_historia():
    try:
        dados = request.get_json()

        if not dados or not isinstance(dados, dict):
            return jsonify({'error': 'Requisição JSON inválida. Esperava um dicionário.'}), 400

        detalhes = dados.get('detalhes', [])

        if not isinstance(detalhes, list):
            return jsonify({'error': 'O campo "detalhes" deve ser uma lista.'}), 400

        # Agora esperamos 2 detalhes: título e prompt principal
        if len(detalhes) < 2:
            return jsonify({'error': 'São necessários um título sugerido e o prompt da história.'}), 400

        # Chama a função que gera a história
        historia_gerada = criar_historia(detalhes) # Renomeada para clareza

        # Se criar_historia retornou um erro, repasse-o
        if 'error' in historia_gerada:
            return jsonify(historia_gerada), 400 # Pode ser 500 se for erro interno da IA
        
        return jsonify(historia_gerada), 200

    except Exception as e:
        print(f"Erro interno na API Flask: {e}")
        # Adiciona traceback para debug no servidor
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erro interno no servidor: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') # host='0.0.0.0' para ser acessível na rede local se necessário