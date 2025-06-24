import pytest
from models.user import User

def test_user_creation():
    user = User("satvik", "secret")
    assert user.username == "satvik"

# def test_user_password_not_exposed():
#     user = User("satvik", "secret")
#     with pytest.raises(AttributeError):
#         _ = user._password # trying to access protected member (by convention)