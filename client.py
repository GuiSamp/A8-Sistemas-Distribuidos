# client.py
import socket
import json
import sys

class MuralClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.token = None

    def _send_request(self, request):
        """Função auxiliar para enviar uma requisição e receber a resposta."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                s.sendall(json.dumps(request).encode('utf-8'))
                response_data = s.recv(8192).decode('utf-8')
                return json.loads(response_data)
        except ConnectionRefusedError:
            print(f"Erro: Não foi possível conectar ao nó em {self.host}:{self.port}. O nó está offline?")
        except Exception as e:
            print(f"Ocorreu um erro de comunicação: {e}")
        return None

    def login(self, username, password):
        """Autentica o usuário e armazena o token de sessão."""
        request = {
            "type": "login",
            "username": username,
            "password": password
        }
        response = self._send_request(request)
        if response and response.get("status") == "ok":
            self.token = response.get("token")
            print("Login realizado com sucesso!")
        elif response:
            print(f"Falha no login: {response.get('message')}")

    def post_message(self, content):
        """Posta uma nova mensagem no mural (requer login)."""
        if not self.token:
            print("Você precisa fazer login para postar uma mensagem.")
            return

        request = {
            "type": "post",
            "token": self.token,
            "content": content
        }
        response = self._send_request(request)
        if response and response.get("status") == "ok":
            print("Mensagem postada com sucesso!")
        elif response:
            print(f"Erro ao postar mensagem: {response.get('message')}")

    def read_mural(self):
        """Lê e exibe todas as mensagens do mural."""
        request = {"type": "read"}
        response = self._send_request(request)
        if response and response.get("status") == "ok":
            mural = response.get("mural", [])
            if not mural:
                print("\n--- MURAL COMPARTILHADO (vazio) ---")
            else:
                print("\n--- MURAL COMPARTILHADO ---")
                for msg in mural:
                    # Formata o timestamp para melhor leitura
                    ts = datetime.datetime.fromisoformat(msg['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"[{ts}] {msg['author']}: {msg['content']}")
                print("----------------------------\n")
        elif response:
            print(f"Erro ao ler o mural: {response.get('message')}")

def print_help():
    """Exibe o menu de ajuda."""
    print("\nComandos disponíveis:")
    print("  ler                - Exibe as mensagens do mural.")
    print("  postar <mensagem>  - Posta uma nova mensagem (requer login).")
    print("  login <user> <pass> - Faz login no sistema.")
    print("  ajuda              - Mostra este menu de ajuda.")
    print("  sair               - Encerra o cliente.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python client.py <host> <porta_cliente>")
        sys.exit(1)
        
    import datetime # Importa aqui porque só é usado na formatação de data

    HOST = sys.argv[1]
    PORT = int(sys.argv[2])

    client = MuralClient(HOST, PORT)
    print(f"Cliente conectado ao nó em {HOST}:{PORT}")
    print("Digite 'ajuda' para ver a lista de comandos.")

    while True:
        try:
            command_line = input("> ").strip().split(" ", 2)
            command = command_line[0].lower()

            if command == "sair":
                break
            elif command == "ajuda":
                print_help()
            elif command == "ler":
                client.read_mural()
            elif command == "login":
                if len(command_line) == 3:
                    client.login(command_line[1], command_line[2])
                else:
                    print("Uso: login <usuario> <senha>")
            elif command == "postar":
                if len(command_line) >= 2:
                    content = " ".join(command_line[1:])
                    client.post_message(content)
                else:
                    print("Uso: postar <sua mensagem aqui>")
            else:
                print("Comando desconhecido. Digite 'ajuda' para ver as opções.")
        except KeyboardInterrupt:
            print("\nSaindo...")
            break