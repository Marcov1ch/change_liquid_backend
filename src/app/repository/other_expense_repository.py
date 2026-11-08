from sqlalchemy.orm import Session

from app.db.models import OtherExpenseDB
from app.services.dto import OtherExpenseDTO


class OtherExpenseRepository:
    """Репозиторий для работы с прочими тратами."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _to_dto(db_expense: OtherExpenseDB) -> OtherExpenseDTO:
        """Преобразовать ORM-модель в DTO."""
        return OtherExpenseDTO(
            id=db_expense.id,
            vehicle_id=db_expense.vehicle_id,
            name=db_expense.name,
            expense_date=db_expense.expense_date,
            amount=db_expense.amount,
        )

    def save(self, expense: OtherExpenseDTO, commit: bool = True) -> OtherExpenseDTO:
        """Создать или обновить запись о прочей трате."""
        if expense.id:
            db_expense = self.db.query(OtherExpenseDB).filter(
                OtherExpenseDB.id == expense.id
            ).first()
            if not db_expense:
                raise ValueError(f'OtherExpense with id {expense.id} not found')

            db_expense.vehicle_id = expense.vehicle_id
            db_expense.name = expense.name
            db_expense.expense_date = expense.expense_date
            db_expense.amount = expense.amount
        else:
            db_expense = OtherExpenseDB(
                vehicle_id=expense.vehicle_id,
                name=expense.name,
                expense_date=expense.expense_date,
                amount=expense.amount,
            )
            self.db.add(db_expense)

        if commit:
            self.db.commit()
        else:
            self.db.flush()
        self.db.refresh(db_expense)

        return self._to_dto(db_expense)

    def find_by_id(self, expense_id: int) -> OtherExpenseDTO | None:
        """Найти прочую трату по id."""
        db_expense = self.db.query(OtherExpenseDB).filter(
            OtherExpenseDB.id == expense_id
        ).first()
        return self._to_dto(db_expense) if db_expense else None

    def find_by_vehicle_id(self, vehicle_id: int) -> list[OtherExpenseDTO]:
        """Найти все прочие траты автомобиля (сначала новые)."""
        db_expenses = self.db.query(OtherExpenseDB).filter(
            OtherExpenseDB.vehicle_id == vehicle_id
        ).order_by(
            OtherExpenseDB.expense_date.desc(),
            OtherExpenseDB.id.desc(),
        ).all()
        return [self._to_dto(expense) for expense in db_expenses]

    def delete(self, expense_id: int) -> bool:
        """Удалить запись о прочей трате."""
        db_expense = self.db.query(OtherExpenseDB).filter(
            OtherExpenseDB.id == expense_id
        ).first()
        if db_expense:
            self.db.delete(db_expense)
            self.db.commit()
            return True
        return False

    def delete_by_vehicle_id(self, vehicle_id: int, commit: bool = True) -> int:
        """Удалить все прочие траты автомобиля. Возвращает количество удалённых."""
        count = self.db.query(OtherExpenseDB).filter(
            OtherExpenseDB.vehicle_id == vehicle_id
        ).delete()
        if commit:
            self.db.commit()
        return count  # type: ignore[no-any-return]
