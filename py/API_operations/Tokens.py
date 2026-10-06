# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Rotating refresh tokens, paired with short-lived access tokens.
#
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, update, delete, or_

from API_models.login import TokenRsp
from API_operations.helpers.Service import Service
from DB.User import User, UserStatus, UserRefreshToken
from DB.helpers.ORM import Session
from helpers import DateTime
from helpers.fastApiUtils import (
    access_ttl,
    refresh_ttl,
    issue_access_token,
    credentials_exception,
)


def _now() -> datetime:
    # Stored as naive UTC, like the TIMESTAMP columns
    return DateTime.now_time().replace(tzinfo=None)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class RefreshTokenService(Service):
    """
    Issue, rotate and revoke refresh tokens. A presented token which was already rotated
    means it was stolen (or replayed), so its whole family is revoked.
    """

    def issue(
        self,
        user_id: int,
        client_info: Optional[str] = None,
        family_id: Optional[str] = None,
    ) -> TokenRsp:
        if family_id is None:
            # New login: only the most recent ones stay valid
            self._revoke_oldest_families(user_id)
            family_id = str(uuid4())
        ret, _ = self._add_token(user_id, client_info, family_id)
        self.session.commit()
        return ret

    def rotate(self, refresh_token: str, client_info: Optional[str] = None) -> TokenRsp:
        now = _now()
        old = self.session.scalars(
            select(UserRefreshToken)
            .where(UserRefreshToken.token_hash == _hash(refresh_token))
            .with_for_update()
        ).one_or_none()
        if old is None or old.expires_at < now:
            raise credentials_exception()
        user = self.session.get(User, old.user_id)
        if (
            old.replaced_by is not None
            or user is None
            or user.status != UserStatus.active.value
        ):
            # Reuse of a rotated token, or user not allowed anymore
            self._revoke_family(old.family_id, now)
            self.session.commit()
            raise credentials_exception()
        if old.revoked_at is not None:
            raise credentials_exception()
        ret, new = self._add_token(old.user_id, client_info, old.family_id)
        old.revoked_at = old.last_used_at = now
        old.replaced_by = new.id
        self.session.commit()
        return ret

    def revoke(self, refresh_token: str) -> None:
        """Silent whatever the token is, see RFC 7009."""
        family_id = self.session.scalars(
            select(UserRefreshToken.family_id).where(
                UserRefreshToken.token_hash == _hash(refresh_token)
            )
        ).one_or_none()
        if family_id is not None:
            self._revoke_family(family_id, _now())
            self.session.commit()

    @staticmethod
    def revoke_all_for_user(session: Session, user_id: int) -> None:
        """Revoke in the caller's session, which commits."""
        session.execute(
            update(UserRefreshToken)
            .where(UserRefreshToken.user_id == user_id)
            .where(UserRefreshToken.revoked_at.is_(None))
            .values(revoked_at=_now())
        )

    def purge_expired(self, grace_days: int = 7) -> int:
        now = _now()
        res = self.session.execute(
            delete(UserRefreshToken).where(
                or_(
                    UserRefreshToken.expires_at < now,
                    UserRefreshToken.revoked_at < now - timedelta(days=grace_days),
                )
            )
        )
        self.session.commit()
        return res.rowcount  # type: ignore

    def _add_token(
        self, user_id: int, client_info: Optional[str], family_id: str
    ) -> tuple[TokenRsp, UserRefreshToken]:
        token = secrets.token_urlsafe(32)
        now = _now()
        row = UserRefreshToken(
            user_id=user_id,
            token_hash=_hash(token),
            family_id=family_id,
            created_at=now,
            expires_at=now + timedelta(seconds=refresh_ttl()),
            client_info=(client_info or "")[:255] or None,
        )
        self.session.add(row)
        self.session.flush()
        ret = TokenRsp(
            access_token=issue_access_token(user_id),
            expires_in=access_ttl(),
            refresh_token=token,
            refresh_expires_in=refresh_ttl(),
        )
        return ret, row

    def _revoke_oldest_families(self, user_id: int) -> None:
        """Leave room for a new family. A family has at most one live token."""
        max_families = int(self.config.get_cnf("MAX_REFRESH_FAMILIES") or 10)
        now = _now()
        to_revoke = self.session.scalars(
            select(UserRefreshToken.family_id)
            .where(UserRefreshToken.user_id == user_id)
            .where(UserRefreshToken.revoked_at.is_(None))
            .where(UserRefreshToken.expires_at > now)
            .order_by(UserRefreshToken.created_at.desc())
            .offset(max(max_families - 1, 0))
        ).all()
        for family_id in to_revoke:
            self._revoke_family(family_id, now)

    def _revoke_family(self, family_id: str, now: datetime) -> None:
        self.session.execute(
            update(UserRefreshToken)
            .where(UserRefreshToken.family_id == family_id)
            .where(UserRefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
