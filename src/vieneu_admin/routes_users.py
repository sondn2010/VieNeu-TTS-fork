"""User management (admin only). The last active admin and the acting admin are protected."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import Response

from .admin_app import AdminApp
from .models import NotFoundError, Session, StoreError


def register(router: APIRouter, app: AdminApp) -> None:
    deps, web, store = app.deps, app.web, app.store
    write = [Depends(deps.csrf_protect)]

    def users_page(request: Request, session: Session, *, status: int = 200,
                   error: str = "", message: str = "") -> Response:
        return web.render(request, "users.html", session, status=status, users=store.list_users(),
                          error=error, message=message)

    def apply(request: Request, session: Session, action, done: str) -> Response:
        """Run a store mutation and re-render the page with its outcome."""
        try:
            action()
        except NotFoundError as e:
            raise HTTPException(404, str(e)) from e
        except StoreError as e:
            return users_page(request, session, status=400, error=str(e))
        return users_page(request, session, message=done)

    def not_self(session: Session, user_id: int, what: str) -> None:
        if session.user.id == user_id:
            raise StoreError(f"You cannot {what} your own account here.")

    @router.get("/users", name="admin_users")
    def list_users(request: Request, session: Session = Depends(deps.require_admin)) -> Response:
        return users_page(request, session)

    @router.post("/users", name="admin_users_create", dependencies=write)
    def create_user(request: Request, session: Session = Depends(deps.require_admin),
                    username: str = Form(""), password: str = Form(""), role: str = Form("user")) -> Response:
        return apply(request, session, lambda: store.create_user(username, password, role),
                     f"User {username.strip()!r} created.")

    @router.post("/users/{user_id}/role", name="admin_users_role", dependencies=write)
    def set_role(request: Request, user_id: int, session: Session = Depends(deps.require_admin),
                 role: str = Form(...)) -> Response:
        def act() -> None:
            if role != "admin":
                not_self(session, user_id, "demote")
            store.set_role(user_id, role)
        return apply(request, session, act, "Role updated.")

    @router.post("/users/{user_id}/active", name="admin_users_active", dependencies=write)
    def set_active(request: Request, user_id: int, session: Session = Depends(deps.require_admin),
                   active: str = Form(...)) -> Response:
        enable = active == "1"

        def act() -> None:
            if not enable:
                not_self(session, user_id, "disable")
            store.set_active(user_id, enable)  # disabling ends the user's sessions
        return apply(request, session, act, "User enabled." if enable else "User disabled.")

    @router.post("/users/{user_id}/password", name="admin_users_password", dependencies=write)
    def reset_password(request: Request, user_id: int, session: Session = Depends(deps.require_admin),
                       password: str = Form("")) -> Response:
        def act() -> None:
            not_self(session, user_id, "reset the password of")  # use Account > Password instead
            store.reset_password(user_id, password)  # also ends the user's sessions
        return apply(request, session, act, "Password reset; the user was signed out.")

    @router.post("/users/{user_id}/delete", name="admin_users_delete", dependencies=write)
    def delete_user(request: Request, user_id: int, session: Session = Depends(deps.require_admin)) -> Response:
        def act() -> None:
            not_self(session, user_id, "delete")
            store.delete_user(user_id)
        return apply(request, session, act, "User deleted.")
