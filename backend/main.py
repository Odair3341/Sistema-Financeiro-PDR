from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

class Comissao(BaseModel):
    data: str
    cliente: str
    servico: str
    valor_bruto: float
    porcentagem: float
    valor_comissao: float
    status: str
    recebido: float
    restante: float

comissoes_db = [
    {
        "data": "20/05/2025",
        "cliente": "PDR TEAM",
        "servico": "208 - GT-974-PDR",
        "valor_bruto": 1239.00,
        "porcentagem": 17.5,
        "valor_comissao": 216.82,
        "status": "Recebida Parcialmente",
        "recebido": 216.82,
        "restante": 0.00
    },
    {
        "data": "22/05/2025",
        "cliente": "PDR TEAM",
        "servico": "2778,00 - MERCEDES",
        "valor_bruto": 2778.00,
        "porcentagem": 17.5,
        "valor_comissao": 486.15,
        "status": "Recebida Integralmente",
        "recebido": 486.15,
        "restante": 0.00
    },
    {
        "data": "23/05/2025",
        "cliente": "PDR TEAM",
        "servico": "FIAT - GG-216-SDR",
        "valor_bruto": 2304.00,
        "porcentagem": 17.5,
        "valor_comissao": 403.20,
        "status": "Recebida Parcialmente",
        "recebido": 161.48,
        "restante": 241.72
    },
    {
        "data": "23/05/2025",
        "cliente": "PDR TEAM",
        "servico": "P-3 2.0 T - DC-419-BXR",
        "valor_bruto": 1088.00,
        "porcentagem": 17.5,
        "valor_comissao": 190.40,
        "status": "Recebida Integralmente",
        "recebido": 190.40,
        "restante": -0.00
    }
]

@app.get("/")
def read_root():
    return {"message": "Bem-vindo à API do sistema financeiro"}

@app.get("/comissoes", response_model=List[Comissao])
def get_comissoes():
    return comissoes_db