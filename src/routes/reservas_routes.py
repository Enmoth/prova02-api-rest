import random

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import select

from src.config.database import get_session
from src.models.reservas_model import Reserva
from src.models.voos_model import Voo

reservas_router = APIRouter(prefix="/reservas")


@reservas_router.get("/{id_voo}")
def lista_reservas_voo(id_voo: int):
    with get_session() as session:
        statement = select(Reserva).where(Reserva.voo_id == id_voo)
        reservas = session.exec(statement).all()
        return reservas

# RESERVA
@reservas_router.post("")
def cria_reserva(reserva: Reserva):
    with get_session() as session:
        voo = session.exec(select(Voo).where(Voo.id == reserva.voo_id)).first()

        if not voo:
            return JSONResponse(
                content={"message": f"Voo com id {reserva.voo_id} não encontrado."},
                status_code=404,
            )
        
        # ---
        # Verificar se já existe uma reserva com o mesmo documento para o mesmo voo
        reserva_existente = (
            session.query(Reserva)
            .filter(Reserva.voo_id == reserva.voo_id, Reserva.documento == reserva.documento)
            .first()
        )

        # Retorna uma exception caso exista
        if reserva_existente:
            raise HTTPException(
                status_code=400,
                detail=f"Já existe uma reserva com o documento {reserva.documento} para este voo.",
            )
        # ---
        codigo_reserva = "".join(
            [str(random.randint(0, 999)).zfill(3) for _ in range(2)]
        )

        reserva.codigo_reserva = codigo_reserva
        session.add(reserva)
        session.commit()
        session.refresh(reserva)
        return reserva

# CHECKIN
@reservas_router.post("/{codigo_reserva}/checkin/{num_poltrona}")
def faz_checkin(codigo_reserva: str, num_poltrona: int):
    with get_session() as session:

        reserva = (
            session.query(Reserva)
            .filter(Reserva.codigo_reserva == codigo_reserva)
            .first()
        )

        if not reserva:
            raise HTTPException(
                status_code=404,
                detail=f"Reserva com código {codigo_reserva} não encontrada.",
            )
        
        # Valida se a poltrona existe, com base no model de voos
        if num_poltrona < 1 or num_poltrona > 9:
            raise HTTPException(
                status_code=400,
                detail="Número de poltrona inválido. Deve ser um número entre 1 e 9.",
            )

        # Verificar se a poltrona está disponível
        poltrona_field = f"poltrona_{num_poltrona}"
        if getattr(reserva.voo, poltrona_field):
            raise HTTPException(
                status_code=400,
                detail=f"Poltrona {num_poltrona} já reservada para este voo.",
            )

        # Marcar a poltrona como reservada
        setattr(reserva.voo, poltrona_field, reserva.documento)
        session.commit()

        return {"message": f"Check-in realizado para a poltrona {num_poltrona} com sucesso."}


# TROCA DE POLTRONAS
@reservas_router.patch("/{codigo_reserva}/troca/{poltrona_origem}/{poltrona_destino}")
def troca_reserva_poltrona_patch(codigo_reserva: str, poltrona_origem: int, poltrona_destino: int):
    with get_session() as session:
        reserva = (
            session.query(Reserva)
            .filter(Reserva.codigo_reserva == codigo_reserva)
            .first()
        )

        if not reserva:
            raise HTTPException(
                status_code=404,
                detail=f"Reserva com código {codigo_reserva} não encontrada.",
            )

        if poltrona_origem < 1 or poltrona_origem > 9 or poltrona_destino < 1 or poltrona_destino > 9:
            raise HTTPException(
                status_code=400,
                detail="Número de poltrona inválido. Deve ser um número entre 1 e 9.",
            )

        poltrona_origem_field = f"poltrona_{poltrona_origem}"
        poltrona_destino_field = f"poltrona_{poltrona_destino}"

        if getattr(reserva.voo, poltrona_origem_field) != reserva.documento:
            raise HTTPException(
                status_code=400,
                detail=f"Você só pode trocar uma poltrona que está reservada para você. Poltrona {poltrona_origem} não está reservada para esta reserva.",
            )

        if getattr(reserva.voo, poltrona_destino_field):
            raise HTTPException(
                status_code=400,
                detail=f"Poltrona {poltrona_destino} já reservada para este voo.",
            )

        setattr(reserva.voo, poltrona_origem_field, None)
        setattr(reserva.voo, poltrona_destino_field, reserva.documento)
        session.commit()

        return {"message": f"Troca de poltronas realizada com sucesso: {poltrona_origem} para {poltrona_destino}."}

