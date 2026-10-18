import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pwdlib import PasswordHash
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from kansei import sha256
from kansei.db import SessionDep, User, UserSession

COOKIE = "kansei_session"
SESSION_LIFETIME = timedelta(days=14)

password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("dummypassword")

router = APIRouter()

SessionCookie = Annotated[str | None, Cookie(alias=COOKIE)]


class Login(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class Signup(Login):
    password: str = Field(min_length=15, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str


def current_user(session: SessionDep, token: SessionCookie = None) -> User:
    if token is None:
        raise HTTPException(status_code=401, detail="Not logged in")
    user = session.scalar(
        select(User)
        .join(UserSession, UserSession.user_id == User.id)
        .where(UserSession.id == sha256(token), UserSession.expires_at > datetime.now(UTC))
    )
    if user is None:
        raise HTTPException(status_code=401, detail="Not logged in")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


@router.post("/signup", status_code=201)
def signup(body: Signup, session: SessionDep) -> UserOut:
    user = User(email=body.email.lower(), password_hash=password_hash.hash(body.password))
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    return UserOut.model_validate(user)


@router.post("/login", status_code=204)
def login(body: Login, session: SessionDep, response: Response) -> None:
    user = session.scalar(select(User).where(User.email == body.email.lower()))
    if user is None:
        password_hash.verify(body.password, DUMMY_HASH)
        raise HTTPException(status_code=401, detail="Wrong email or password")
    if not password_hash.verify(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Wrong email or password")

    token = secrets.token_urlsafe(32)
    session.add(UserSession(id=sha256(token), user_id=user.id, expires_at=datetime.now(UTC) + SESSION_LIFETIME))
    session.commit()
    response.set_cookie(
        COOKIE,
        token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        httponly=True,
        secure=True,
        samesite="lax",
    )


@router.post("/logout", status_code=204)
def logout(session: SessionDep, response: Response, token: SessionCookie = None) -> None:
    if token is not None:
        session.execute(delete(UserSession).where(UserSession.id == sha256(token)))
        session.commit()
    response.delete_cookie(COOKIE, httponly=True, secure=True, samesite="lax")


@router.get("/me")
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
