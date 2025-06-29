from ninja.security import HttpBearer
from django.contrib.auth import get_user_model
from django.conf import settings
import jwt

User = get_user_model()

class CustomJWTAuth(HttpBearer):
    def authenticate(self, request, token: str):
        try:
            # Periksa dulu algoritma dari token (optional)
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "HS256":
                print(f"Algoritma tidak didukung: {header.get('alg')}")
                return None

            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )
            user_id = payload.get("user_id")
            if user_id:
                return User.objects.get(id=user_id)
        except Exception as e:
            print("JWT decode failed:", e)
            return None
