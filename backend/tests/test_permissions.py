"""Matrice de droits DFB §3.1 (exigence 7.2)."""
from types import SimpleNamespace as NS

import pytest

from app.permissions import Perm, can

A, PM, C, R = "admin", "project_manager", "contributor", "reader"
EXPECTED = {
    Perm.VIEW: {A, PM, C, R},
    Perm.PROJECT_WRITE: {A, PM},
    Perm.PROJECT_DELETE: {A, PM},
    Perm.ACTION_WRITE: {A, PM, C},
    Perm.ACTION_DELETE: {A, PM},
    Perm.RISK_WRITE: {A, PM, C},
    Perm.LINK_WRITE: {A, PM, C},
    Perm.FILE_WRITE: {A, PM, C},
    Perm.EMAIL_LOG_VIEW: {A},
    Perm.COMMENT_WRITE: {A, PM, C},
    Perm.MEETING_MANAGE: {A, PM},
    Perm.CHECKLIST_WRITE: {A, PM, C},
    Perm.USER_MANAGE: {A},
    Perm.SELF_SETTINGS: {A, PM, C, R},
}


@pytest.mark.parametrize("perm", list(EXPECTED))
@pytest.mark.parametrize("role", [A, PM, C, R])
def test_matrix(role, perm):
    assert can(NS(id=1, role=role, is_active=True), perm) is (role in EXPECTED[perm])


def test_all_permissions_covered():
    assert set(EXPECTED) | {Perm.COMMENT_EDIT_OWN} == set(Perm)


def test_inactive_user_has_no_right():
    assert not can(NS(id=1, role=A, is_active=False), Perm.VIEW)
    assert not can(None, Perm.VIEW)


def test_comment_edit_only_by_author_with_write_role():
    me = NS(id=1, role=C, is_active=True)
    assert can(me, Perm.COMMENT_EDIT_OWN, NS(author_id=1))
    assert not can(me, Perm.COMMENT_EDIT_OWN, NS(author_id=2))
    assert not can(NS(id=1, role=R, is_active=True), Perm.COMMENT_EDIT_OWN, NS(author_id=1))
