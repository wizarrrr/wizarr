from typing import Optional
from models.admins import AdminsModel, Admins
from pydantic import ValidationError
from werkzeug.security import generate_password_hash

# ANCHOR - Get Admins
def get_admins() -> list[Admins]:
    # Get all admins as a list of dicts
    admins = Admins.select()
    
    # Return a list of dicts
    return admins


# ANCHOR - Create Admin User
def create_admin_user(username: str, email: str, password: str, confirm_password: Optional[str] = None):

    # Validate user input
    data = AdminsModel(
        username=username,
        email=email,
        password=password
    )
    
    # Validate passwords match
    if confirm_password:
        if str(data.password) != str(confirm_password):
            raise ValidationError("Passwords do not match")
    
    # Validate username is not taken
    users = get_admins()
    
    if any(user.username == data.username for user in users):
        raise ValidationError("Username already taken")
    
    # Hash the password
    password_hash = generate_password_hash(data.password)
    
    # Create the user
    Admins.create(
        username=data.username,
        password=password_hash,
        email=data.email
    )
    
    # Remove password from data
    response = data.model_dump()
    response.pop("password")
    
    # Return the user
    return response
    
    