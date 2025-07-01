from django.utils.timezone import now
from django.core.cache import cache
from ninja.throttling import BaseThrottle


class RegisterThrottle(BaseThrottle):
    rate = 5

    def get_cache_key(self, request):
        ip = request.META.get("REMOTE_ADDR", "anonymous")
        return f"register:{ip}:{now().date()}"

    def allow_request(self, request):
        key = self.get_cache_key(request)
        count = cache.get(key, 0)
        if count >= self.rate:
            return False
        cache.set(key, count + 1, 86400)  # 1 day
        return True


class CommentThrottle(BaseThrottle):
    rate = 10

    def get_cache_key(self, request):
        uid = request.user.id if request.user.is_authenticated else request.META.get("REMOTE_ADDR", "anon")
        return f"comment:{uid}:{now().strftime('%Y-%m-%d-%H')}"

    def allow_request(self, request):
        key = self.get_cache_key(request)
        count = cache.get(key, 0)
        if count >= self.rate:
            return False
        cache.set(key, count + 1, 3600)  # 1 hour
        return True


class CourseCreateThrottle(BaseThrottle):
    rate = 1

    def get_cache_key(self, request):
        return f"create-course:{request.user.id}:{now().date()}"

    def allow_request(self, request):
        key = self.get_cache_key(request)
        count = cache.get(key, 0)
        if count >= self.rate:
            return False
        cache.set(key, count + 1, 86400)  # 1 day
        return True


class ContentCreateThrottle(BaseThrottle):
    rate = 10

    def get_cache_key(self, request):
        return f"create-content:{request.user.id}:{now().strftime('%Y-%m-%d-%H')}"

    def allow_request(self, request):
        key = self.get_cache_key(request)
        count = cache.get(key, 0)
        if count >= self.rate:
            return False
        cache.set(key, count + 1, 3600)  # 1 hour
        return True
