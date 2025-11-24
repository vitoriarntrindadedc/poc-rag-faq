import streamlit as st
import boto3
from botocore.exceptions import ClientError

# ==========================================

# Modelo Claude
MODEL_ARN = "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0"
# ==========================================
# 2. CONFIGURAÇÃO DA PÁGINA & ESTILO
# ==========================================
st.set_page_config(page_title="FAQ Assistant", page_icon="💬", layout="centered")

# CSS para deixar a interface mais limpa e moderna
st.markdown("""
<style>
    .stChatMessage {
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .stTextInput input {
        border-radius: 20px;
    }
    h1 {
        color: #2C3E50;
        font-family: 'Helvetica', sans-serif;
    }
    /* Remove o menu hambúrguer padrão para parecer um app */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ==========================================
# 3. CONEXÃO COM AWS BEDROCK
# ==========================================
@st.cache_resource
def get_bedrock_client():
    try:
        return boto3.client(
            service_name="bedrock-agent-runtime",
            region_name=st.secrets["AWS_REGION"],
            aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"]
        )
    except Exception as e:
        st.error(f"Erro fatal na conexão AWS: {e}")
        return None


client = get_bedrock_client()


def query_bedrock(question):
    """
    Função que chama o retrieve_and_generate com o prompt personalizado
    """
    # Prompt System para garantir a persona gentil
    prompt_template = """
    Você é um assistente virtual de atendimento, muito gentil, paciente e humano.
    Sua função é tirar dúvidas da equipe com base na FAQ da empresa.

    Diretrizes:
    - Use emojis moderadamente para soar amigável (ex: 😊, ✅).
    - Se a resposta não estiver no contexto, peça desculpas gentilmente e diga que não sabe.
    - NUNCA invente informações fora do contexto fornecido.
    - Seja conciso mas acolhedor.

    Contexto da FAQ:
    $search_results$

    Pergunta do usuário: 
    """

    try:
        response = client.retrieve_and_generate(
            input={"text": question},
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseId": st.secrets["KNOWLEDGE_BASE_ID"],
                    "modelArn": MODEL_ARN,
                    "generationConfiguration": {
                        "promptTemplate": {
                            "textPromptTemplate": prompt_template
                        },
                        "inferenceConfig": {
                            "textInferenceConfig": {
                                "temperature": 0.3,  #  para máxima fidelidade ao documento
                                "maxTokens": 1000
                            }
                        }
                    }
                }
            }
        )
        return response["output"]["text"]

    except ClientError as e:
        return f"⚠️ Erro na AWS: {e}"
    except Exception as e:
        return f"⚠️ Erro inesperado: {e}"


# ==========================================
# 4. INTERFACE DO CHAT (FRONTEND)
# ==========================================

st.title("💬 Autoatendimento FAQ")
st.markdown("Bem-vindo! Tire suas dúvidas sobre os processos da empresa de forma rápida.")

# Inicializa histórico
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Olá! Tudo bem? 😊 Sou seu assistente virtual. Como posso ajudar você hoje?"}
    ]

# Renderiza histórico na tela
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Captura entrada do usuário
if prompt := st.chat_input("Digite sua pergunta aqui..."):

    # 1. Mostra pergunta do usuário
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Gera resposta (com loading)
    with st.chat_message("assistant"):
        with st.spinner("Consultando a base de conhecimento..."):
            if client:
                resposta = query_bedrock(prompt)
            else:
                resposta = "Erro: Cliente AWS não inicializado."

            st.markdown(resposta)

    # 3. Salva resposta no histórico
    st.session_state.messages.append({"role": "assistant", "content": resposta})