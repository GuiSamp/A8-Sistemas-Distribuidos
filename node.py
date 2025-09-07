# node.py
import socket
import threading
import json
import sys
import uuid
import datetime
import time
import logging

# Configuração do logging para exibir informações detalhadas
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - (%(threadName)s) %(message)s')

# --- Estruturas de Dados e Configuração ---

# O mural de mensagens é uma lista de dicionários.
# Usamos uma trava (Lock) para garantir que o acesso ao mural seja thread-safe,
# evitando condições de corrida quando múltiplos clientes ou nós tentam modificar a lista ao mesmo tempo.
mural_lock = threading.Lock()
mural = []
known_message_ids = set()

# Simples "banco de dados" de usuários e senhas. Em um sistema real, use hashes de senha.
USERS = {
    "aluno1": "senha123",
    "aluno2": "ifba2025"
}
# Armazena tokens de sessão simples para usuários autenticados.
active_tokens = {}

# --- Funções Auxiliares ---

def create_message(author, content):
    """Cria uma nova mensagem com um ID único e timestamp."""
    return {
        "id": str(uuid.uuid4()),
        "author": author,
        "content": content,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

def add_message_to_mural(message):
    """Adiciona uma mensagem ao mural local de forma segura."""
    with mural_lock:
        if message['id'] not in known_message_ids:
            mural.append(message)
            known_message_ids.add(message['id'])
            # Mantém o mural ordenado por timestamp
            mural.sort(key=lambda x: x['timestamp'])
            logging.info(f"Nova mensagem adicionada ao mural: {message['id']} por {message['author']}")
            return True
    return False

# --- Lógica de Rede: Comunicação entre Nós (Peer-to-Peer) ---

def broadcast_to_peers(message_to_send, own_port):
    """Envia uma mensagem para todos os outros nós (peers)."""
    # Esta função é assíncrona por natureza. Ela não espera por uma resposta.
    # Ela simplesmente tenta enviar a mensagem. Se um nó estiver offline,
    # a conexão falhará, mas o programa continuará.
    message_payload = {
        "type": "replicate",
        "message": message_to_send
    }
    json_payload = json.dumps(message_payload).encode('utf-8')

    for peer in PEER_NODES:
        if peer[1] == own_port: # Não envia para si mesmo
            continue

        # Inicia uma nova thread para cada envio para não bloquear a principal
        threading.Thread(target=send_to_single_peer, args=(peer, json_payload), daemon=True).start()

def send_to_single_peer(peer_address, payload):
    """Tenta enviar um payload para um único nó peer."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(peer_address)
            s.sendall(payload)
            logging.info(f"Mensagem replicada para {peer_address}")
    except ConnectionRefusedError:
        logging.warning(f"Não foi possível conectar ao nó {peer_address} para replicação. Ele pode estar offline.")
    except Exception as e:
        logging.error(f"Erro ao replicar para {peer_address}: {e}")

def handle_peer_connection(conn, addr):
    """Lida com conexões recebidas de outros nós."""
    logging.info(f"Conexão de peer recebida de {addr}")
    try:
        with conn:
            data = conn.recv(4096).decode('utf-8')
            if not data:
                return

            request = json.loads(data)
            req_type = request.get("type")

            if req_type == "replicate":
                # Um peer está enviando uma mensagem para ser replicada
                message = request.get("message")
                if message:
                    add_message_to_mural(message)

            elif req_type == "sync_request":
                # Um peer que acabou de se conectar está pedindo as mensagens que ele não tem
                peer_known_ids = set(request.get("known_ids", []))
                
                with mural_lock:
                    missing_messages = [msg for msg in mural if msg["id"] not in peer_known_ids]
                
                response = {
                    "type": "sync_response",
                    "missing_messages": missing_messages
                }
                conn.sendall(json.dumps(response).encode('utf-8'))
                logging.info(f"Enviando {len(missing_messages)} mensagens faltantes para o peer {addr}")

    except (json.JSONDecodeError, KeyError) as e:
        logging.error(f"Erro de formato nos dados do peer {addr}: {e}")
    except Exception as e:
        logging.error(f"Erro ao lidar com a conexão do peer {addr}: {e}")

def start_peer_server(host, port):
    """Inicia o servidor TCP para ouvir outros nós."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    logging.info(f"Nó ouvindo peers na porta {port}")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_peer_connection, args=(conn, addr), name=f"Peer-{addr}", daemon=True).start()

# --- Lógica de Rede: Comunicação com Clientes ---

def handle_client_connection(conn, addr, own_port):
    """Lida com conexões recebidas de clientes."""
    logging.info(f"Conexão de cliente recebida de {addr}")
    try:
        with conn:
            data = conn.recv(1024).decode('utf-8')
            if not data:
                return

            request = json.loads(data)
            req_type = request.get("type")
            response = {"status": "error", "message": "Requisição inválida"}

            if req_type == "login":
                username = request.get("username")
                password = request.get("password")
                if USERS.get(username) == password:
                    # Gera um token simples. Em produção, use algo mais seguro como JWT.
                    token = f"token_{username}_{uuid.uuid4()}"
                    active_tokens[token] = username
                    response = {"status": "ok", "token": token}
                else:
                    response = {"status": "error", "message": "Usuário ou senha inválidos"}

            elif req_type == "post":
                token = request.get("token")
                content = request.get("content")
                username = active_tokens.get(token)
                if username and content:
                    # Cria a mensagem, adiciona localmente e a replica para os outros nós
                    new_message = create_message(username, content)
                    if add_message_to_mural(new_message):
                        threading.Thread(target=broadcast_to_peers, args=(new_message, own_port)).start()
                        response = {"status": "ok", "message": "Mensagem postada com sucesso"}
                    else:
                        response = {"status": "error", "message": "Mensagem duplicada"}
                else:
                    response = {"status": "error", "message": "Token inválido ou conteúdo vazio"}
            
            elif req_type == "read":
                # Leitura é pública, não requer autenticação
                with mural_lock:
                    # Retorna uma cópia para evitar problemas de concorrência
                    response = {"status": "ok", "mural": list(mural)}

            conn.sendall(json.dumps(response).encode('utf-8'))
    except (json.JSONDecodeError, KeyError) as e:
        logging.error(f"Erro de formato nos dados do cliente {addr}: {e}")
    except Exception as e:
        logging.error(f"Erro ao lidar com a conexão do cliente {addr}: {e}")

def start_client_server(host, port, own_port):
    """Inicia o servidor TCP para ouvir clientes."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    logging.info(f"Nó ouvindo clientes na porta {port}")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client_connection, args=(conn, addr, own_port), name=f"Client-{addr}", daemon=True).start()

# --- Sincronização e Reconciliação (Consistência Eventual) ---

def reconcile_with_peers(own_port):
    """Função executada na inicialização para sincronizar com outros nós."""
    logging.info("Iniciando processo de reconciliação...")
    
    # Pede a um peer aleatório (que não seja ele mesmo) a lista de mensagens
    # Em um sistema real, poderia tentar vários peers se o primeiro falhar.
    peers_to_try = [p for p in PEER_NODES if p[1] != own_port]
    if not peers_to_try:
        logging.info("Nenhum outro peer para sincronizar. Iniciando como nó primário.")
        return

    # Tenta conectar com o primeiro peer da lista
    target_peer = peers_to_try[0]
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(target_peer)
            
            # Envia os IDs das mensagens que já possui
            with mural_lock:
                current_ids = list(known_message_ids)

            request = {
                "type": "sync_request",
                "known_ids": current_ids
            }
            s.sendall(json.dumps(request).encode('utf-8'))
            
            # Recebe a resposta com as mensagens faltantes
            response_data = s.recv(8192).decode('utf-8')
            response = json.loads(response_data)

            if response.get("type") == "sync_response":
                missing_messages = response.get("missing_messages", [])
                logging.info(f"Recebidas {len(missing_messages)} mensagens durante a reconciliação.")
                for msg in missing_messages:
                    add_message_to_mural(msg)
                logging.info("Reconciliação concluída com sucesso.")

    except ConnectionRefusedError:
        logging.warning(f"Peer {target_peer} está offline. Não foi possível sincronizar no momento.")
    except Exception as e:
        logging.error(f"Falha na reconciliação com {target_peer}: {e}")


# --- Ponto de Entrada Principal ---

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python node.py <porta_cliente> <porta_peer> [lista de portas de outros peers]")
        print("Exemplo: python node.py 8000 9000 9001 9002")
        sys.exit(1)

    CLIENT_PORT = int(sys.argv[1])
    PEER_PORT = int(sys.argv[2])
    PEER_PORTS = [int(p) for p in sys.argv[3:]]
    
    HOST = '127.0.0.1' # localhost

    # Lista de todos os nós no sistema (incluindo ele mesmo)
    PEER_NODES = [(HOST, port) for port in PEER_PORTS]

    # Simulação de inicialização ou reconexão: espera um pouco e tenta sincronizar
    time.sleep(2) 
    reconcile_with_peers(PEER_PORT)

    # Inicia a thread para ouvir clientes
    client_thread = threading.Thread(
        target=start_client_server,
        args=(HOST, CLIENT_PORT, PEER_PORT),
        name='ClientServer',
        daemon=True
    )
    client_thread.start()

    # A thread principal irá ouvir outros nós (peers)
    start_peer_server(HOST, PEER_PORT)