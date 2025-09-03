from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from app.models.order import Order, OrderCreate, OrderUpdate, OrderStatusUpdate, OrderDB, OrderStatus
from app.core.database import get_db

router = APIRouter()

@router.get("/", response_model=List[Order])
def get_orders(db: Session = Depends(get_db)):
    """Obtener todas las órdenes"""
    orders = db.query(OrderDB).all()
    return orders

@router.get("/{order_id}", response_model=Order)
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Obtener una orden específica"""
    order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return order

@router.post("/", response_model=Order)
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    """Crear una nueva orden"""
    # Calcular el total
    total = order.quantity * order.price
    
    # Crear la orden en la base de datos
    db_order = OrderDB(
        customer_name=order.customer_name,
        product_name=order.product_name,
        quantity=order.quantity,
        price=order.price,
        total=total,
        notes=order.notes,
        status="pending"
    )
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    return db_order

@router.put("/{order_id}", response_model=Order)
def update_order(order_id: int, order_update: OrderUpdate, db: Session = Depends(get_db)):
    """Actualizar una orden completa"""
    db_order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    # Actualizar solo los campos proporcionados
    update_data = order_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_order, field, value)
    
    # Recalcular el total si se actualizó cantidad o precio
    if 'quantity' in update_data or 'price' in update_data:
        db_order.total = db_order.quantity * db_order.price
    
    db.commit()
    db.refresh(db_order)
    
    return db_order

@router.put("/{order_id}/status")
def update_order_status(order_id: int, status_update: OrderStatusUpdate, db: Session = Depends(get_db)):
    """Actualizar el estado de una orden"""
    db_order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    db_order.status = status_update.status.value
    db.commit()
    db.refresh(db_order)
    
    return {"message": "Estado actualizado correctamente", "order": db_order}

@router.delete("/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    """Eliminar una orden"""
    db_order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    db.delete(db_order)
    db.commit()
    
    return {"message": "Orden eliminada correctamente"}