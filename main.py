from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

app = FastAPI()

# --- Modelos de Dados ---
class ClienteInput(BaseModel):
    nome: str = Field(..., max_length=20, description="Nome do cliente (max 20 caracteres)")
    tipo: str = Field(..., pattern="^[NP]$", description="Tipo de atendimento: N (Normal) ou P (Prioritário)")

class Cliente(BaseModel):
    posicao: int
    nome: str
    tipo: str
    data_chegada: datetime
    atendido: bool

# --- Banco de Dados em Memória ---
fila: List[Cliente] = []

# --- Funções Auxiliares ---
def reordenar_fila():
    """
    Percorre a lista e renumera as posições de 1 em diante 
    para todos que ainda não foram atendidos.
    """
    posicao_atual = 1
    for cliente in fila:
        if not cliente.atendido:
            cliente.posicao = posicao_atual
            posicao_atual += 1

# --- Endpoints ---

# 1. GET /fila - Listar clientes na fila
@app.get("/fila")
def listar_fila():
    return [c for c in fila if not c.atendido]

# 2. GET /fila/{id} - Buscar cliente por posição
@app.get("/fila/{id}")
def buscar_cliente(id: int):
    for cliente in fila:
        if cliente.posicao == id and not cliente.atendido:
            return cliente
    raise HTTPException(status_code=404, detail="Cliente não encontrado nesta posição.")

# 3. POST /fila - Adicionar novo cliente COM LÓGICA DE PRIORIDADE (BÔNUS)
@app.post("/fila")
def adicionar_cliente(cliente_in: ClienteInput):
    novo_cliente = Cliente(
        posicao=0, # Será calculado pela função reordenar_fila
        nome=cliente_in.nome,
        tipo=cliente_in.tipo,
        data_chegada=datetime.now(),
        atendido=False
    )

    if cliente_in.tipo == 'N':
        # Se for Normal, simplesmente entra no final da fila
        fila.append(novo_cliente)
    else:
        # Se for Prioritário (P), precisa passar na frente dos Normais (N)
        inserido = False
        for i, cliente in enumerate(fila):
            # Procura o primeiro cliente NÃO atendido que seja NORMAL (N)
            if not cliente.atendido and cliente.tipo == 'N':
                # Insere o prioriotário ANTES desse normal
                fila.insert(i, novo_cliente)
                inserido = True
                break
        
        # Se não encontrou nenhum 'N' (ou a fila só tem 'P's, ou está vazia)
        if not inserido:
            fila.append(novo_cliente)

    # Recalcula as posições (1, 2, 3...) baseada na nova ordem da lista
    reordenar_fila()
    
    return novo_cliente

# 4. PUT /fila - Atualizar fila (Fila anda)
@app.put("/fila")
def atualizar_fila():
    # Verifica se tem alguém na fila para ser atendido
    clientes_na_fila = [c for c in fila if not c.atendido]
    if not clientes_na_fila:
        # Se não tiver ninguém, não faz nada, apenas avisa
        return {"mensagem": "Fila vazia, nada para atualizar."}

    # O primeiro da fila (posicao 1) é atendido
    # Como a lista está ordenada, pegamos o primeiro não atendido
    primeiro_da_fila = clientes_na_fila[0]
    
    # Atualiza o status dele
    primeiro_da_fila.posicao = 0
    primeiro_da_fila.atendido = True

    # Reordena quem sobrou (quem era 2 vira 1, etc.)
    reordenar_fila()
                
    return {"mensagem": "Fila atualizada. Próximo cliente chamado."}

# 5. DELETE /fila/{id} - Remover cliente e reordenar
@app.delete("/fila/{id}")
def remover_cliente(id: int):
    indice_para_remover = -1
    
    # Procura o índice do cliente na lista original
    for i, cliente in enumerate(fila):
        if cliente.posicao == id and not cliente.atendido:
            indice_para_remover = i
            break
            
    if indice_para_remover == -1:
        raise HTTPException(status_code=404, detail="Cliente não encontrado na posição informada.")
        
    # Remove da lista
    fila.pop(indice_para_remover)
    
    # Reordena as posições dos que sobraram para não ficar buraco na numeração
    reordenar_fila()
    
    return {"mensagem": "Cliente removido e fila reordenada."}