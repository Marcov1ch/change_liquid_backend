from datetime import date

from sqlalchemy.orm import Session

from app.api.other_expense.schema import OtherExpenseCreateRequest
from app.repository.other_expense_repository import OtherExpenseRepository
from app.services.dto import OtherExpenseDTO

_MSG_EMPTY_NAME = 'Название траты не может быть пустым'
_MSG_NAME_TOO_LONG = 'Название траты не может быть длиннее 100 символов'
_MSG_AMOUNT_POSITIVE = 'Стоимость траты должна быть больше 0'
_MSG_FUTURE_DATE = 'Дата траты не может быть позже сегодняшнего дня'

_NAME_MAX_LENGTH = 100


class OtherExpenseService:
    """Класс для работы с прочими тратами."""

    def __init__(self, db: Session):
        self.repository = OtherExpenseRepository(db)

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Обрезать название и проверить его корректность."""
        normalized = name.strip()
        if not normalized:
            raise ValueError(_MSG_EMPTY_NAME)
        if len(normalized) > _NAME_MAX_LENGTH:
            raise ValueError(_MSG_NAME_TOO_LONG)
        return normalized

    @staticmethod
    def _validate_amount(amount: int) -> None:
        """Проверить, что стоимость больше 0."""
        if amount <= 0:
            raise ValueError(_MSG_AMOUNT_POSITIVE)

    @staticmethod
    def _validate_date(expense_date: date) -> None:
        """Проверить, что дата не в будущем."""
        if expense_date > date.today():
            raise ValueError(_MSG_FUTURE_DATE)

    def create(
        self,
        vehicle_id: int,
        request: OtherExpenseCreateRequest,
    ) -> OtherExpenseDTO:
        """Создать запись о прочей трате."""
        name = self._normalize_name(request.name)
        self._validate_amount(request.amount)
        self._validate_date(request.expense_date)

        expense = OtherExpenseDTO(
            id=None,
            vehicle_id=vehicle_id,
            name=name,
            expense_date=request.expense_date,
            amount=request.amount,
        )
        return self.repository.save(expense)

    def get_by_id(self, expense_id: int) -> OtherExpenseDTO | None:
        """Получить прочую трату по id."""
        return self.repository.find_by_id(expense_id)

    def get_by_vehicle(self, vehicle_id: int) -> list[OtherExpenseDTO]:
        """Получить прочие траты автомобиля."""
        return self.repository.find_by_vehicle_id(vehicle_id)  # type: ignore[no-any-return]

    def update(
        self,
        expense_id: int,
        *,
        name: str | None = None,
        expense_date: date | None = None,
        amount: int | None = None,
    ) -> OtherExpenseDTO | None:
        """Частично обновить запись о прочей трате."""
        expense = self.repository.find_by_id(expense_id)
        if not expense:
            return None

        if name is not None:
            expense.name = self._normalize_name(name)
        if amount is not None:
            self._validate_amount(amount)
            expense.amount = amount
        if expense_date is not None:
            self._validate_date(expense_date)
            expense.expense_date = expense_date

        return self.repository.save(expense)

    def delete(self, expense_id: int) -> bool:
        """Удалить запись о прочей трате."""
        return bool(self.repository.delete(expense_id))

    def delete_by_vehicle(self, vehicle_id: int, commit: bool = True) -> int:
        """Удалить все прочие траты автомобиля."""
        return self.repository.delete_by_vehicle_id(vehicle_id, commit)  # type: ignore[no-any-return]
