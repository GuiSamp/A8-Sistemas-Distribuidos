# A8-Sistemas-Distribuidos
# Sistema de Mural Distribuído

Este projeto implementa um serviço de mural de mensagens compartilhado utilizando uma arquitetura distribuída com múltiplos nós, conforme especificado na atividade da disciplina de Sistemas Distribuídos.

## Requisitos Atendidos

-   **Modelo Arquitetural**: O sistema opera com 3 ou mais nós distribuídos, onde cada um mantém uma cópia local do mural. A comunicação é feita via sockets TCP.
-   **Replicação e Consistência**: Mensagens postadas em um nó são replicadas de forma assíncrona para os outros. O sistema garante consistência eventual.
-   **Autenticação Básica**: Usuários precisam fazer login para postar, mas a leitura do mural é pública.
-   **Simulação de Falhas**: É possível derrubar um nó e, ao reiniciá-lo, ele se reconcilia com a rede para obter as mensagens que perdeu.

## Estrutura do Projeto

-   `node.py`: O código do servidor do nó. Cada processo executando este script atua como um nó independente no sistema.
-   `client.py`: Um cliente de linha de comando para interagir com qualquer um dos nós do sistema.

## Como Executar

### Pré-requisitos

-   Python 3.6 ou superior.
-   Nenhuma biblioteca externa é necessária.

### 1. Iniciar os Nós

Você precisará de pelo menos 3 terminais abertos para simular os 3 nós.

A sintaxe de execução do nó é:
`python node.py <porta_cliente> <porta_peer> [lista de todas as portas_peer no sistema]`

-   `<porta_cliente>`: A porta que este nó usará para ouvir os clientes.
-   `<porta_peer>`: A porta que este nó usará para ouvir outros nós.
-   `[lista de portas_peer]`: A lista completa de portas de **todos** os nós no sistema (incluindo a sua própria) para que eles saibam com quem se comunicar.

**Exemplo com 3 nós:**

1.  **Terminal 1 (Nó A):**
    ```bash
    python node.py 8001 9001 9001 9002 9003
    ```

2.  **Terminal 2 (Nó B):**
    ```bash
    python node.py 8002 9002 9001 9002 9003
    ```

3.  **Terminal 3 (Nó C):**
    ```bash
    python node.py 8003 9003 9001 9002 9003
    ```
    
Os logs em cada terminal mostrarão os nós iniciando e ouvindo nas portas especificadas.

### 2. Usar o Cliente

Abra um novo terminal para o cliente. Você pode se conectar a qualquer um dos nós.

**Sintaxe:** `python client.py <host> <porta_cliente_do_no>`

-   Para se conectar ao **Nó A**:
    ```bash
    python client.py 127.0.0.1 8001
    ```

**Comandos do Cliente:**

-   `ler`: Exibe as mensagens do mural.
-   `login aluno1 senha123`: Faz login com um usuário.
-   `postar Olá, mundo!`: Posta uma mensagem (requer login).
-   `ajuda`: Mostra os comandos.
-   `sair`: Fecha o cliente.

### 3. Simulação de Falha e Reconciliação

1.  **Poste algumas mensagens**: Conecte-se a um nó (ex: 8001), faça login e poste 2 ou 3 mensagens. Use o comando `ler` em clientes conectados a outros nós (8002, 8003) para verificar que as mensagens foram replicadas.

2.  **Derrube um nó**: Vá para o terminal de um dos nós (ex: Nó C, na porta 8003/9003) e pressione `Ctrl+C` para pará-lo.

3.  **Poste mais mensagens**: Com o Nó C offline, conecte-se ao Nó A (8001) e poste uma nova mensagem. Verifique que o Nó B (8002) a recebeu, mas o Nó C, obviamente, não.

4.  **Reconecte o nó falho**: Reinicie o Nó C no seu terminal com o mesmo comando de antes:
    ```bash
    python node.py 8003 9003 9001 9002 9003
    ```

5.  **Verifique a reconciliação**: Os logs do Nó C mostrarão que ele está iniciando o processo de reconciliação, conectando-se a outro peer (o Nó A, neste caso) e baixando as mensagens que perdeu.

6.  **Confirme a consistência**: Conecte um cliente ao Nó C (porta 8003) e use o comando `ler`. Você verá que ele agora possui **todas** as mensagens, incluindo a que foi enviada enquanto ele estava offline, demonstrando a consistência eventual.
