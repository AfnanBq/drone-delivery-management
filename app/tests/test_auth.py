from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.schemas.user import UserLogin
from app.services.auth import generate_access_token


@patch("app.services.auth.get_user_by_name_and_role")
def test_generate_access_token_user_not_found(mock_get_user):
    # Arrange
    mock_get_user.return_value = None

    body = UserLogin(
        name="john",
        role="admin",
    )
    db = Mock()
    # Act / Assert
    with pytest.raises(HTTPException) as exc:
        generate_access_token(body, db)

    assert exc.value.status_code == 404
    assert exc.value.detail == "User not found"

    mock_get_user.assert_called_once_with(
        db,
        body.name,
        body.role,
    )


@patch("app.services.auth.create_access_token")
@patch("app.services.auth.get_user_by_name_and_role")
@patch("app.services.auth.settings")
def test_generate_access_token_success(
    mock_settings,
    mock_get_user,
    mock_create_token,
):
    # Arrange
    mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
    mock_get_user.return_value = {"id": 1, "name": "user_name"}
    mock_create_token.return_value = "jwt-token"

    body = UserLogin(
        name="user_name",
        role="admin",
    )

    db = Mock()

    # Act
    result = generate_access_token(body, db)

    # Assert
    assert result == "jwt-token"

    mock_get_user.assert_called_once_with(
        db,
        body.name,
        body.role,
    )

    mock_create_token.assert_called_once_with(
        subject="user_name",
        role="admin",
        expires_delta=timedelta(minutes=30),
    )
