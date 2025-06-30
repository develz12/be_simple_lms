from ninja.security import HttpBearer
from django.contrib.auth import get_user_model
from ninja_jwt.tokens import UntypedToken
from ninja_jwt.authentication import JWTAuth
from django.contrib.auth.models import AnonymousUser

class CustomJWTAuth(HttpBearer):
    def authenticate(self, request, token):
        try:
            validated_token = JWTAuth().get_validated_token(token)
            user = JWTAuth().get_user(validated_token)
            request.user = user  # inject ke request.user
            return user
        except Exception:
            return AnonymousUser()
