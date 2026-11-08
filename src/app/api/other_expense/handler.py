import logging

from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.api.other_expense.schema import (
    OtherExpenseResponse,
    OtherExpenseUpdateRequest,
    OtherExpenseCreateRequest,
)
from app.common.middleware import (
    verify_vehicle_access,
    verify_vehicle_view_access,
    verify_other_expense_access,
    verify_other_expense_view_access,
)
from app.db.database import get_db
from app.services.dto import VehicleDTO, OtherExpenseDTO
from app.services.other_expense_service import OtherExpenseService

logger = logging.getLogger(__name__)


class OtherExpenseHandler:
    """Хэндлер для операций с прочими тратами."""

    @staticmethod
    def _to_response(expense: OtherExpenseDTO) -> OtherExpenseResponse:
        """Преобразовать DTO в Response."""
        return OtherExpenseResponse(
            id=expense.id,
            vehicle_id=expense.vehicle_id,
            name=expense.name,
            expense_date=expense.expense_date,
            amount=expense.amount,
        )

    async def create_other_expense(
        self,
        request: OtherExpenseCreateRequest,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_access),
    ) -> OtherExpenseResponse:
        """Создать запись о трате."""
        expense_service = OtherExpenseService(db)

        try:
            expense = expense_service.create(vehicle.id, request)
            return self._to_response(expense)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )
        except Exception:
            logger.exception('Failed to create other expense')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось создать трату',
            )

    async def get_vehicle_other_expenses(
        self,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_view_access),
    ) -> list[OtherExpenseResponse]:
        """Получить все траты автомобиля."""
        expense_service = OtherExpenseService(db)

        try:
            expenses = expense_service.get_by_vehicle(vehicle.id)
            return [self._to_response(expense) for expense in expenses]
        except HTTPException:
            raise
        except Exception:
            logger.exception('Failed to get vehicle other expenses')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось получить траты',
            )

    async def get_other_expense(
        self,
        db: Session = Depends(get_db),
        expense: OtherExpenseDTO = Depends(verify_other_expense_view_access),
    ) -> OtherExpenseResponse:
        """Получить трату по ID."""
        return self._to_response(expense)

    async def update_other_expense(
        self,
        request: OtherExpenseUpdateRequest,
        db: Session = Depends(get_db),
        expense: OtherExpenseDTO = Depends(verify_other_expense_access),
    ) -> OtherExpenseResponse:
        """Частично обновить запись о трате."""
        expense_service = OtherExpenseService(db)

        try:
            update_data = request.model_dump(exclude_none=True)
            updated = expense_service.update(expense.id, **update_data)
            if not updated:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Трата не найдена',
                )
            return self._to_response(updated)
        except HTTPException:
            raise
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )
        except Exception:
            logger.exception('Failed to update other expense')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось обновить трату',
            )

    async def delete_other_expense(
        self,
        db: Session = Depends(get_db),
        expense: OtherExpenseDTO = Depends(verify_other_expense_access),
    ) -> dict[str, str]:
        """Удалить запись о трате."""
        expense_service = OtherExpenseService(db)

        try:
            expense_service.delete(expense.id)
            return {'status': 'ok', 'message': f'Трата {expense.id} удалена'}
        except Exception:
            logger.exception('Failed to delete other expense')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось удалить трату',
            )


other_expense_handler = OtherExpenseHandler()
