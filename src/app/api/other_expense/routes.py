from fastapi import APIRouter

from app.api.other_expense.handler import other_expense_handler

router = APIRouter()

router.add_api_route(
    "/vehicles/{vehicle_id}/other-expenses",
    other_expense_handler.get_vehicle_other_expenses,
    methods=["GET"],
    tags=["other-expenses"],
)
router.add_api_route(
    "/vehicles/{vehicle_id}/other-expenses",
    other_expense_handler.create_other_expense,
    methods=["POST"],
    tags=["other-expenses"],
)
router.add_api_route(
    "/other-expenses/{expense_id}",
    other_expense_handler.get_other_expense,
    methods=["GET"],
    tags=["other-expenses"],
)
router.add_api_route(
    "/other-expenses/{expense_id}",
    other_expense_handler.update_other_expense,
    methods=["PATCH"],
    tags=["other-expenses"],
)
router.add_api_route(
    "/other-expenses/{expense_id}",
    other_expense_handler.delete_other_expense,
    methods=["DELETE"],
    tags=["other-expenses"],
)
